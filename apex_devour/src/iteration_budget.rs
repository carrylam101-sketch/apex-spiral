use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// APEX Iteration Budget Gate
/// Gene 602: APEX dependency chain root
/// 
/// Addresses: Hermite iteration cut-off / max_iterations truncation risk.
/// Aims to provide budget-aware intervention before hard cut-off.
/// 
/// NOT integrated with Hermes Agent internals (run_agent.py / model_tools.py)
/// — this is a standalone measurement gate that can be called from external code.
/// 
/// Boundary: This gate does NOT modify agent behavior.
/// It measures and reports budget risk only.

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IterationRecord {
    pub task_id: String,
    pub iteration_count: u32,
    pub tool_calls: u32,
    pub checkpoint_triggered: bool,
    pub truncation_risk: f64,
}

/// Budget configuration thresholds
#[derive(Debug, Clone)]
pub struct BudgetConfig {
    pub budget_low: u32,      // Warn: 70% of budget consumed
    pub budget_medium: u32,   // Alert: 85% of budget consumed
    pub budget_high: u32,     // Critical: 95% of budget consumed
    pub max_iterations: u32,  // Hard cut-off
}

impl Default for BudgetConfig {
    fn default() -> Self {
        Self {
            budget_low: 70,         // 70% → warn
            budget_medium: 85,      // 85% → alert  
            budget_high: 95,        // 95% → critical
            max_iterations: 100,    // 100 → hard cut
        }
    }
}

/// Intervention level based on budget consumption
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum InterventionLevel {
    Normal,   // < 70% consumed
    Low,      // 70-84%
    Medium,   // 85-94%
    High,     // 95-99%
    Critical, // 100% (hard cut)
}

impl InterventionLevel {
    pub fn from_percent(pct: f64) -> Self {
        if pct < 70.0 {
            InterventionLevel::Normal
        } else if pct < 85.0 {
            InterventionLevel::Low
        } else if pct < 95.0 {
            InterventionLevel::Medium
        } else if pct < 100.0 {
            InterventionLevel::High
        } else {
            InterventionLevel::Critical
        }
    }

    pub fn label(&self) -> &'static str {
        match self {
            InterventionLevel::Normal => "normal",
            InterventionLevel::Low => "low_warn",
            InterventionLevel::Medium => "medium_alert",
            InterventionLevel::High => "high_critical",
            InterventionLevel::Critical => "critical_truncate",
        }
    }
}

/// Budget gate result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BudgetGateOutput {
    pub iteration_count: u32,
    pub max_iterations: u32,
    pub budget_remaining: u32,
    pub budget_consumed_pct: f64,
    pub intervention_level: String,
    pub truncation_risk: f64,
    pub should_checkpoint: bool,
    pub should_truncate: bool,
    pub intervention_credit: f64,
}

impl BudgetGateOutput {
    pub fn new(iter_count: u32, max_iter: u32, checkpoint: bool) -> Self {
        let budget_remaining = max_iter.saturating_sub(iter_count);
        let pct = if max_iter > 0 {
            ((iter_count as f64 / max_iter as f64) * 100.0).min(100.0)
        } else {
            100.0
        };
        let level = InterventionLevel::from_percent(pct);
        let risk = pct / 100.0;
        
        // Truncation risk: 0.0 when normal, grows with intervention level
        let trunc_risk = match level {
            InterventionLevel::Normal => 0.0,
            InterventionLevel::Low => 0.1,
            InterventionLevel::Medium => 0.3,
            InterventionLevel::High => 0.6,
            InterventionLevel::Critical => 1.0,
        };
        
        // Checkpoint recommended at Medium or above, or at High budget
        let should_checkpoint = matches!(
            level,
            InterventionLevel::Medium | InterventionLevel::High | InterventionLevel::Critical
        ) || pct >= 85.0;
        
        // Truncate flag when at max
        let should_truncate = iter_count >= max_iter;
        
        // Credit: higher when checkpoint is recommended and not yet at critical
        let credit = match level {
            InterventionLevel::Normal => 0.0,
            InterventionLevel::Low => 0.1 * if should_checkpoint { 1.0 } else { 0.5 },
            InterventionLevel::Medium => 0.25 * if should_checkpoint { 1.0 } else { 0.8 },
            InterventionLevel::High => 0.45 * if should_checkpoint { 1.0 } else { 0.5 },
            InterventionLevel::Critical => 0.6,
        };
        
        Self {
            iteration_count: iter_count,
            max_iterations: max_iter,
            budget_remaining,
            budget_consumed_pct: pct,
            intervention_level: level.label().to_string(),
            truncation_risk: trunc_risk,
            should_checkpoint,
            should_truncate,
            intervention_credit: credit,
        }
    }
}

