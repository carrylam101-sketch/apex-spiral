//! Reflexion-style verbal reinforcement gate.
//! Native Rust implementation inspired by Reflexion (arXiv:2303.11366), without copying external code.
//!
//! Purpose for APEX Devour:
//! - Convert feedback + verbal reflection + next attempt outcome into a measurable gate.
//! - Keep reflection as auditable memory only when it changes the next policy/outcome signal.
//! - Bound claims: this is not weight update RL; it is an evidence gate for reflection memory.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReflectionAttempt {
    pub attempt_id: String,
    pub task_hash: String,
    #[serde(default)]
    pub feedback_signal: String,
    #[serde(default)]
    pub reflection_text: String,
    pub prior_pass: bool,
    pub next_pass: bool,
    pub prior_score: f64,
    pub next_score: f64,
    #[serde(default)]
    pub repeated_error: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReflectionMemoryItem {
    pub attempt_id: String,
    pub score_delta: f64,
    pub pass_delta: i32,
    pub reflection_len: usize,
    pub repeated_error_penalty: f64,
    pub reflection_credit: f64,
    pub gate: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReflectionReport {
    pub n_attempts: usize,
    pub mean_score_delta: f64,
    pub pass_improvement_rate: f64,
    pub repeated_error_rate: f64,
    pub mean_reflection_credit: f64,
    pub keep_memory: bool,
    pub items: Vec<ReflectionMemoryItem>,
}

pub struct ReflectionGate;

impl ReflectionGate {
    /// Assign conservative reflection-memory credit.
    /// score_delta = clamp(next_score - prior_score, -1, 1)
    /// pass_delta = +1 if fail->pass, -1 if pass->fail, 0 otherwise
    /// text_quality = clamp(reflection_len / 160, 0, 1)
    /// credit = clamp(0.45*(score_delta+1)/2 + 0.35*pass_bonus + 0.20*text_quality - repeated_error_penalty, 0, 1)
    pub fn evaluate(attempts: &[ReflectionAttempt]) -> ReflectionReport {
        let n_attempts = attempts.len();
        if n_attempts == 0 {
            return ReflectionReport {
                n_attempts: 0,
                mean_score_delta: 0.0,
                pass_improvement_rate: 0.0,
                repeated_error_rate: 0.0,
                mean_reflection_credit: 0.0,
                keep_memory: false,
                items: vec![],
            };
        }

        let mut items = Vec::with_capacity(n_attempts);
        let mut score_delta_sum = 0.0;
        let mut pass_improvements = 0usize;
        let mut repeated_errors = 0usize;

        for a in attempts {
            let score_delta = (a.next_score - a.prior_score).clamp(-1.0, 1.0);
            score_delta_sum += score_delta;

            let pass_delta = match (a.prior_pass, a.next_pass) {
                (false, true) => {
                    pass_improvements += 1;
                    1
                }
                (true, false) => -1,
                _ => 0,
            };

            if a.repeated_error {
                repeated_errors += 1;
            }

            let reflection_len = a.reflection_text.chars().count();
            let text_quality = (reflection_len as f64 / 160.0).clamp(0.0, 1.0);
            let pass_bonus = match pass_delta {
                1 => 1.0,
                0 => 0.35,
                _ => 0.0,
            };
            let repeated_error_penalty = if a.repeated_error { 0.25 } else { 0.0 };
            let normalized_delta = ((score_delta + 1.0) / 2.0).clamp(0.0, 1.0);
            let reflection_credit =
                (0.45 * normalized_delta + 0.35 * pass_bonus + 0.20 * text_quality
                    - repeated_error_penalty)
                    .clamp(0.0, 1.0);

            let gate = if reflection_credit >= 0.70 && pass_delta >= 0 {
                "keep".to_string()
            } else if reflection_credit >= 0.45 {
                "review".to_string()
            } else {
                "discard".to_string()
            };

            items.push(ReflectionMemoryItem {
                attempt_id: a.attempt_id.clone(),
                score_delta,
                pass_delta,
                reflection_len,
                repeated_error_penalty,
                reflection_credit,
                gate,
            });
        }

        let mean_score_delta = score_delta_sum / n_attempts as f64;
        let pass_improvement_rate = pass_improvements as f64 / n_attempts as f64;
        let repeated_error_rate = repeated_errors as f64 / n_attempts as f64;
        let mean_reflection_credit =
            items.iter().map(|i| i.reflection_credit).sum::<f64>() / n_attempts as f64;
        let keep_memory = mean_reflection_credit >= 0.58
            && mean_score_delta >= 0.0
            && repeated_error_rate <= 0.35;

        ReflectionReport {
            n_attempts,
            mean_score_delta,
            pass_improvement_rate,
            repeated_error_rate,
            mean_reflection_credit,
            keep_memory,
            items,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn keeps_useful_reflection_memory() {
        let attempts = vec![ReflectionAttempt {
            attempt_id: "r1".into(),
            task_hash: "task-a".into(),
            feedback_signal: "tests failed: missing edge case".into(),
            reflection_text: "Next attempt must add a regression test for the empty input edge case before changing production code.".into(),
            prior_pass: false,
            next_pass: true,
            prior_score: 0.2,
            next_score: 0.9,
            repeated_error: false,
        }];
        let report = ReflectionGate::evaluate(&attempts);
        assert!(report.keep_memory);
        assert_eq!(report.items[0].gate, "keep");
        assert!(report.mean_score_delta > 0.6);
    }

    #[test]
    fn discards_repeated_bad_reflection() {
        let attempts = vec![ReflectionAttempt {
            attempt_id: "r2".into(),
            task_hash: "task-b".into(),
            feedback_signal: "same tool error".into(),
            reflection_text: "try again".into(),
            prior_pass: false,
            next_pass: false,
            prior_score: 0.3,
            next_score: 0.1,
            repeated_error: true,
        }];
        let report = ReflectionGate::evaluate(&attempts);
        assert!(!report.keep_memory);
        assert_eq!(report.items[0].gate, "discard");
    }
}
