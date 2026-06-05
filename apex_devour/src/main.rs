//! APEX Devour Evolution Engine — Core CLI
//! Self-evolution by absorbing mechanisms from high-quality Agentic RL / coding-agent repos.
//! Formula: D_devour = Q_source · M_mech · A_impl · V_audit · T_transfer
//!        G_devour = 1 + 0.08·D_devour - 0.05·Ω_risk
//!        ΔG_candidate = ΔG_current × G_devour

use anyhow::Result;
use clap::{Parser, Subcommand};
use std::path::PathBuf;
mod apex_gate;
mod apex_gate_health;
mod apex_gate_registry;
mod auto_repair;
mod credit;
mod devour;
mod iteration_budget;
mod hybrid_retrieval;
mod maintenance;
mod mcp_client;
mod reflection;
mod resolution;
mod straTA;
mod vlm_agentic;

pub use auto_repair::{AutoRepairEngine, AutoRepairInput, AutoRepairResult};
pub use apex_gate::ApexGate;
pub use credit::{CreditAssigner, TrajectoryStep};
pub use devour::{DevourEngine, SourceDigest};
pub use hybrid_retrieval::{HybridRetrievalGate, HybridRetrievalInput, HybridRetrievalReport};
pub use maintenance::{MaintenanceGate, MaintenanceSession};
pub use reflection::{ReflectionAttempt, ReflectionGate};
pub use resolution::{IssueResolutionRun, ResolutionGate};
pub use vlm_agentic::{VLMCorrectionReport, VLMTrajectoryStep};
pub use straTA::{
    CycleResult, ExecutionStatus, GRPOState, MemLLM, MemoryEntry, StraTAEngine, Strategy,
    StrategyStatus, SyncStatus, TaskExecution, VerificationResult,
};

/// APEX Devour CLI
#[derive(Parser, Debug)]
#[command(name = "apex_devour")]
#[command(about = "APEX 吞噬自进化引擎: source → mechanism → APEX gate → measurable evidence")]
struct Cli {
    #[command(subcommand)]
    cmd: Command,
}