/// APEX Integration: compute G_apex_iteration_budget
/// G_apex_ib = 1 + 0.03 * (1 - truncation_risk) - 0.02 * truncation_risk
/// When truncation_risk=0 (normal): G_ib=1.03
/// When truncation_risk=1 (critical): G_ib=0.99
pub fn compute_g_apex_ib(output: &BudgetGateOutput) -> f64 {
    let base = 1.0;
    let pos = 0.03 * (1.0 - output.truncation_risk);
    let neg = 0.02 * output.truncation_risk;
    base + pos - neg
}

/// Evaluate a batch of iteration records and compute aggregate metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IterationBudgetReport {
    pub n_records: usize,
    pub n_normal: usize,
    pub n_low: usize,
    pub n_medium: usize,
    pub n_high: usize,
    pub n_critical: usize,
    pub n_checkpoint: usize,
    pub n_truncate: usize,
    pub mean_truncation_risk: f64,
    pub mean_credit: f64,
    pub g_apex_ib: f64,
}

impl IterationBudgetReport {
    pub fn from_records(records: &[IterationRecord], max_iter: u32) -> Self {
        let mut n_normal = 0;
        let mut n_low = 0;
        let mut n_medium = 0;
        let mut n_high = 0;
        let mut n_critical = 0;
        let mut n_checkpoint = 0;
        let mut n_truncate = 0;
        let mut sum_risk = 0.0;
        let mut sum_credit = 0.0;
        
        for rec in records {
            let output = BudgetGateOutput::new(rec.iteration_count, max_iter, rec.checkpoint_triggered);
            match output.intervention_level.as_str() {
                "normal" => n_normal += 1,
                "low_warn" => n_low += 1,
                "medium_alert" => n_medium += 1,
                "high_critical" => n_high += 1,
                "critical_truncate" => n_critical += 1,
                _ => {}
            }
            if output.should_checkpoint { n_checkpoint += 1; }
            if output.should_truncate { n_truncate += 1; }
            sum_risk += output.truncation_risk;
            sum_credit += output.intervention_credit;
        }
        
        let n = records.len().max(1);
        let mean_risk = sum_risk / n as f64;
        let mean_credit = sum_credit / n as f64;
        let g_ib = 1.0 + 0.03 * (1.0 - mean_risk) - 0.02 * mean_risk;
        
        Self {
            n_records: n,
            n_normal,
            n_low,
            n_medium,
            n_high,
            n_critical,
            n_checkpoint,
            n_truncate,
            mean_truncation_risk: mean_risk,
            mean_credit,
            g_apex_ib: g_ib,
        }
    }
}

// ---- CLI helpers ----

