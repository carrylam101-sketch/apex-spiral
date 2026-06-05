//! APEX Devour Module
//! Evaluates D_devour = Q_source · M_mech · A_impl · V_audit · T_transfer
//! and G_devour = 1 + 0.08·D_devour - 0.05·Ω_risk

use serde::{Deserialize, Serialize};

/// A single source digest entry — maps external repo mechanism to APEX dimensions.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SourceDigest {
    pub repo: String,
    pub stars_observed: u64,
    pub mechanism: String,
    pub apex_mapping: Vec<String>,
    /// "native_rust" | "python_glue" | "concept_only" | "not_started"
    pub impl_status: String,
    /// "test_pass" | "partial" | "none"
    pub audit_status: String,
    pub transferrable: bool,
    /// Risk flags: "license_restrictive", "hallucination_risk", "supply_chain", "no_repro", "dangerous_capability"
    pub risk_flags: Vec<String>,
}

/// Devoured mechanism result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DevourResult {
    pub repo: String,
    pub stars: u64,
    pub mechanism: String,
    pub apex_mapping: Vec<String>,
    pub q_source: f64,
    pub m_mech: f64,
    pub a_impl: f64,
    pub v_audit: f64,
    pub t_transfer: f64,
    pub d_devour: f64,
    pub omega_risk: f64,
    pub g_devour: f64,
    pub gain_signal: String, // "positive" | "neutral" | "negative"
    pub gates_passed: Vec<String>,
    pub gates_failed: Vec<String>,
}

impl Default for DevourEngine {
    fn default() -> Self {
        Self::new()
    }
}

pub struct DevourEngine;

impl DevourEngine {
    pub fn new() -> Self {
        Self
    }

    /// Evaluate a source digest and return devour result with G_devour.
    pub fn devour(&mut self, digest: SourceDigest) -> anyhow::Result<DevourResult> {
        let q_source = Self::eval_q_source(digest.stars_observed);
        let m_mech = Self::eval_m_mech(&digest.apex_mapping);
        let a_impl = Self::eval_a_impl(&digest.impl_status);
        let v_audit = Self::eval_v_audit(&digest.audit_status);
        let t_transfer = Self::eval_t_transfer(digest.transferrable);
        let omega_risk = Self::eval_omega_risk(&digest.risk_flags);

        let d_devour = q_source * m_mech * a_impl * v_audit * t_transfer;
        let g_devour = 1.0 + 0.08 * d_devour - 0.05 * omega_risk;

        let gates_passed =
            Self::gates_passed(q_source, m_mech, a_impl, v_audit, t_transfer, omega_risk);
        let gates_failed =
            Self::gates_failed(q_source, m_mech, a_impl, v_audit, t_transfer, omega_risk);

        let gain_signal = if g_devour >= 1.0 {
            "positive"
        } else if g_devour >= 0.95 {
            "neutral"
        } else {
            "negative"
        };

        Ok(DevourResult {
            repo: digest.repo,
            stars: digest.stars_observed,
            mechanism: digest.mechanism,
            apex_mapping: digest.apex_mapping,
            q_source,
            m_mech,
            a_impl,
            v_audit,
            t_transfer,
            d_devour,
            omega_risk,
            g_devour,
            gain_signal: gain_signal.to_string(),
            gates_passed,
            gates_failed,
        })
    }

    /// Q_source: source quality from stars / benchmark / community adoption.
    /// Conservative: 74.6k stars → 0.82; linear scaling.
    fn eval_q_source(stars: u64) -> f64 {
        const REF_STARS: f64 = 74_600.0;
        const REF_Q: f64 = 0.82;
        let base = (stars as f64 / REF_STARS).min(1.5).max(0.05);
        (base * REF_Q).min(1.0).max(0.0)
    }

    /// M_mech: mechanism understanding completeness.
    /// Count apex_mapping entries that map to concrete APEX dimensions.
    fn eval_m_mech(mappings: &[String]) -> f64 {
        if mappings.is_empty() {
            return 0.0;
        }
        let valid_dims = [
            "LongPlan",
            "ToolAct",
            "Sandbox",
            "Workflow",
            "P_decompose",
            "V_audit",
            "IssueRepair",
            "G_self",
            "SkillMemory",
            "Reflect",
            "S_review",
            "MetaG",
            "PolicyTextUpdate",
        ];
        let valid = mappings
            .iter()
            .filter(|m| valid_dims.contains(&m.as_str()))
            .count();
        (valid as f64 / mappings.len() as f64).max(0.0).min(1.0)
    }

    /// A_impl: Rust/Go/C implementation status.
    fn eval_a_impl(status: &str) -> f64 {
        match status {
            "native_rust" | "native_go" | "native_c" => 0.90,
            "python_glue" => 0.50,
            "concept_only" => 0.25,
            "not_started" => 0.05,
            _ => 0.10,
        }
    }

