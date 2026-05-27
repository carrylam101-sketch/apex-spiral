//! APEX Gate Registry — Gene 603
//! Pre-check for registry.dispatch(): harm negation + SV resource + EV estimation.
//! Integration point: tools/registry.py dispatch() prefix.
//!
//! APEX mapping:
//!   EV = BV + AV > 0.5 → pass
//!   SV = Σ C_all < sv_budget → pass
//!   Ω_harm = harm_rate < 0 → reject
//!
//! Gate formula:
//!   G_apex_gr = 1 + 0.05×allowed - 0.04×rejected
//!   ΔG_apex_gr = ΔG_current × G_apex_gr (standalone measurement only)
//!
//! Boundary: This is a MEASUREMENT gate — does NOT modify Hermes Agent registry.dispatch() behavior.
//! Integration with hermes-agent/tools/registry.py requires separate implementation in that codebase.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Decision outcome for a single dispatch pre-check
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GateCheckResult {
    /// Tool name
    pub tool_name: String,
    /// Whether the tool is allowed to execute
    pub allowed: bool,
    /// EV score (benefit value = base_value + appeal_value)
    pub ev_score: f64,
    /// SV utilization ratio (0.0–1.0+)
    pub sv_ratio: f64,
    /// Harm rate (negative = anti-harm = beneficial)
    pub harm_rate: f64,
    /// Rejection reason if not allowed
    pub reject_reason: Option<String>,
    /// Individual gate pass/fail
    pub ev_pass: bool,
    pub sv_pass: bool,
    pub harm_pass: bool,
    /// Partial credit: 1.0 = full pass, 0.5 = warning, 0.0 = blocked
    pub gate_credit: f64,
}

/// Configuration for apex_gate pre-check
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GateConfig {
    /// Minimum EV score to pass (default: 0.5)
    pub ev_threshold: f64,
    /// Maximum SV utilization to pass (default: 0.95)
    pub sv_budget: f64,
    /// Maximum allowed harm rate (default: 0.0, negative = anti-harm = good)
    pub harm_threshold: f64,
    /// Known base values for common tool categories (BV estimation)
    pub base_values: HashMap<String, f64>,
    /// Known appeal modifiers (AV estimation)
    pub appeal_modifiers: HashMap<String, f64>,
    /// Harm rate overrides per tool (negative = beneficial)
    pub harm_overrides: HashMap<String, f64>,
}

impl Default for GateConfig {
    fn default() -> Self {
        let mut base_values = HashMap::new();
        base_values.insert("terminal".to_string(), 0.7);
        base_values.insert("browser".to_string(), 0.8);
        base_values.insert("file".to_string(), 0.6);
        base_values.insert("web".to_string(), 0.5);
        base_values.insert("delegate_task".to_string(), 0.9);
        base_values.insert("python".to_string(), 0.7);

        let mut appeal_modifiers = HashMap::new();
        appeal_modifiers.insert("terminal".to_string(), 0.1);
        appeal_modifiers.insert("browser".to_string(), 0.15);
        appeal_modifiers.insert("file".to_string(), 0.1);
        appeal_modifiers.insert("web".to_string(), 0.05);
        appeal_modifiers.insert("delegate_task".to_string(), 0.2);
        appeal_modifiers.insert("python".to_string(), 0.1);

        let mut harm_overrides = HashMap::new();
        harm_overrides.insert("delegate_task".to_string(), -0.2); // subagents can self-terminate safely
        harm_overrides.insert("terminal".to_string(), 0.0);       // neutral: user-initiated
        harm_overrides.insert("browser".to_string(), 0.0);       // neutral
        harm_overrides.insert("file".to_string(), 0.0);           // neutral
        harm_overrides.insert("web".to_string(), 0.0);          // neutral

        Self {
            ev_threshold: 0.5,
            sv_budget: 0.95,
            harm_threshold: 0.0,
            base_values,
            appeal_modifiers,
            harm_overrides,
        }
    }
}

impl GateConfig {
    /// EV = BV + AV for a given tool/toolset
    /// Checks full tool_name first, then falls back to the prefix (first segment before _)
    pub fn ev_score(&self, tool_name: &str) -> f64 {
        // Try full name first (e.g. "delegate_task")
        let bv = self.base_values.get(tool_name)
            .or_else(|| {
                let prefix = tool_name.split('_').next().unwrap_or(tool_name);
                self.base_values.get(prefix)
            })
            .copied().unwrap_or(0.5);
        let av = self.appeal_modifiers.get(tool_name)
            .or_else(|| {
                let prefix = tool_name.split('_').next().unwrap_or(tool_name);
                self.appeal_modifiers.get(prefix)
            })
            .copied().unwrap_or(0.0);
        bv + av
    }

    /// Harm rate for a given tool (negative = beneficial)
    /// Checks full tool_name first, then falls back to the prefix
    pub fn harm_rate(&self, tool_name: &str) -> f64 {
        // Try full name first (e.g. "dangerous_tool")
        self.harm_overrides.get(tool_name)
            .or_else(|| {
                let prefix = tool_name.split('_').next().unwrap_or(tool_name);
                self.harm_overrides.get(prefix)
            })
            .copied()
            .unwrap_or(0.0)
    }
}

