use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};

#[derive(Parser, Debug)]
#[command(name = "evomaster_claw_core")]
#[command(about = "EvoMaster adapted CLAW native evolution core: objective, GPT-stream policy update envelope, and HashPool knowledge cache")]
struct Cli {
    #[command(subcommand)]
    cmd: Command,
}

#[derive(Subcommand, Debug)]
enum Command {
    /// Health check and formula declaration.
    Health,
    /// Compute J_claw = E[R_exec + lambda*K_claw] from trajectory JSONL.
    Objective {
        #[arg(long)]
        input: PathBuf,
        #[arg(long, default_value_t = 0.35)]
        lambda: f64,
    },
    /// Build K_claw = HashPool(Filter(valid trajectories)).
    Cache {
        #[arg(long)]
        input: PathBuf,
        #[arg(long, default_value_t = 0.50)]
        min_reward: f64,
        #[arg(long, default_value_t = 128)]
        max_items: usize,
    },
    /// Produce next CLAW policy envelope from current trajectory, cache, and sandbox constraints.
    Update {
        #[arg(long)]
        trajectory: PathBuf,
        #[arg(long)]
        cache: PathBuf,
        #[arg(long)]
        constraints: PathBuf,
    },
    /// End-to-end audit: objective + cache + policy gates.
    Audit {
        #[arg(long)]
        input: PathBuf,
        #[arg(long)]
        constraints: PathBuf,
        #[arg(long, default_value_t = 0.35)]
        lambda: f64,
        #[arg(long, default_value_t = 0.50)]
        min_reward: f64,
    },
}

#[derive(Serialize, Deserialize, Clone, Debug, Default)]
struct TrajectoryEvent {
    id: Option<String>,
    task_id: Option<String>,
    command: String,
    success: bool,
    exec_reward: f64,
    compliance: f64,
    reusable: bool,
    error_type: Option<String>,
    artifact: Option<String>,
    policy_hint: Option<String>,
}

#[derive(Serialize, Deserialize, Clone, Debug, Default)]
struct SandboxConstraints {
    allowed_tools: Vec<String>,
    blocked_patterns: Vec<String>,
    max_depth: u32,
    max_steps: u32,
    require_artifact: bool,
}

