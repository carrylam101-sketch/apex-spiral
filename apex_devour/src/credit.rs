//! Agentic RL credit assignment gate.
//! Native Rust implementation inspired by Agent Lightning's decoupled trajectory → transition
//! credit-assignment idea, without copying external code.
//!
//! Purpose for APEX Devour:
//! - Convert arbitrary agent execution traces into measurable transitions.
//! - Assign conservative step credit from reward, verifier pass/fail, and tool error signals.
//! - Produce gates usable by APEX/CLAW before any RL or skill-memory update.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrajectoryStep {
    pub step_id: String,
    pub observation_hash: String,
    pub action: String,
    pub tool: String,
    pub reward: f64,
    pub verifier_pass: bool,
    #[serde(default)]
    pub tool_error: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StepCredit {
    pub step_id: String,
    pub normalized_reward: f64,
    pub verifier_weight: f64,
    pub tool_penalty: f64,
    pub credit: f64,
    pub gate: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreditReport {
    pub n_steps: usize,
    pub total_credit: f64,
    pub mean_credit: f64,
    pub pass_rate: f64,
    pub tool_error_rate: f64,
    pub keep_for_training: bool,
    pub steps: Vec<StepCredit>,
}

pub struct CreditAssigner;

impl CreditAssigner {
    /// Assign conservative credit to each transition.
    /// Formula:
    /// normalized_reward = clamp((reward + 1)/2, 0, 1)
    /// verifier_weight = 1.0 if verifier_pass else 0.35
    /// tool_penalty = 0.25 if tool_error else 0.0
    /// credit = clamp(normalized_reward * verifier_weight - tool_penalty, 0, 1)
    pub fn assign(steps: &[TrajectoryStep]) -> CreditReport {
        let n_steps = steps.len();
        if n_steps == 0 {
            return CreditReport {
                n_steps: 0,
                total_credit: 0.0,
                mean_credit: 0.0,
                pass_rate: 0.0,
                tool_error_rate: 0.0,
                keep_for_training: false,
                steps: vec![],
            };
        }

        let mut pass_count = 0usize;
        let mut error_count = 0usize;
        let mut credits = Vec::with_capacity(n_steps);

        for s in steps {
            if s.verifier_pass {
                pass_count += 1;
            }
            if s.tool_error {
                error_count += 1;
            }

            let normalized_reward = ((s.reward + 1.0) / 2.0).clamp(0.0, 1.0);
            let verifier_weight = if s.verifier_pass { 1.0 } else { 0.35 };
            let tool_penalty = if s.tool_error { 0.25 } else { 0.0 };
            let credit = (normalized_reward * verifier_weight - tool_penalty).clamp(0.0, 1.0);
            let gate = if credit >= 0.70 {
                "train".to_string()
            } else if credit >= 0.40 {
                "review".to_string()
            } else {
                "reject".to_string()
            };

            credits.push(StepCredit {
                step_id: s.step_id.clone(),
                normalized_reward,
                verifier_weight,
                tool_penalty,
                credit,
                gate,
            });
        }

        let total_credit: f64 = credits.iter().map(|c| c.credit).sum();
        let mean_credit = total_credit / n_steps as f64;
        let pass_rate = pass_count as f64 / n_steps as f64;
        let tool_error_rate = error_count as f64 / n_steps as f64;
        let keep_for_training = mean_credit >= 0.55 && pass_rate >= 0.60 && tool_error_rate <= 0.20;

        CreditReport {
            n_steps,
            total_credit,
            mean_credit,
            pass_rate,
            tool_error_rate,
            keep_for_training,
            steps: credits,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn assigns_high_credit_to_verified_positive_steps() {
        let steps = vec![TrajectoryStep {
            step_id: "s1".into(),
            observation_hash: "abc".into(),
            action: "run tests".into(),
            tool: "terminal".into(),
            reward: 0.8,
            verifier_pass: true,
            tool_error: false,
        }];
        let r = CreditAssigner::assign(&steps);
        assert_eq!(r.n_steps, 1);
        assert!(r.mean_credit > 0.85);
        assert!(r.keep_for_training);
        assert_eq!(r.steps[0].gate, "train");
    }

    #[test]
    fn rejects_error_prone_unverified_steps() {
        let steps = vec![TrajectoryStep {
            step_id: "s1".into(),
            observation_hash: "abc".into(),
            action: "guess patch".into(),
            tool: "none".into(),
            reward: -0.2,
            verifier_pass: false,
            tool_error: true,
        }];
        let r = CreditAssigner::assign(&steps);
        assert!(!r.keep_for_training);
        assert_eq!(r.steps[0].gate, "reject");
    }
}