/// Single tool dispatch pre-check
pub fn apex_gate(tool_name: &str, sv_ratio: f64, config: &GateConfig) -> GateCheckResult {
    let ev_score = config.ev_score(tool_name);
    let harm_rate = config.harm_rate(tool_name);

    let ev_pass = ev_score >= config.ev_threshold;
    let sv_pass = sv_ratio <= config.sv_budget;
    let harm_pass = harm_rate < 0.0 || (harm_rate >= 0.0 && harm_rate <= config.harm_threshold);

    let allowed = ev_pass && sv_pass && harm_pass;

    let reject_reason = if !allowed {
        if !ev_pass {
            Some(format!("EV too low: {} < threshold {}", ev_score, config.ev_threshold))
        } else if !sv_pass {
            Some(format!("SV budget exceeded: {} > {}", sv_ratio, config.sv_budget))
        } else {
            Some(format!("Harm rate positive: {} > 0", harm_rate))
        }
    } else {
        None
    };

        // gate_credit: 1.0 = full pass, 0.8 = normal pass, 0.5 = marginal
        let gate_credit = if allowed {
            if ev_score >= config.ev_threshold + 0.3 && harm_rate <= -0.1 {
                1.0 // strong pass: very high EV + clearly anti-harm
            } else if ev_pass && sv_pass && harm_pass {
                0.8 // normal pass (harm_pass already means harm_rate < 0)
            } else {
                0.5 // marginal
            }
        } else {
            0.0
        };

    GateCheckResult {
        tool_name: tool_name.to_string(),
        allowed,
        ev_score,
        sv_ratio,
        harm_rate,
        reject_reason,
        ev_pass,
        sv_pass,
        harm_pass,
        gate_credit,
    }
}

/// Batch report for multiple dispatch pre-checks
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GateRegistryReport {
    pub total_checks: u32,
    pub allowed_count: u32,
    pub rejected_count: u32,
    pub mean_gate_credit: f64,
    pub ev_pass_rate: f64,
    pub sv_pass_rate: f64,
    pub harm_pass_rate: f64,
    pub mean_ev: f64,
    pub mean_sv_ratio: f64,
    pub rejected_tools: Vec<String>,
    /// G_apex_gr = 1 + 0.05×allowed_rate - 0.04×rejected_rate
    pub g_apex_gr: f64,
}

impl GateRegistryReport {
    pub fn from_results(results: &[GateCheckResult]) -> Self {
        let total = results.len() as u32;
        if total == 0 {
            return Self {
                total_checks: 0,
                allowed_count: 0,
                rejected_count: 0,
                mean_gate_credit: 0.0,
                ev_pass_rate: 0.0,
                sv_pass_rate: 0.0,
                harm_pass_rate: 0.0,
                mean_ev: 0.0,
                mean_sv_ratio: 0.0,
                rejected_tools: vec![],
                g_apex_gr: 1.0,
            };
        }

        let allowed_count = results.iter().filter(|r| r.allowed).count() as u32;
        let rejected_count = total - allowed_count;
        let allowed_rate = allowed_count as f64 / total as f64;
        let rejected_rate = rejected_count as f64 / total as f64;

        let mean_gate_credit = results.iter().map(|r| r.gate_credit).sum::<f64>() / total as f64;
        let ev_pass_rate = results.iter().filter(|r| r.ev_pass).count() as f64 / total as f64;
        let sv_pass_rate = results.iter().filter(|r| r.sv_pass).count() as f64 / total as f64;
        let harm_pass_rate = results.iter().filter(|r| r.harm_pass).count() as f64 / total as f64;
        let mean_ev = results.iter().map(|r| r.ev_score).sum::<f64>() / total as f64;
        let mean_sv_ratio = results.iter().map(|r| r.sv_ratio).sum::<f64>() / total as f64;
        let rejected_tools = results
            .iter()
            .filter(|r| !r.allowed)
            .map(|r| r.tool_name.clone())
            .collect();

        // G_apex_gr = 1 + 0.05×allowed_rate - 0.04×rejected_rate
        let g_apex_gr = 1.0 + 0.05 * allowed_rate - 0.04 * rejected_rate;

        Self {
            total_checks: total,
            allowed_count,
            rejected_count,
            mean_gate_credit,
            ev_pass_rate,
            sv_pass_rate,
            harm_pass_rate,
            mean_ev,
            mean_sv_ratio,
            rejected_tools,
            g_apex_gr,
        }
    }

    /// G_apex_gr clamped to [0.80, 1.20]
    pub fn g_apex_gr_clamped(&self) -> f64 {
        self.g_apex_gr.clamp(0.80, 1.20)
    }
}