#[derive(Subcommand, Debug)]
enum Command {
    /// Health check and formula declaration
    Health,
    /// Devour a source: evaluate Q_source · M_mech · A_impl · V_audit · T_transfer
    Devour {
        #[arg(long)]
        repo: String,
        #[arg(long)]
        stars: u64,
        #[arg(long)]
        mechanism: String,
        #[arg(long)]
        apex_mapping: Vec<String>,
        #[arg(long)]
        impl_status: String, // "native_rust", "python_glue", "concept_only", "not_started"
        #[arg(long)]
        audit_status: String, // "test_pass", "partial", "none"
        #[arg(long)]
        transferrable: bool,
        #[arg(long)]
        risk_flags: Vec<String>,
    },
    /// Compute ΔG candidate from current ΔG and G_devour
    DeltaG {
        #[arg(long)]
        delta_g_current: f64,
        #[arg(long)]
        g_devour: f64,
    },
    /// Assign Agentic-RL-style credit from a trajectory JSON file
    Credit {
        #[arg(long)]
        input: PathBuf,
    },
    /// Evaluate Reflexion-style verbal reflection memory from attempts JSON
    Reflection {
        #[arg(long)]
        input: PathBuf,
    },
    /// Evaluate self-improving coding-agent maintenance sessions JSON
    Maintenance {
        #[arg(long)]
        input: PathBuf,
    },
    /// Evaluate issue→patch→test resolution runs JSON
    Resolution {
        #[arg(long)]
        input: PathBuf,
    },
    /// VLM-Agentic self-correction gate: GUI/VLM agent trajectory self-correction evaluation
    VLM {
        #[arg(long)]
        input: PathBuf,
    },
    /// StraTA: Strategic Tiered Agent — Bee Queen Swarm Mode
    StraTA {
        #[arg(long)]
        s1: String,
        #[arg(long, num_args=1.., value_delimiter=',')]
        agents: Vec<String>,
        #[arg(long, value_delimiter = ';')]
        tasks: Vec<String>, // "agent_id|task_desc;agent_id|task_desc"
    },
    /// Report current devour pipeline status
    Status,
    /// Full APEX gate: EVM health check + Neuro-Cell + Self Loop + Devour → ΔG candidate
    Gate {
        #[arg(long)]
        evm_refresh: bool,
        #[arg(long)]
        output: Option<PathBuf>,
    },
    /// Iteration Budget gate: budget-aware intervention measurement (Gene 602)
    IterationBudget {
        /// JSON file with iteration records (array of task/session objects with iteration_count)
        #[arg(long)]
        input: Option<PathBuf>,
        /// Current iteration count (for single-record mode)
        #[arg(long)]
        iter_count: Option<u32>,
        /// Max iterations budget (default: 100)
        #[arg(long)]
        max_iter: Option<u32>,
    },
    /// Hybrid Retrieval gate: fuse BM25 + vector + graph hits via weighted RRF
    HybridRetrieval {
        /// JSON file with bm25/vector/graph hit arrays
        #[arg(long)]
        input: PathBuf,
    },
    /// APEX Gate Registry: pre-check for tool dispatch (EV/SV/harm gates)
    GateRegistry {
        /// JSON file with tool SV ratios: [{"tool": "name", "sv_ratio": 0.5}, ...]
        #[arg(long)]
        input: Option<PathBuf>,
        /// Tool name for single-record mode
        #[arg(long)]
        tool: Option<String>,
        /// SV ratio (0.0–1.0+) for single-record mode
        #[arg(long)]
        sv_ratio: Option<f64>,
    },
    /// Auto-repair: closed-loop cargo check → cargo fix until clean or stuck (nanoGPT-claw pattern)
    AutoRepair {
        /// Working directory for cargo commands (defaults to current dir)
        #[arg(long)]
        workdir: Option<PathBuf>,
        /// Maximum repair iterations (default: 10)
        #[arg(long)]
        max_iterations: Option<usize>,
    },
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.cmd {
        Command::Health => {
            println!("APEX Devour Evolution Engine v0.1.0");
            println!("Formula: D_devour = Q_source · M_mech · A_impl · V_audit · T_transfer");
            println!("        G_devour = 1 + 0.08·D_devour - 0.05·Ω_risk");
            println!("        ΔG_candidate = ΔG_current × G_devour");
            println!();
            println!("EVM health: defect_rate ≤ 0.083 (no critical defects)");
            println!("Neuro-Cell Gate: G_neuro ≥ 1.0");
            println!("Self Loop: G_self ≥ 1.0");
            println!("Devour: G_devour ≥ 1.0 → positive gain from external mechanism absorption");
            println!();
            println!("Gate thresholds:");
            println!("  Q_source  (0-1): stars/activity/benchmark. >0.70 = high quality source");
            println!("  M_mech    (0-1): mechanism understanding completeness. >0.65 = deployable");
            println!("  A_impl    (0-1): Rust/Go/C implementation status. >0.50 = in-progress");
            println!("  V_audit   (0-1): test/lint/sandbox verification. >0.60 = audited");
            println!("  T_transfer(0-1): transferability to CLAW/Hermes. >0.60 = transferable");
            println!(
                "  Ω_risk    (0-1): supply chain/license/hallucination risk. <0.20 = acceptable"
            );
            Ok(())
        }
        Command::Devour {
            repo,
            stars,
            mechanism,
            apex_mapping,
            impl_status,
            audit_status,
            transferrable,
            risk_flags,
        } => {
            let mut engine = DevourEngine::default();
            let digest = SourceDigest {
                repo,
                stars_observed: stars,
                mechanism,
                apex_mapping,
                impl_status,
                audit_status,
                transferrable,
                risk_flags,
            };
            let result = engine.devour(digest)?;
            println!("{}", serde_json::to_string_pretty(&result)?);
            Ok(())
        }
        Command::DeltaG {
            delta_g_current,
            g_devour,
        } => {
            let gate = ApexGate::new();
            let candidate = gate.compute_delta_g_candidate(delta_g_current, g_devour);
            println!("ΔG_current = {}", delta_g_current);
            println!("G_devour    = {:.4}", g_devour);
            println!("ΔG_candidate= {:.4}", candidate);
            Ok(())
        }
        Command::Credit { input } => {
            let raw = std::fs::read_to_string(&input)?;
            let steps: Vec<TrajectoryStep> = serde_json::from_str(&raw)?;
            let report = CreditAssigner::assign(&steps);
            println!("{}", serde_json::to_string_pretty(&report)?);
            Ok(())
        }
        Command::Reflection { input } => {
            let raw = std::fs::read_to_string(&input)?;
            let attempts: Vec<ReflectionAttempt> = serde_json::from_str(&raw)?;
            let report = ReflectionGate::evaluate(&attempts);
            println!("{}", serde_json::to_string_pretty(&report)?);
            Ok(())
        }
        Command::Maintenance { input } => {
            let raw = std::fs::read_to_string(&input)?;
            let sessions: Vec<MaintenanceSession> = serde_json::from_str(&raw)?;
            let report = MaintenanceGate::evaluate(&sessions);
            println!("{}", serde_json::to_string_pretty(&report)?);
            Ok(())
        }
        Command::Resolution { input } => {
            let raw = std::fs::read_to_string(&input)?;
            let runs: Vec<IssueResolutionRun> = serde_json::from_str(&raw)?;
            let report = ResolutionGate::evaluate(&runs);
            println!("{}", serde_json::to_string_pretty(&report)?);
            Ok(())
        }
        Command::VLM { input } => {
            let raw = std::fs::read_to_string(&input)?;
            let steps: Vec<VLMTrajectoryStep> = serde_json::from_str(&raw)?;
            let report = vlm_agentic::evaluate(&steps);
            println!("{}", serde_json::to_string_pretty(&report)?);
            Ok(())
        }
        Command::StraTA { s1, agents, tasks } => {
            let parsed_tasks: Vec<(&str, &str)> = tasks
                .iter()
                .filter_map(|t| {
                    let parts: Vec<&str> = t.split('|').collect();
                    if parts.len() == 2 {
                        Some((parts[0].trim(), parts[1].trim()))
                    } else {
                        None
                    }
                })
                .collect();
            if parsed_tasks.is_empty() {
                anyhow::bail!("No valid tasks parsed from --tasks. Format: 'agent_id|task_desc;agent_id|task_desc'");
            }
            let agent_refs: Vec<&str> = agents.iter().map(|s| s.as_str()).collect();
            let mut engine = StraTAEngine::new();
            let result = engine.run_cycle(&s1, &agent_refs, &parsed_tasks);
            println!("ApexStraTA = π(z|s₁) ⊗ π(aₜ|z,sₜ) ⊗ GRPO(z,aₜ) ⊗ MemLLM");
            println!("z_id        = {}", result.z_id);
            println!("exec_ids    = {:?}", result.exec_ids);
            println!("J(θ)        = {:.4}", result.J_theta);
            println!("complete    = {}", result.verification.complete);
            println!("reason      = {}", result.verification.reason);
            println!(
                "rate        = {:.1}%",
                result.verification.completion_rate * 100.0
            );
            Ok(())
        }
        Command::Status => {
            println!("APEX Devour Status: operational");
            println!("Pipeline: source_digest → mechanism_analysis → devour_assess → G_devour → ΔG_candidate");
            println!("Known sources: OpenHands(74.6k★), SWE-agent(19.3k★), Voyager(6.9k★), Reflexion(3.2k★)");
            Ok(())
        }
        Command::Gate { evm_refresh, output } => {
            use apex_gate_health::{write_report, ApexGateReport};
            let mut report = ApexGateReport::from_registry();
            if evm_refresh {
                report.refresh_from_evm();
            }
            report.run_gate_checks();
            report.compute_delta_g();

            println!("APEX Gate Report v0.1.0");
            println!("ΔG_current      = {:.4}", report.delta_g_current);
            println!("G_neuro         = {:.4}", report.g_neuro);
            println!("G_self          = {:.4}", report.g_self);
            println!("G_evm           = {:.4}", report.g_evm);
            println!("G_devour        = {:.4}", report.g_devour);
            println!("ΔG_candidate    = {:.4}", report.delta_g_candidate);
            println!("gate_open       = {}", report.gate_open);
            if report.evm_status.is_some() {
                let es = report.evm_status.as_ref().unwrap();
                println!("EVM_base        = {:.4}", es.evm_base);
                println!("defect_rate     = {:.4}", es.defect_rate);
                println!("Π_evm           = {:.4}", es.pi_evm);
                println!("Ω_defect        = {:.4}", es.omega_defect);
            }
            if !report.gates_passed.is_empty() {
                println!("gates_passed:");
                for g in &report.gates_passed {
                    println!("  ✓ {}", g);
                }
            }
            if !report.gates_failed.is_empty() {
                println!("gates_failed:");
                for g in &report.gates_failed {
                    println!("  ✗ {}", g);
                }
            }

            if let Some(path) = output {
                write_report(&report, &path)
                    .map_err(|e| anyhow::anyhow!("Failed to write report: {}", e))?;
                println!("Report written to: {}", path.display());
            }

            Ok(())
        }
        Command::IterationBudget { input, iter_count, max_iter } => {
            use iteration_budget::{
                BudgetGateOutput, IterationBudgetReport,
            };

            let max = max_iter.unwrap_or(100);

            if let Some(path) = input {
                // Batch mode: read JSON file of iteration records
                let content = std::fs::read_to_string(&path)
                    .map_err(|e| anyhow::anyhow!("Read error: {}", e))?;
                let records = iteration_budget::parse_records_from_args(
                    &["--input".to_string(), path.to_string_lossy().to_string()],
                );
                let report = IterationBudgetReport::from_records(&records, max);
                println!("IterationBudgetReport (batch)");
                println!("  n_records              = {}", report.n_records);
                println!("  n_normal               = {}", report.n_normal);
                println!("  n_low                  = {}", report.n_low);
                println!("  n_medium               = {}", report.n_medium);
                println!("  n_high                 = {}", report.n_high);
                println!("  n_critical             = {}", report.n_critical);
                println!("  n_checkpoint           = {}", report.n_checkpoint);
                println!("  n_truncate             = {}", report.n_truncate);
                println!("  mean_truncation_risk   = {:.4}", report.mean_truncation_risk);
                println!("  mean_credit            = {:.4}", report.mean_credit);
                println!("  G_apex_ib              = {:.4}", report.g_apex_ib);
                println!("  source                 = file:{}", path.display());
            } else if let Some(count) = iter_count {
                // Single-record mode
                let out = BudgetGateOutput::new(count, max, false);
                let g_ib = iteration_budget::compute_g_apex_ib(&out);
                println!("IterationBudget (single)");
                println!("  iteration_count        = {}", out.iteration_count);
                println!("  max_iterations         = {}", out.max_iterations);
                println!("  budget_consumed_pct    = {:.2}%", out.budget_consumed_pct);
                println!("  intervention_level     = {}", out.intervention_level);
                println!("  truncation_risk         = {:.4}", out.truncation_risk);
                println!("  should_checkpoint      = {}", out.should_checkpoint);
                println!("  should_truncate         = {}", out.should_truncate);
                println!("  intervention_credit    = {:.4}", out.intervention_credit);
                println!("  G_apex_ib              = {:.4}", g_ib);
            } else {
                anyhow::bail!("Must provide either --input <file> or --iter-count <n>");
            }

            Ok(())
        }
        Command::HybridRetrieval { input } => {
            let raw = std::fs::read_to_string(&input)?;
            let retrieval_input: HybridRetrievalInput = serde_json::from_str(&raw)?;
            let report = HybridRetrievalGate::evaluate(&retrieval_input);
            println!("{}", serde_json::to_string_pretty(&report)?);
            Ok(())
        }
        Command::GateRegistry { input, tool, sv_ratio } => {
            use apex_gate_registry::{apex_gate, batch_gate_check, GateConfig, GateRegistryReport};

            let config = GateConfig::default();

            if let Some(path) = input {
                // Batch mode: read JSON file with tool SV pairs
                let content = std::fs::read_to_string(&path)
                    .map_err(|e| anyhow::anyhow!("Read error: {}", e))?;
                let parsed: Vec<serde_json::Value> = serde_json::from_str(&content)
                    .map_err(|e| anyhow::anyhow!("JSON parse error: {}", e))?;
                let tool_sv_pairs: Vec<(String, f64)> = parsed
                    .iter()
                    .filter_map(|v| {
                        let name = v.get("tool")?.as_str()?.to_string();
                        let sv = v.get("sv_ratio")?.as_f64()?;
                        Some((name, sv))
                    })
                    .collect();
                let report = batch_gate_check(&tool_sv_pairs, &config);
                println!("GateRegistryReport (batch)");
                println!("  total_checks          = {}", report.total_checks);
                println!("  allowed_count         = {}", report.allowed_count);
                println!("  rejected_count        = {}", report.rejected_count);
                println!("  mean_gate_credit      = {:.4}", report.mean_gate_credit);
                println!("  ev_pass_rate          = {:.4}", report.ev_pass_rate);
                println!("  sv_pass_rate          = {:.4}", report.sv_pass_rate);
                println!("  harm_pass_rate        = {:.4}", report.harm_pass_rate);
                println!("  mean_ev               = {:.4}", report.mean_ev);
                println!("  mean_sv_ratio         = {:.4}", report.mean_sv_ratio);
                println!("  G_apex_gr             = {:.4}", report.g_apex_gr);
                if !report.rejected_tools.is_empty() {
                    println!("  rejected_tools        = {:?}", report.rejected_tools);
                }
                println!("  source                = file:{}", path.display());
            } else if let (Some(t), Some(sv)) = (tool, sv_ratio) {
                // Single-record mode
                let result = apex_gate(&t, sv, &config);
                println!("GateRegistry (single)");
                println!("  tool_name             = {}", result.tool_name);
                println!("  allowed               = {}", result.allowed);
                println!("  ev_score              = {:.4}", result.ev_score);
                println!("  sv_ratio              = {:.4}", result.sv_ratio);
                println!("  harm_rate             = {:.4}", result.harm_rate);
                println!("  gate_credit           = {:.4}", result.gate_credit);
                if let Some(reason) = result.reject_reason {
                    println!("  reject_reason         = {}", reason);
                }
                println!("  G_apex_gr             = {:.4}", config.ev_threshold.max(1.0)); // placeholder per-gate
            } else {
                anyhow::bail!("Must provide either --input <json-file> or --tool <name> --sv-ratio <n>");
            }

            Ok(())
        }
        Command::AutoRepair { workdir, max_iterations } => {
            let input = AutoRepairInput {
                working_dir: workdir.map(|p| p.to_string_lossy().to_string()),
                max_iterations,
            };
            let engine = AutoRepairEngine::new();
            let result = engine.evaluate(input);
            println!("{}", serde_json::to_string_pretty(&result)?);
            Ok(())
        }
    }
}
