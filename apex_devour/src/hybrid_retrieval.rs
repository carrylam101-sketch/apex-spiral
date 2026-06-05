//! Hybrid retrieval RRF gate for APEX-MEM style memory retrieval.
//!
//! Native Rust measurement gate inspired by APEX-MEM's retrieval architecture:
//! BM25 lexical hits + dense vector hits + graph BFS hits fused with Reciprocal Rank Fusion.
//! This module is deliberately local/offline: it does not embed Tantivy/HNSW/petgraph server
//! dependencies; the external APEX-MEM MCP server can still provide real channel outputs.

use serde::{Deserialize, Serialize};
use std::collections::{BTreeSet, HashMap};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetrievalChannelHit {
    pub id: String,
    pub rank: usize,
    #[serde(default)]
    pub score: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HybridRetrievalInput {
    #[serde(default)]
    pub bm25: Vec<RetrievalChannelHit>,
    #[serde(default)]
    pub vector: Vec<RetrievalChannelHit>,
    #[serde(default)]
    pub graph: Vec<RetrievalChannelHit>,
    #[serde(default = "default_k_rrf")]
    pub k_rrf: f64,
    #[serde(default = "default_top_k")]
    pub top_k: usize,
}

fn default_k_rrf() -> f64 { 60.0 }
fn default_top_k() -> usize { 5 }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FusedRetrievalHit {
    pub id: String,
    pub fused_score: f64,
    pub channel_count: usize,
    pub sources: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HybridRetrievalReport {
    pub n_bm25: usize,
    pub n_vector: usize,
    pub n_graph: usize,
    pub n_unique: usize,
    pub top_k: usize,
    pub k_rrf: f64,
    pub channel_coverage: f64,
    pub overlap_rate: f64,
    pub mean_channel_count: f64,
    pub rrf_quality: f64,
    pub keep_for_memory: bool,
    pub fused_hits: Vec<FusedRetrievalHit>,
}

pub struct HybridRetrievalGate;

impl HybridRetrievalGate {
    /// Fuse three retrieval channels with weighted RRF and produce conservative gates.
    /// weights: bm25=1.00, vector=1.05, graph=0.90.
    /// rrf_quality = 0.40*channel_coverage + 0.35*overlap_rate + 0.25*normalized_top_score.
    pub fn evaluate(input: &HybridRetrievalInput) -> HybridRetrievalReport {
        let mut scores: HashMap<String, f64> = HashMap::new();
        let mut sources: HashMap<String, BTreeSet<String>> = HashMap::new();

        add_channel(&input.bm25, "bm25", 1.00, input.k_rrf, &mut scores, &mut sources);
        add_channel(&input.vector, "vector", 1.05, input.k_rrf, &mut scores, &mut sources);
        add_channel(&input.graph, "graph", 0.90, input.k_rrf, &mut scores, &mut sources);

        let mut fused_hits: Vec<FusedRetrievalHit> = scores
            .iter()
            .map(|(id, score)| {
                let srcs: Vec<String> = sources
                    .get(id)
                    .cloned()
                    .unwrap_or_default()
                    .into_iter()
                    .collect();
                FusedRetrievalHit {
                    id: id.clone(),
                    fused_score: *score,
                    channel_count: srcs.len(),
                    sources: srcs,
                }
            })
            .collect();
        fused_hits.sort_by(|a, b| {
            b.fused_score
                .partial_cmp(&a.fused_score)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| b.channel_count.cmp(&a.channel_count))
                .then_with(|| a.id.cmp(&b.id))
        });
        let top_k = input.top_k.max(1);
        fused_hits.truncate(top_k);

        let n_unique = scores.len();
        let active_channels = [!input.bm25.is_empty(), !input.vector.is_empty(), !input.graph.is_empty()]
            .iter()
            .filter(|x| **x)
            .count();
        let channel_coverage = active_channels as f64 / 3.0;
        let mean_channel_count = if n_unique == 0 {
            0.0
        } else {
            sources.values().map(|s| s.len() as f64).sum::<f64>() / n_unique as f64
        };
        let overlap_rate = if n_unique == 0 {
            0.0
        } else {
            sources.values().filter(|s| s.len() >= 2).count() as f64 / n_unique as f64
        };
        let theoretical_top = (1.00 + 1.05 + 0.90) / (input.k_rrf + 1.0);
        let top_score = fused_hits.first().map(|h| h.fused_score).unwrap_or(0.0);
        let normalized_top_score = if theoretical_top > 0.0 {
            (top_score / theoretical_top).clamp(0.0, 1.0)
        } else {
            0.0
        };
        let rrf_quality = (0.40 * channel_coverage
            + 0.35 * overlap_rate
            + 0.25 * normalized_top_score)
            .clamp(0.0, 1.0);
        let keep_for_memory = rrf_quality >= 0.55 && channel_coverage >= 0.66 && overlap_rate >= 0.20;

        HybridRetrievalReport {
            n_bm25: input.bm25.len(),
            n_vector: input.vector.len(),
            n_graph: input.graph.len(),
            n_unique,
            top_k,
            k_rrf: input.k_rrf,
            channel_coverage,
            overlap_rate,
            mean_channel_count,
            rrf_quality,
            keep_for_memory,
            fused_hits,
        }
    }
}

fn add_channel(
    hits: &[RetrievalChannelHit],
    name: &str,
    weight: f64,
    k_rrf: f64,
    scores: &mut HashMap<String, f64>,
    sources: &mut HashMap<String, BTreeSet<String>>,
) {
    for (idx, h) in hits.iter().enumerate() {
        let rank = if h.rank == 0 { idx + 1 } else { h.rank };
        let rrf = weight / (k_rrf + rank as f64);
        *scores.entry(h.id.clone()).or_insert(0.0) += rrf;
        sources.entry(h.id.clone()).or_default().insert(name.to_string());
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn hit(id: &str, rank: usize) -> RetrievalChannelHit {
        RetrievalChannelHit { id: id.into(), rank, score: 0.0 }
    }

    #[test]
    fn fuses_overlapping_three_channel_hits() {
        let input = HybridRetrievalInput {
            bm25: vec![hit("a", 1), hit("b", 2)],
            vector: vec![hit("a", 1), hit("c", 2)],
            graph: vec![hit("a", 1), hit("d", 2)],
            k_rrf: 60.0,
            top_k: 3,
        };
        let report = HybridRetrievalGate::evaluate(&input);
        assert_eq!(report.n_unique, 4);
        assert_eq!(report.fused_hits[0].id, "a");
        assert_eq!(report.fused_hits[0].channel_count, 3);
        assert!(report.rrf_quality > 0.55);
        assert!(report.keep_for_memory);
    }

    #[test]
    fn rejects_single_channel_low_overlap_retrieval() {
        let input = HybridRetrievalInput {
            bm25: vec![hit("a", 1), hit("b", 2), hit("c", 3)],
            vector: vec![],
            graph: vec![],
            k_rrf: 60.0,
            top_k: 3,
        };
        let report = HybridRetrievalGate::evaluate(&input);
        assert!(report.channel_coverage < 0.34);
        assert_eq!(report.overlap_rate, 0.0);
        assert!(!report.keep_for_memory);
    }
}