pub fn parse_records_from_args(args: &[String]) -> Vec<IterationRecord> {
    let mut records = Vec::new();
    let mut i = 0;
    while i < args.len() {
        if args[i] == "--input" && i + 1 < args.len() {
            // Read from JSON file
            let path = &args[i + 1];
            if let Ok(content) = std::fs::read_to_string(path) {
                if let Ok(parsed) = serde_json::from_str::<Vec<serde_json::Value>>(&content) {
                    for v in parsed {
                        let task_id = v.get("task_id")
                            .or_else(|| v.get("session_id"))
                            .and_then(|x| x.as_str())
                            .unwrap_or("unknown")
                            .to_string();
                        let iter_count = v.get("iteration_count")
                            .or_else(|| v.get("iter_count"))
                            .and_then(|x| x.as_u64())
                            .unwrap_or(0) as u32;
                        let tool_calls = v.get("tool_calls")
                            .and_then(|x| x.as_u64())
                            .unwrap_or(0) as u32;
                        let checkpoint = v.get("checkpoint_triggered")
                            .and_then(|x| x.as_bool())
                            .unwrap_or(false);
                        records.push(IterationRecord {
                            task_id,
                            iteration_count: iter_count,
                            tool_calls,
                            checkpoint_triggered: checkpoint,
                            truncation_risk: 0.0, // computed from BudgetGateOutput
                        });
                    }
                }
            }
            i += 2;
        } else {
            i += 1;
        }
    }
    records
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_intervention_levels() {
        assert_eq!(InterventionLevel::from_percent(50.0), InterventionLevel::Normal);
        assert_eq!(InterventionLevel::from_percent(72.0), InterventionLevel::Low);
        assert_eq!(InterventionLevel::from_percent(88.0), InterventionLevel::Medium);
        assert_eq!(InterventionLevel::from_percent(97.0), InterventionLevel::High);
        assert_eq!(InterventionLevel::from_percent(100.0), InterventionLevel::Critical);
    }

    #[test]
    fn test_budget_gate_normal() {
        let out = BudgetGateOutput::new(20, 100, false);
        assert_eq!(out.intervention_level, "normal");
        assert_eq!(out.truncation_risk, 0.0);
        assert!(!out.should_checkpoint);
        assert!(!out.should_truncate);
        assert!(out.intervention_credit < 0.01);
    }

    #[test]
    fn test_budget_gate_medium() {
        let out = BudgetGateOutput::new(88, 100, false);
        assert_eq!(out.intervention_level, "medium_alert");
        assert!((out.truncation_risk - 0.3).abs() < 0.01);
        assert!(out.should_checkpoint);
        assert!(!out.should_truncate);
        assert!(out.intervention_credit > 0.1);
    }

    #[test]
    fn test_budget_gate_critical() {
        let out = BudgetGateOutput::new(100, 100, false);
        assert_eq!(out.intervention_level, "critical_truncate");
        assert_eq!(out.truncation_risk, 1.0);
        assert!(out.should_truncate);
        assert!(out.intervention_credit > 0.5);
    }

    #[test]
    fn test_g_apex_ib() {
        let normal = BudgetGateOutput::new(20, 100, false);
        let critical = BudgetGateOutput::new(100, 100, false);
        let g_normal = compute_g_apex_ib(&normal);
        let g_critical = compute_g_apex_ib(&critical);
        assert!(g_normal > 1.0);
        assert!(g_critical < 1.0);
        assert!(g_normal > g_critical);
    }

    #[test]
    fn test_iteration_budget_report() {
        let records = vec![
            IterationRecord { task_id: "t1".into(), iteration_count: 20, tool_calls: 30, checkpoint_triggered: false, truncation_risk: 0.0 },
            IterationRecord { task_id: "t2".into(), iteration_count: 88, tool_calls: 120, checkpoint_triggered: false, truncation_risk: 0.0 },
            IterationRecord { task_id: "t3".into(), iteration_count: 100, tool_calls: 150, checkpoint_triggered: true, truncation_risk: 0.0 },
        ];
        let report = IterationBudgetReport::from_records(&records, 100);
        assert_eq!(report.n_records, 3);
        assert_eq!(report.n_normal, 1);
        assert_eq!(report.n_medium, 1);
        assert_eq!(report.n_critical, 1);
        // record 2 (88%) triggers checkpoint (>= 85.0); record 3 (100%) triggers checkpoint (>= 85.0)
        assert_eq!(report.n_checkpoint, 2);
        assert_eq!(report.n_truncate, 1);
        assert!(report.g_apex_ib > 0.98 && report.g_apex_ib < 1.05);
    }

    #[test]
    fn test_saturation_handling() {
        // Over-saturation (iterations > max) should be clamped
        let out = BudgetGateOutput::new(150, 100, false);
        assert_eq!(out.budget_consumed_pct, 100.0);
        assert_eq!(out.budget_remaining, 0);
        assert_eq!(out.intervention_level, "critical_truncate");
        assert!(out.should_truncate);
    }
}