    /// V_audit: test/lint/sandbox verification status.
    fn eval_v_audit(status: &str) -> f64 {
        match status {
            "test_pass" => 0.85,
            "partial" => 0.45,
            "none" => 0.10,
            _ => 0.10,
        }
    }

    /// T_transfer: transferability to CLAW/Hermes.
    fn eval_t_transfer(transferrable: bool) -> f64 {
        if transferrable {
            0.78
        } else {
            0.20
        }
    }

    /// Ω_risk: supply chain / license / hallucination / dangerous capability risk.
    fn eval_omega_risk(flags: &[String]) -> f64 {
        let flag_count = flags.len() as f64;
        // Each flag adds ~0.05 risk; cap at 0.40
        (flag_count * 0.05).min(0.40)
    }

    fn gates_passed(q: f64, m: f64, a: f64, v: f64, t: f64, o: f64) -> Vec<String> {
        let mut gates = Vec::new();
        if q > 0.70 {
            gates.push("Q_source>0.70".to_string());
        }
        if m > 0.65 {
            gates.push("M_mech>0.65".to_string());
        }
        if a > 0.50 {
            gates.push("A_impl>0.50".to_string());
        }
        if v > 0.60 {
            gates.push("V_audit>0.60".to_string());
        }
        if t > 0.60 {
            gates.push("T_transfer>0.60".to_string());
        }
        if o < 0.20 {
            gates.push("Omega_risk<0.20".to_string());
        }
        gates
    }

    fn gates_failed(q: f64, m: f64, a: f64, v: f64, t: f64, o: f64) -> Vec<String> {
        let mut gates = Vec::new();
        if q <= 0.70 {
            gates.push("Q_source≤0.70".to_string());
        }
        if m <= 0.65 {
            gates.push("M_mech≤0.65".to_string());
        }
        if a <= 0.50 {
            gates.push("A_impl≤0.50".to_string());
        }
        if v <= 0.60 {
            gates.push("V_audit≤0.60".to_string());
        }
        if t <= 0.60 {
            gates.push("T_transfer≤0.60".to_string());
        }
        if o >= 0.20 {
            gates.push("Omega_risk≥0.20".to_string());
        }
        gates
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_devour_openhands() {
        let mut engine = DevourEngine::new();
        let digest = SourceDigest {
            repo: "OpenHands/OpenHands".to_string(),
            stars_observed: 74_600,
            mechanism: "Multi-model SDK/CLI/GUI/Cloud software-agent stack with scalable execution"
                .to_string(),
            apex_mapping: vec![
                "LongPlan".to_string(),
                "ToolAct".to_string(),
                "Sandbox".to_string(),
                "Workflow".to_string(),
            ],
            impl_status: "not_started".to_string(),
            audit_status: "none".to_string(),
            transferrable: true,
            risk_flags: vec![],
        };
        let result = engine.devour(digest).unwrap();
        assert!(result.q_source > 0.70);
        assert!(result.m_mech >= 0.75);
        assert_eq!(result.gain_signal, "positive"); // D>0 but tiny; G_devour≈1.0002 crosses positive threshold
    }

    #[test]
    fn test_devour_sweagent() {
        let mut engine = DevourEngine::new();
        let digest = SourceDigest {
            repo: "SWE-agent/SWE-agent".to_string(),
            stars_observed: 19_300,
            mechanism: "GitHub issue → patch → test loop; SWE-bench oriented environment"
                .to_string(),
            apex_mapping: vec![
                "P_decompose".to_string(),
                "V_audit".to_string(),
                "IssueRepair".to_string(),
            ],
            impl_status: "concept_only".to_string(),
            audit_status: "partial".to_string(),
            transferrable: true,
            risk_flags: vec!["license_restrictive".to_string()],
        };
        let result = engine.devour(digest).unwrap();
        assert!(result.q_source > 0.20 && result.q_source < 0.40);
        assert_eq!(result.gain_signal, "neutral");
    }

    #[test]
    fn test_d_devour_formula() {
        // D_devour = Q · M · A · V · T
        // With OpenHands-like params:
        let q = 0.82;
        let m = 1.00; // 4/4 valid mappings
        let a = 0.90; // native_rust
        let v = 0.85; // test_pass
        let t = 0.78; // transferrable
        let d = q * m * a * v * t;
        let g = 1.0 + 0.08 * d - 0.05 * 0.0;
        assert!(d > 0.45);
        assert!(g > 1.0); // native rust impl would be positive
    }

    #[test]
    fn test_omega_risk() {
        let flags = vec!["hallucination_risk".to_string(), "no_repro".to_string()];
        let o = DevourEngine::eval_omega_risk(&flags);
        assert_eq!(o, 0.10);
    }
}
