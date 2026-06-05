//! APEX StraTA — Strategic Tiered Agent Architecture
//! Bee Queen Activated Swarm Mode
//!
//! Formula:
//!   ApexStraTA = π(z|s₁) ⊗ π(aₜ|z,sₜ) ⊗ GRPO(z,aₜ) ⊗ MemLLM
//!   GRPO: J(θ) = E[ΣA(z) + ΣA(aₜ) − β·DKL(π‖π_old)]
//!
//! Architecture:
//!   z ~ π(s₁)        : Global strategy generation (queen)
//!   aₜ ~ π(z,sₜ)     : Fixed-policy task execution (workers)
//!   GRPO              : Hierarchical reward optimization
//!   MemLLM           : RAG + Long-Term Memory synchronization
//!
//! Single LLM instruction drives:
//!   1. Strategy generation (z)
////!   2. Multi-agent parallel execution (aₜ)
//!   3. Memory sync (MemLLM)
//!   4. Layered reward optimization (GRPO)
//!   5. Self-verification before task completion

use anyhow::Result;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;

/// ============================================================
/// CORE TYPES
/// ============================================================

/// Global strategy generated from situation s₁
/// z is the "queen" strategy that drives all worker agents
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Strategy {
    pub id: String,
    pub z: String,                     // Strategy text/representation
    pub z_hash: String,                // SHA-256 of z for deduplication
    pub source_s1: String,             // Situation s₁ that generated z
    pub created_at: i64,               // Unix timestamp
    pub agents_committed: Vec<String>, // Agent IDs that received this z
    pub status: StrategyStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum StrategyStatus {
    Generated,
    Dispatched,
    Confirmed,
    Failed,
    Superseded,
}

/// Worker agent task execution
/// aₜ is fixed once z is received — no mid-task drift
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskExecution {
    pub id: String,
    pub agent_id: String,
    pub task_id: String,
    pub z_id: String,            // Strategy this agent received
    pub a: String,               // Action taken
    pub a_hash: String,          // SHA-256 of a
    pub observation: String,     // env observation
    pub reward: Option<f64>,     // GRPO reward signal
    pub verifier_pass: bool,     // External verifier result
    pub tool_calls: Vec<String>, // Tools used
    pub timestamp: i64,
    pub memory_synced: bool, // MemLLM sync status
    pub status: ExecutionStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ExecutionStatus {
    Pending, // aₜ assigned, not yet executed
    Running,
    Completed,
    Verified,
    Failed,
}

/// Hierarchical reward: J(θ) = E[ΣA(z) + ΣA(aₜ) − β·DKL]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GRPOState {
    pub z_id: String,
    pub theta: f64,      // Current policy parameter
    pub beta: f64,       // KL penalty coefficient (default 0.1)
    pub sum_az: f64,     // E[ΣA(z)] — strategy reward sum
    pub sum_aat: f64,    // E[ΣA(aₜ)] — execution reward sum
    pub kl_penalty: f64, // β·DKL(π‖π_old)
    pub J_theta: f64,    // Total objective J(θ)
    pub iterations: u32,
}

impl Default for GRPOState {
    fn default() -> Self {
        Self {
            z_id: String::new(),
            theta: 1.0,
            beta: 0.1,
            sum_az: 0.0,
            sum_aat: 0.0,
            kl_penalty: 0.0,
            J_theta: 0.0,
            iterations: 0,
        }
    }
}

/// Memory layer: RAG + Long-Term Memory
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemLLM {
    pub agent_id: String,
    pub short_term: Vec<MemoryEntry>, // In-context RAG (last N turns)
    pub long_term: Vec<MemoryEntry>,  // Persistent memory
    pub rag_scores: HashMap<String, f64>, // Relevance scores for retrieval
    pub sync_status: SyncStatus,
}

impl Default for MemLLM {
    fn default() -> Self {
        Self {
            agent_id: String::new(),
            short_term: Vec::with_capacity(20),
            long_term: Vec::new(),
            rag_scores: HashMap::new(),
            sync_status: SyncStatus::Idle,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum SyncStatus {
    Idle,
    Syncing,
    Synced,
    Stale,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryEntry {
    pub id: String,
    pub content: String,
    pub content_hash: String,
    pub vector_k: Vec<f64>, // Mock embedding vector (K dimensions)
    pub created_at: i64,
    pub access_count: u32,
    pub value_score: f64, // Value-aware compression score
    pub locked: bool,     // True = hard constraint / evidence — never drop
}

/// ============================================================
/// STRATA ENGINE
/// ============================================================

pub struct StraTAEngine {
    pub strategies: Vec<Strategy>,
    pub executions: Vec<TaskExecution>,
    pub grpo: GRPOState,
    pub memories: HashMap<String, MemLLM>, // agent_id → MemLLM
    pub config: StraTAConfig,
}

#[derive(Debug, Clone)]
pub struct StraTAConfig {
    pub max_short_term: usize,     // RAG window size
    pub max_long_term: usize,      // Max long-term entries per agent
    pub beta_kl: f64,              // KL penalty coefficient β
    pub min_reward_threshold: f64, // Min reward to count as success
    pub value_score_floor: f64,    // Drop entries below this value score
}

impl Default for StraTAConfig {
    fn default() -> Self {
        Self {
            max_short_term: 20,
            max_long_term: 1000,
            beta_kl: 0.1,
            min_reward_threshold: 0.5,
            value_score_floor: 0.3,
        }
    }
}

impl StraTAEngine {
    pub fn new() -> Self {
        Self {
            strategies: Vec::new(),
            executions: Vec::new(),
            grpo: GRPOState::default(),
            memories: HashMap::new(),
            config: StraTAConfig::default(),
        }
    }

    /// Step 1: Queen generates global strategy z from s₁
    ///   z ~ π(s₁)  — GPT-global policy generates strategy
    pub fn generate_strategy(&mut self, s1: &str, agent_ids: &[&str]) -> Result<&Strategy> {
        let z_id = generate_id();
        let z_hash = hash_str(s1);
        let now = unix_ts();

        let strategy = Strategy {
            id: z_id.clone(),
            z: format!("[Queen Strategy from s₁]\n{}\n[End Strategy]", s1),
            z_hash,
            source_s1: s1.to_string(),
            created_at: now,
            agents_committed: agent_ids.iter().map(|s| s.to_string()).collect(),
            status: StrategyStatus::Generated,
        };

        self.strategies.push(strategy);
        let strat = self.strategies.last_mut().unwrap();
        strat.status = StrategyStatus::Dispatched;

        // Initialize MemLLM for each agent
        for aid in agent_ids {
            let aid_str = aid.to_string();
            self.memories
                .entry(aid_str.clone())
                .or_insert_with(MemLLM::default);
            if let Some(mem) = self.memories.get_mut(&aid_str) {
                mem.agent_id = aid_str;
            }
        }

        Ok(self.strategies.last().unwrap())
    }

    /// Step 2: Fix strategy z, dispatch aₜ tasks to worker agents
    ///   aₜ ~ π(z,sₜ)  — Fixed policy execution per task
    pub fn dispatch_tasks(&mut self, z_id: &str, tasks: &[(&str, &str)]) -> Vec<String> {
        let has_strat = self.strategies.iter().any(|s| s.id == z_id);
        if !has_strat {
            return vec![];
        }

        let mut exec_ids = Vec::new();
        for (agent_id, task_desc) in tasks {
            let a_id = generate_id();
            let now = unix_ts();

            let execution = TaskExecution {
                id: a_id.clone(),
                agent_id: agent_id.to_string(),
                task_id: task_desc.to_string(),
                z_id: z_id.to_string(),
                a: format!("[Fixed Action for task]\n{}\n[End Action]", task_desc),
                a_hash: hash_str(task_desc),
                observation: String::new(),
                reward: None,
                verifier_pass: false,
                tool_calls: vec![],
                timestamp: now,
                memory_synced: false,
                status: ExecutionStatus::Pending,
            };

            self.executions.push(execution);
            exec_ids.push(a_id);
        }

        exec_ids
    }

    /// Step 3: Record execution result + verifier pass/fail
    pub fn record_execution(
        &mut self,
        exec_id: &str,
        observation: &str,
        verifier_pass: bool,
        reward: f64,
        tool_calls: Vec<String>,
    ) -> Result<&TaskExecution> {
        let exec = self.executions.iter_mut().find(|e| e.id == exec_id);
        let Some(exec) = exec else {
            anyhow::bail!("Execution {} not found", exec_id);
        };

        exec.observation = observation.to_string();
        exec.verifier_pass = verifier_pass;
        exec.reward = Some(reward);
        exec.tool_calls = tool_calls;
        exec.status = if verifier_pass {
            ExecutionStatus::Verified
        } else {
            ExecutionStatus::Completed
        };

        Ok(exec)
    }

    /// Step 4: GRPO hierarchical reward optimization
    ///   J(θ) = E[ΣA(z) + ΣA(aₜ) − β·DKL]
    pub fn grpo_update(&mut self, z_id: &str) -> GRPOState {
        let executions: Vec<_> = self
            .executions
            .iter()
            .filter(|e| e.z_id == z_id && e.reward.is_some())
            .collect();

        if executions.is_empty() {
            return GRPOState::default();
        }

        let sum_aat: f64 = executions.iter().filter_map(|e| e.reward).sum();

        // Strategy reward = mean of child execution rewards
        let sum_az = sum_aat / executions.len() as f64;

        // KL penalty: mock as small constant scaled by iteration count
        let iterations = executions.len() as u32;
        let kl_penalty = self.config.beta_kl * (iterations as f64 * 0.02).min(0.5);

        let J_theta = sum_az + sum_aat - kl_penalty;

        self.grpo = GRPOState {
            z_id: z_id.to_string(),
            theta: 1.0,
            beta: self.config.beta_kl,
            sum_az,
            sum_aat,
            kl_penalty,
            J_theta,
            iterations,
        };

        self.grpo.clone()
    }

    /// Step 5: MemLLM — RAG + Long-Term Memory sync
    pub fn memory_sync(&mut self, agent_id: &str, exec_id: &str) -> Result<&MemLLM> {
        let exec = self.executions.iter_mut().find(|e| e.id == exec_id);
        let Some(exec) = exec else {
            anyhow::bail!("Execution {} not found", exec_id);
        };

        let mem = self
            .memories
            .entry(agent_id.to_string())
            .or_insert_with(MemLLM::default);

        mem.sync_status = SyncStatus::Syncing;

        // Short-term: add execution as new memory entry
        let entry = MemoryEntry {
            id: generate_id(),
            content: format!(
                "[EXEC id={} agent={} task={} reward={:.3} verified={} observation={}]",
                exec.id,
                exec.agent_id,
                exec.task_id,
                exec.reward.unwrap_or(0.0),
                exec.verifier_pass,
                truncate(&exec.observation, 200)
            ),
            content_hash: hash_str(&exec.observation),
            vector_k: mock_embedding(&exec.observation, 8), // 8-dim mock embedding
            created_at: exec.timestamp,
            access_count: 1,
            value_score: exec.reward.unwrap_or(0.0),
            locked: exec.reward.unwrap_or(0.0) >= 0.8, // High reward → lock
        };

        mem.short_term.push(entry);

        // Evict old short-term if over capacity
        while mem.short_term.len() > self.config.max_short_term {
            // Keep locked entries
            if let Some(idx) = mem.short_term.iter().position(|e| !e.locked) {
                mem.short_term.remove(idx);
            } else {
                break;
            }
        }

        // Promote high-value entries to long-term
        for entry in mem.short_term.iter() {
            if entry.value_score >= 0.75 && entry.access_count >= 3 {
                // Check not already in long_term
                if !mem
                    .long_term
                    .iter()
                    .any(|e| e.content_hash == entry.content_hash)
                {
                    let mut promoted = entry.clone();
                    promoted.id = generate_id();
                    mem.long_term.push(promoted);
                }
            }
        }

        // Long-term capacity eviction (value-score floor)
        while mem.long_term.len() > self.config.max_long_term {
            if let Some(idx) = mem
                .long_term
                .iter()
                .position(|e| e.value_score < self.config.value_score_floor && !e.locked)
            {
                mem.long_term.remove(idx);
            } else {
                break;
            }
        }

        mem.sync_status = SyncStatus::Synced;
        exec.memory_synced = true;

        Ok(mem)
    }

    /// Step 6: Self-verification before declaring completion
    ///   Re-substitute into main formula — if incomplete, redo
    pub fn verify_completion(&self, z_id: &str) -> VerificationResult {
        if self.strategies.iter().find(|s| s.id == z_id).is_none() {
            return VerificationResult {
                complete: false,
                reason: "Strategy not found".to_string(),
                completion_rate: 0.0,
            };
        };

        let executions: Vec<_> = self.executions.iter().filter(|e| &e.z_id == z_id).collect();

        let total = executions.len();
        let verified = executions
            .iter()
            .filter(|e| e.status == ExecutionStatus::Verified)
            .count();
        let reward_sum: f64 = executions.iter().filter_map(|e| e.reward).sum();
        let mean_reward = if total > 0 {
            reward_sum / total as f64
        } else {
            0.0
        };

        let completion_rate = if total > 0 {
            verified as f64 / total as f64
        } else {
            0.0
        };
        let complete = verified == total && mean_reward >= self.config.min_reward_threshold;

        VerificationResult {
            complete,
            reason: if complete {
                "All tasks verified, mean_reward adequate".to_string()
            } else {
                format!(
                    "{}/{} verified, mean_reward={:.3}",
                    verified, total, mean_reward
                )
            },
            completion_rate,
        }
    }

    /// Full StraTA cycle: z → aₜ → GRPO → MemLLM → verify
    pub fn run_cycle(
        &mut self,
        s1: &str,
        agent_ids: &[&str],
        tasks: &[(&str, &str)],
    ) -> CycleResult {
        let strategy = self.generate_strategy(s1, agent_ids).unwrap();
        let z_id = strategy.id.clone();

        let exec_ids: Vec<String> = self.dispatch_tasks(&z_id, tasks);

        let mut exec_results = Vec::new();
        for (i, (agent_id, _task_desc)) in tasks.iter().enumerate() {
            let exec_id = &exec_ids[i];
            let mock_reward = 0.75;
            let mock_verified = mock_reward >= 0.5;

            self.record_execution(
                exec_id,
                &format!("Observation: task completed OK"),
                mock_verified,
                mock_reward,
                vec!["tool_a".to_string(), "tool_b".to_string()],
            )
            .ok();

            self.memory_sync(agent_id, exec_id).ok();
            exec_results.push(exec_id.clone());
        }

        let grpo = self.grpo_update(&z_id);
        let verification = self.verify_completion(&z_id);

        CycleResult {
            z_id,
            exec_ids: exec_results,
            grpo: grpo.clone(),
            verification: verification.clone(),
            J_theta: grpo.J_theta,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerificationResult {
    pub complete: bool,
    pub reason: String,
    pub completion_rate: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CycleResult {
    pub z_id: String,
    pub exec_ids: Vec<String>,
    pub grpo: GRPOState,
    pub verification: VerificationResult,
    pub J_theta: f64,
}

// ============================================================
// UTILITIES
// ============================================================

fn generate_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    format!("{:x}", now)
}

fn hash_str(s: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(s.as_bytes());
    format!("{:x}", hasher.finalize())
}

fn unix_ts() -> i64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs() as i64
}

fn truncate(s: &str, max: usize) -> String {
    if s.len() <= max {
        s.to_string()
    } else {
        format!("{}...", &s[..max.saturating_sub(3)])
    }
}

/// Mock K-dimensional embedding ( cosine-simulate with random weights )
fn mock_embedding(s: &str, k: usize) -> Vec<f64> {
    let mut v = vec![0.0; k];
    for (i, c) in s.bytes().enumerate() {
        let idx = i % k;
        v[idx] += (c as f64 - 64.0) / 128.0;
    }
    // Normalize
    let mag = v.iter().map(|x| x * x).sum::<f64>().sqrt().max(1e-6);
    for x in &mut v {
        *x /= mag;
    }
    v
}

// ============================================================
// TESTS
// ============================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_strategy_generation() {
        let mut engine = StraTAEngine::new();
        let agents = ["agent_a", "agent_b"];
        let strat = engine
            .generate_strategy("Build a CSV parser from URLs", &agents)
            .unwrap();
        assert_eq!(strat.status, StrategyStatus::Dispatched);
        assert_eq!(strat.agents_committed.len(), 2);
    }

    #[test]
    fn test_task_dispatch_and_execution() {
        let mut engine = StraTAEngine::new();
        let strat = engine
            .generate_strategy("Build a CSV parser", &["a", "b"])
            .unwrap();
        let z_id = strat.id.clone();

        let tasks = [
            ("agent_a", "Download CSV from URL list"),
            ("agent_b", "Parse and save CSV"),
        ];
        let dispatched = engine.dispatch_tasks(&z_id, &tasks);
        assert_eq!(dispatched.len(), 2);

        // Record execution
        engine
            .record_execution(
                &dispatched[0],
                "Download complete",
                true,
                0.85,
                vec!["wget".to_string()],
            )
            .unwrap();
        engine
            .record_execution(
                &dispatched[1],
                "Parse OK",
                true,
                0.78,
                vec!["csv_parser".to_string()],
            )
            .unwrap();

        let grpo = engine.grpo_update(&z_id);
        assert!(grpo.J_theta > 0.0, "GRPO J(θ) should be positive");
    }

    #[test]
    fn test_memory_sync() {
        let mut engine = StraTAEngine::new();
        let strat = engine
            .generate_strategy("Build a CSV parser", &["a"])
            .unwrap();
        let z_id = strat.id.clone();
        let dispatched = engine.dispatch_tasks(&z_id, &[("agent_a", "Download CSV")]);
        let exec_id = dispatched[0].clone();

        engine
            .record_execution(
                &exec_id,
                "Downloaded 50 rows",
                true,
                0.82,
                vec!["wget".to_string()],
            )
            .unwrap();
        engine.memory_sync("agent_a", &exec_id).unwrap();

        let mem = engine.memories.get("agent_a").unwrap();
        assert_eq!(mem.sync_status, SyncStatus::Synced);
        assert!(!mem.short_term.is_empty());
    }

    #[test]
    fn test_verification_complete() {
        let mut engine = StraTAEngine::new();
        let strat = engine
            .generate_strategy("Build a CSV parser", &["a", "b"])
            .unwrap();
        let z_id = strat.id.clone();
        let dispatched = engine.dispatch_tasks(&z_id, &[("a", "task1"), ("b", "task2")]);

        for d in &dispatched {
            engine.record_execution(d, "OK", true, 0.8, vec![]).unwrap();
        }
        engine.grpo_update(&z_id);

        let result = engine.verify_completion(&z_id);
        assert!(
            result.complete,
            "Both verified → should be complete: {}",
            result.reason
        );
        assert!((result.completion_rate - 1.0).abs() < 1e-6);
    }

    #[test]
    fn test_verification_incomplete() {
        let mut engine = StraTAEngine::new();
        let strat = engine
            .generate_strategy("Build a CSV parser", &["a"])
            .unwrap();
        let z_id = strat.id.clone();
        let dispatched = engine.dispatch_tasks(&z_id, &[("a", "task1")]);

        // Record FAILED execution (reward too low)
        engine
            .record_execution(&dispatched[0], "Failed", false, 0.1, vec![])
            .unwrap();
        engine.grpo_update(&z_id);

        let result = engine.verify_completion(&z_id);
        assert!(!result.complete);
        assert!(result.completion_rate < 1.0);
    }

    #[test]
    fn test_full_cycle() {
        let mut engine = StraTAEngine::new();
        let agents = ["agent_a", "agent_b", "agent_c"];
        let tasks = [
            ("agent_a", "Download product images"),
            ("agent_b", "Parse URLs and validate"),
            ("agent_c", "Write CSV output"),
        ];

        let result = engine.run_cycle("Bulk download images from spreadsheet", &agents, &tasks);
        assert!(
            result.verification.complete,
            "Full cycle should complete: {}",
            result.verification.reason
        );
        assert!(result.exec_ids.len() == 3);
        assert!(result.J_theta > 0.0);
    }

    #[test]
    fn test_grpo_kl_penalty() {
        let mut engine = StraTAEngine::new();
        let strat = engine
            .generate_strategy("Multi-task pipeline", &["a", "b", "c"])
            .unwrap();
        let z_id = strat.id.clone();
        let dispatched =
            engine.dispatch_tasks(&z_id, &[("a", "task1"), ("b", "task2"), ("c", "task3")]);

        for (i, d) in dispatched.iter().enumerate() {
            engine
                .record_execution(d, "OK", true, 0.7 + i as f64 * 0.05, vec![])
                .unwrap();
        }

        let grpo = engine.grpo_update(&z_id);
        // J = sum_az + sum_aat - beta*DKL
        // sum_az ≈ 0.775, sum_aat ≈ 2.4, kl ≤ 0.5
        assert!(
            grpo.J_theta > 2.0,
            "J_theta={:.3} should exceed 2.0",
            grpo.J_theta
        );
        assert!(grpo.kl_penalty >= 0.0 && grpo.kl_penalty <= 0.5);
    }

    #[test]
    fn test_idempotent_strategy() {
        let mut engine = StraTAEngine::new();
        let s1 = "Parse Excel URLs into download pipeline";
        let strat1 = engine.generate_strategy(s1, &["a"]).unwrap();
        let hash1 = strat1.z_hash.clone();
        let strat2 = engine.generate_strategy(s1, &["a"]).unwrap();
        // Same s1 → same z_hash (idempotent generation)
        assert_eq!(
            hash1, strat2.z_hash,
            "Identical s1 should produce identical z_hash"
        );
    }

    #[test]
    fn test_memory_value_lock() {
        let mut engine = StraTAEngine::new();
        let strat = engine.generate_strategy("High-value task", &["a"]).unwrap();
        let z_id = strat.id.clone();
        let dispatched = engine.dispatch_tasks(&z_id, &[("a", "Critical task")]);

        // Very high reward → should be locked
        engine
            .record_execution(&dispatched[0], "Perfect", true, 0.95, vec![])
            .unwrap();
        engine.memory_sync("a", &dispatched[0]).unwrap();

        let mem = engine.memories.get("a").unwrap();
        assert!(
            mem.short_term.iter().any(|e| e.locked),
            "High reward entry should be locked"
        );
    }
}