#[derive(Serialize)]
struct ObjectiveOutput {
    status: &'static str,
    formula: &'static str,
    lambda: f64,
    n_events: usize,
    success_rate: f64,
    avg_exec_reward: f64,
    avg_compliance: f64,
    knowledge_density: f64,
    k_claw: f64,
    objective: f64,
    trajectory_gate: bool,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
struct CacheItem {
    hash: String,
    command: String,
    task_id: Option<String>,
    reward: f64,
    compliance: f64,
    artifact: Option<String>,
    policy_hint: Option<String>,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
struct CacheOutput {
    status: String,
    formula: String,
    input_events: usize,
    valid_events: usize,
    unique_hashes: usize,
    min_reward: f64,
    hash_pool: Vec<CacheItem>,
}

#[derive(Serialize)]
struct UpdateOutput {
    status: &'static str,
    formula: &'static str,
    policy: &'static str,
    cache_items: usize,
    constraints: SandboxConstraints,
    recommended_tools: Vec<String>,
    avoid_errors: Vec<String>,
    reusable_patterns: Vec<String>,
    gates: BTreeMap<&'static str, bool>,
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.cmd {
        Command::Health => print_json(&serde_json::json!({
            "status":"ok",
            "engine":"evomaster_claw_core",
            "version": env!("CARGO_PKG_VERSION"),
            "formulas":[
                "max_pi E_tau~pi[R_exec(tau)+lambda*K_claw(tau)]",
                "pi_claw(t+1)=GPT-Stream(tau(t),K_claw,Constraint_sandbox)",
                "K_claw=HashPool(Filter(tau_valid))"
            ],
            "commands":["health","objective","cache","update","audit"]
        })),
        Command::Objective { input, lambda } => {
            let events = read_events(&input)?;
            print_json(&objective(&events, lambda))
        }
        Command::Cache { input, min_reward, max_items } => {
            let events = read_events(&input)?;
            print_json(&cache(&events, min_reward, max_items))
        }
        Command::Update { trajectory, cache, constraints } => {
            let events = read_events(&trajectory)?;
            let cache_payload: CacheOutput = read_json(&cache)?;
            let constraints_payload: SandboxConstraints = read_json(&constraints)?;
            print_json(&update_policy(&events, &cache_payload, constraints_payload))
        }
        Command::Audit { input, constraints, lambda, min_reward } => {
            let events = read_events(&input)?;
            let constraints_payload: SandboxConstraints = read_json(&constraints)?;
            let obj = objective(&events, lambda);
            let cache_payload = cache(&events, min_reward, 128);
            let update = update_policy(&events, &cache_payload, constraints_payload);
            print_json(&serde_json::json!({
                "status":"ok",
                "mode":"evomaster_claw_native_evolution_audit",
                "objective": obj,
                "cache": cache_payload,
                "policy_update": update,
                "verify": {
                    "objective_gate": obj.trajectory_gate,
                    "cache_gate": cache_payload.unique_hashes > 0,
                    "sandbox_gate": update.gates.get("sandbox_gate").copied().unwrap_or(false),
                    "reuse_gate": update.gates.get("reuse_gate").copied().unwrap_or(false)
                }
            }))
        }
    }
}

fn read_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T> {
    let raw = fs::read_to_string(path).with_context(|| format!("read {}", path.display()))?;
    serde_json::from_str(&raw).with_context(|| format!("parse json {}", path.display()))
}

fn read_events(path: &Path) -> Result<Vec<TrajectoryEvent>> {
    let file = fs::File::open(path).with_context(|| format!("open {}", path.display()))?;
    let reader = BufReader::new(file);
    let mut out = Vec::new();
    for (idx, line) in reader.lines().enumerate() {
        let line = line.with_context(|| format!("read line {}", idx + 1))?;
        if line.trim().is_empty() { continue; }
        let event: TrajectoryEvent = serde_json::from_str(&line)
            .with_context(|| format!("parse jsonl line {}", idx + 1))?;
        out.push(event);
    }
    Ok(out)
}

fn print_json<T: Serialize>(value: &T) -> Result<()> {
    println!("{}", serde_json::to_string_pretty(value)?);
    Ok(())
}

fn clamp01(v: f64) -> f64 { v.max(0.0).min(1.0) }

fn objective(events: &[TrajectoryEvent], lambda: f64) -> ObjectiveOutput {
    let n = events.len().max(1) as f64;
    let success_rate = events.iter().filter(|e| e.success).count() as f64 / n;
    let avg_exec_reward = events.iter().map(|e| clamp01(e.exec_reward)).sum::<f64>() / n;
    let avg_compliance = events.iter().map(|e| clamp01(e.compliance)).sum::<f64>() / n;
    let knowledge_density = events.iter().filter(|e| e.success && e.reusable && e.artifact.is_some()).count() as f64 / n;
    let k_claw = clamp01(0.45 * success_rate + 0.30 * knowledge_density + 0.25 * avg_compliance);
    let objective = avg_exec_reward + lambda * k_claw;
    ObjectiveOutput {
        status: "ok",
        formula: "J_claw=E[R_exec(tau)+lambda*K_claw(tau)]",
        lambda,
        n_events: events.len(),
        success_rate,
        avg_exec_reward,
        avg_compliance,
        knowledge_density,
        k_claw,
        objective,
        trajectory_gate: success_rate >= 0.60 && avg_compliance >= 0.70,
    }
}

fn cache(events: &[TrajectoryEvent], min_reward: f64, max_items: usize) -> CacheOutput {
    let mut seen = BTreeSet::new();
    let mut items = Vec::new();
    for e in events.iter().filter(|e| e.success && e.reusable && e.exec_reward >= min_reward && e.compliance >= 0.70) {
        let fingerprint = format!("{}|{}|{}|{}", e.task_id.clone().unwrap_or_default(), e.command, e.artifact.clone().unwrap_or_default(), e.policy_hint.clone().unwrap_or_default());
        let mut hasher = Sha256::new();
        hasher.update(fingerprint.as_bytes());
        let hash = hex::encode(hasher.finalize());
        if seen.insert(hash.clone()) {
            items.push(CacheItem {
                hash,
                command: e.command.clone(),
                task_id: e.task_id.clone(),
                reward: e.exec_reward,
                compliance: e.compliance,
                artifact: e.artifact.clone(),
                policy_hint: e.policy_hint.clone(),
            });
            if items.len() >= max_items { break; }
        }
    }
    CacheOutput {
        status: "ok".to_string(),
        formula: "K_claw=HashPool(Filter(tau_valid))".to_string(),
        input_events: events.len(),
        valid_events: items.len(),
        unique_hashes: seen.len(),
        min_reward,
        hash_pool: items,
    }
}

fn update_policy(events: &[TrajectoryEvent], cache: &CacheOutput, constraints: SandboxConstraints) -> UpdateOutput {
    let mut tool_scores: BTreeMap<String, f64> = BTreeMap::new();
    let mut avoid = BTreeSet::new();
    for e in events {
        if e.success {
            *tool_scores.entry(e.command.clone()).or_insert(0.0) += e.exec_reward * e.compliance;
        } else if let Some(err) = &e.error_type {
            avoid.insert(err.clone());
        }
    }
    let mut recommended: Vec<_> = tool_scores.into_iter()
        .filter(|(tool, _)| constraints.allowed_tools.is_empty() || constraints.allowed_tools.iter().any(|t| tool.contains(t) || t == tool))
        .collect();
    recommended.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    let recommended_tools = recommended.into_iter().take(5).map(|(tool, _)| tool).collect::<Vec<_>>();
    let reusable_patterns = cache.hash_pool.iter()
        .take(8)
        .map(|item| item.policy_hint.clone().unwrap_or_else(|| item.command.clone()))
        .collect::<Vec<_>>();
    let sandbox_gate = constraints.max_depth > 0 && constraints.max_steps > 0 && !constraints.blocked_patterns.iter().any(|p| p.trim().is_empty());
    let reuse_gate = !cache.hash_pool.is_empty() && !reusable_patterns.is_empty();
    let mut gates = BTreeMap::new();
    gates.insert("sandbox_gate", sandbox_gate);
    gates.insert("reuse_gate", reuse_gate);
    gates.insert("artifact_gate", !constraints.require_artifact || cache.hash_pool.iter().all(|i| i.artifact.is_some()));
    gates.insert("policy_gate", !recommended_tools.is_empty());
    UpdateOutput {
        status: "ok",
        formula: "pi_claw(t+1)=GPT-Stream(tau(t),K_claw,Constraint_sandbox)",
        policy: "gpt_stream_policy_envelope",
        cache_items: cache.hash_pool.len(),
        constraints,
        recommended_tools,
        avoid_errors: avoid.into_iter().collect(),
        reusable_patterns,
        gates,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_events() -> Vec<TrajectoryEvent> {
        vec![
            TrajectoryEvent { task_id: Some("a".into()), command: "browser_snapshot".into(), success: true, exec_reward: 0.92, compliance: 0.95, reusable: true, artifact: Some("/tmp/a.json".into()), policy_hint: Some("prefer DOM before vision".into()), ..Default::default() },
            TrajectoryEvent { task_id: Some("a".into()), command: "browser_vision".into(), success: false, exec_reward: 0.10, compliance: 0.40, reusable: false, error_type: Some("vision_waste".into()), ..Default::default() },
            TrajectoryEvent { task_id: Some("b".into()), command: "terminal".into(), success: true, exec_reward: 0.80, compliance: 0.88, reusable: true, artifact: Some("/tmp/b.log".into()), policy_hint: Some("verify with CLI before switch".into()), ..Default::default() },
        ]
    }

    #[test]
    fn objective_scores_policy_value() {
        let out = objective(&sample_events(), 0.35);
        assert!(out.objective > 0.70);
        assert!(out.k_claw > 0.50);
    }

    #[test]
    fn cache_filters_valid_unique_trajectories() {
        let out = cache(&sample_events(), 0.50, 10);
        assert_eq!(out.valid_events, 2);
        assert_eq!(out.unique_hashes, 2);
        assert_eq!(out.hash_pool[0].hash.len(), 64);
    }

    #[test]
    fn update_respects_sandbox_and_reuse() {
        let events = sample_events();
        let cache_payload = cache(&events, 0.50, 10);
        let constraints = SandboxConstraints { allowed_tools: vec!["browser".into(), "terminal".into()], blocked_patterns: vec!["rm -rf".into()], max_depth: 2, max_steps: 20, require_artifact: true };
        let out = update_policy(&events, &cache_payload, constraints);
        assert_eq!(out.gates.get("sandbox_gate"), Some(&true));
        assert_eq!(out.gates.get("reuse_gate"), Some(&true));
        assert!(out.avoid_errors.contains(&"vision_waste".to_string()));
    }
}