/// Batch gate check for multiple tools with SV ratios
pub fn batch_gate_check(
    tool_sv_pairs: &[(String, f64)],
    config: &GateConfig,
) -> GateRegistryReport {
    let results: Vec<GateCheckResult> = tool_sv_pairs
        .iter()
        .map(|(name, sv_ratio)| apex_gate(name, *sv_ratio, config))
        .collect();
    GateRegistryReport::from_results(&results)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ev_score_default() {
        let config = GateConfig::default();
        // Known tool base values (use assert! with epsilon for float equality)
        assert!((config.ev_score("delegate_task") - 1.1).abs() < 1e-9); // 0.9 + 0.2
        assert!((config.ev_score("terminal_tool") - 0.8).abs() < 1e-9); // 0.7 + 0.1
        assert!((config.ev_score("browser_navigate") - 0.95).abs() < 1e-9); // 0.8 + 0.15
        // Unknown tool: bv=0.5, av=0.0
        assert!((config.ev_score("unknown_tool") - 0.5).abs() < 1e-9);
    }

    #[test]
    fn test_apex_gate_allowed() {
        let config = GateConfig::default();
        // delegate_task: EV=1.1 >= 0.5 ✓, SV=0.5 <= 0.95 ✓, harm=-0.2 < 0 ✓
        let result = apex_gate("delegate_task", 0.5, &config);
        assert!(result.allowed);
        assert!(result.ev_pass);
        assert!(result.sv_pass);
        assert!(result.harm_pass);
        assert!(result.reject_reason.is_none());
        assert_eq!(result.gate_credit, 1.0);
    }

    #[test]
    fn test_apex_gate_rejected_low_ev() {
        let config = GateConfig::default();
        // web_tool: EV=0.55 (0.5+0.05) borderline, but low SV
        // SV ratio above budget
        let result = apex_gate("web_search", 0.98, &config);
        assert!(!result.allowed);
        assert!(result.sv_pass == false); // SV over budget
    }

    #[test]
    fn test_apex_gate_harm_reject() {
        let config = GateConfig::default();
        // A hypothetical tool with positive harm
        let mut config = GateConfig::default();
        config.harm_overrides.insert("dangerous_tool".to_string(), 0.5);
        let result = apex_gate("dangerous_tool", 0.5, &config);
        assert!(!result.allowed);
        assert!(!result.harm_pass);
        assert!(result.reject_reason.is_some());
        assert!(result.reject_reason.unwrap().contains("Harm"));
    }

    #[test]
    fn test_gate_report_empty() {
        let report = GateRegistryReport::from_results(&[]);
        assert_eq!(report.total_checks, 0);
        assert_eq!(report.g_apex_gr, 1.0);
    }

    #[test]
    fn test_gate_report_all_pass() {
        let config = GateConfig::default();
        let results = vec![
            apex_gate("delegate_task", 0.5, &config),
            apex_gate("terminal_tool", 0.5, &config),
        ];
        let report = GateRegistryReport::from_results(&results);
        assert_eq!(report.total_checks, 2);
        assert_eq!(report.allowed_count, 2);
        assert_eq!(report.rejected_count, 0);
        assert_eq!(report.g_apex_gr, 1.0 + 0.05 * 1.0 - 0.04 * 0.0);
        assert_eq!(report.g_apex_gr, 1.05);
    }

    #[test]
    fn test_gate_report_mixed() {
        let config = GateConfig::default();
        // SV too high → rejected
        let r1 = apex_gate("delegate_task", 0.5, &config); // pass
        let r2 = apex_gate("delegate_task", 0.99, &config); // SV fail
        let results = vec![r1, r2];
        let report = GateRegistryReport::from_results(&results);
        assert_eq!(report.total_checks, 2);
        assert_eq!(report.allowed_count, 1);
        assert_eq!(report.rejected_count, 1);
        // G = 1 + 0.05×0.5 - 0.04×0.5 = 1 + 0.025 - 0.02 = 1.005
        assert_eq!(report.g_apex_gr, 1.005);
    }

    #[test]
    fn test_batch_gate_check() {
        let config = GateConfig::default();
        let tools = vec![
            ("delegate_task".to_string(), 0.5),
            ("terminal_tool".to_string(), 0.6),
            ("browser_navigate".to_string(), 0.4),
        ];
        let report = batch_gate_check(&tools, &config);
        assert_eq!(report.total_checks, 3);
        assert_eq!(report.allowed_count, 3);
        assert_eq!(report.rejected_count, 0);
        assert!(report.g_apex_gr >= 1.05);
    }

    #[test]
    fn test_g_apex_gr_clamped() {
        let report = GateRegistryReport {
            total_checks: 10,
            allowed_count: 0,
            rejected_count: 10,
            mean_gate_credit: 0.0,
            ev_pass_rate: 0.0,
            sv_pass_rate: 0.0,
            harm_pass_rate: 0.0,
            mean_ev: 0.0,
            mean_sv_ratio: 0.0,
            rejected_tools: vec![],
            g_apex_gr: 0.60, // would be 0.60 without clamp
        };
        assert_eq!(report.g_apex_gr_clamped(), 0.80); // clamped to minimum
    }
}