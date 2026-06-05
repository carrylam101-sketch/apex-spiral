//! VLM-Agentic Self-Correction Gate
//! Absorbs the pattern: VLM (Vision-Language Model) → embodied action → self-correction loop → policy update.
//! Source → mechanism → APEX mapping → measurable gate.
//!
//! source: CogAgent (GUI agent, VLMs for GUI automation, arXiv:2312.08914, ~3.5k stars)
//! mechanism: Screen understanding + action generation + internal self-correction across steps.
//! APEX mapping: MetaG (self-correction) + ToolAct (embodied action) + LongPlan (GUI navigation) + V_audit (verifier).
//! Measurable gate: VLMCorrectionReport (correction_rate, correction_quality, keep_for_training).

use serde::{Deserialize, Serialize};

/// A single step in a VLM-agentic trajectory.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VLMTrajectoryStep {
    pub step_id: String,
    /// Visual observation: screenshot description or encoded frame.
    pub visual_obs: String,
    /// Action taken by the VLM agent.
    pub action: String,
    /// Tool used (terminal, browser, mouse_click, keyboard, etc.)
    pub tool: String,
    /// Whether the action succeeded (verifier pass).
    pub success: bool,
    /// Whether a self-correction was triggered in this step.
    pub correction_triggered: bool,
    /// Quality of correction if triggered (0.0-1.0).
    pub correction_quality: Option<f64>,
    /// Whether trajectory continued after correction.
    pub continued: bool,
}

/// Correction pattern evaluation result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CorrectionEval {
    pub step_id: String,
    pub correction_triggered: bool,
    pub correction_quality: f64,
    pub correction_effective: bool,
}

impl VLMTrajectoryStep {
    pub fn evaluate_correction(&self) -> CorrectionEval {
        let correction_quality = self.correction_quality.unwrap_or(0.0);
        let correction_effective = self.correction_triggered
            && (correction_quality >= 0.5 || self.continued);
        CorrectionEval {
            step_id: self.step_id.clone(),
            correction_triggered: self.correction_triggered,
            correction_quality,
            correction_effective,
        }
    }
}

/// Report from VLM-agentic self-correction gate evaluation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VLMCorrectionReport {
    pub n_steps: usize,
    pub n_corrections: usize,
    pub correction_rate: f64,
    pub mean_correction_quality: f64,
    pub effective_corrections: usize,
    pub correction_effectiveness: f64,
    /// Trajectory is worth training on if correction rate is reasonable and effectiveness is high.
    pub keep_for_training: bool,
    /// Human-readable summary.
    pub summary: String,
}

impl VLMCorrectionReport {
    pub fn from_steps(steps: &[VLMTrajectoryStep]) -> Self {
        let n_steps = steps.len();
        let n_corrections = steps.iter().filter(|s| s.correction_triggered).count();
        let correction_rate = if n_steps > 0 {
            n_corrections as f64 / n_steps as f64
        } else {
            0.0
        };

        let evals: Vec<CorrectionEval> = steps.iter().map(|s| s.evaluate_correction()).collect();
        let correction_quality_sum: f64 = evals
            .iter()
            .filter(|e| e.correction_triggered)
            .map(|e| e.correction_quality)
            .sum();
        let mean_correction_quality = if n_corrections > 0 {
            correction_quality_sum / n_corrections as f64
        } else {
            0.0
        };

        let effective_corrections = evals.iter().filter(|e| e.correction_effective).count();
        let correction_effectiveness = if n_corrections > 0 {
            effective_corrections as f64 / n_corrections as f64
        } else {
            0.0
        };

        // keep_for_training: correction_rate > 0.05 (some corrections) AND correction_effectiveness > 0.4
        let keep_for_training = correction_rate > 0.05 && correction_effectiveness > 0.4;

        let summary = if n_corrections == 0 {
            format!("No corrections in {} steps — trajectory stable.", n_steps)
        } else {
            format!(
                "{}/{} steps triggered correction (rate={:.2}), effectiveness={:.2}, mean quality={:.2}",
                n_corrections, n_steps, correction_rate, correction_effectiveness, mean_correction_quality
            )
        };

        VLMCorrectionReport {
            n_steps,
            n_corrections,
            correction_rate,
            mean_correction_quality,
            effective_corrections,
            correction_effectiveness,
            keep_for_training,
            summary,
        }
    }
}

/// Evaluate VLM-agentic trajectory steps through the self-correction gate.
pub fn evaluate(trajectory: &[VLMTrajectoryStep]) -> VLMCorrectionReport {
    VLMCorrectionReport::from_steps(trajectory)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_step(id: &str, correction: bool, quality: Option<f64>, continued: bool, success: bool) -> VLMTrajectoryStep {
        VLMTrajectoryStep {
            step_id: id.to_string(),
            visual_obs: format!("screen for step {}", id),
            action: format!("action for step {}", id),
            tool: "terminal".to_string(),
            success,
            correction_triggered: correction,
            correction_quality: quality,
            continued,
        }
    }

    #[test]
    fn test_no_corrections() {
        let steps = vec![
            make_step("s1", false, None, true, true),
            make_step("s2", false, None, true, true),
        ];
        let report = VLMCorrectionReport::from_steps(&steps);
        assert_eq!(report.n_steps, 2);
        assert_eq!(report.n_corrections, 0);
        assert!(!report.keep_for_training);
    }

    #[test]
    fn test_effective_corrections() {
        let steps = vec![
            make_step("s1", true, Some(0.7), true, false),
            make_step("s2", false, None, true, true),
            make_step("s3", true, Some(0.9), true, false),
        ];
        let report = VLMCorrectionReport::from_steps(&steps);
        assert_eq!(report.n_corrections, 2);
        assert!(report.correction_rate > 0.05);
        assert!(report.mean_correction_quality > 0.7);
        assert!(report.correction_effectiveness > 0.4);
        assert!(report.keep_for_training);
    }

    #[test]
    fn test_ineffective_corrections() {
        let steps = vec![
            make_step("s1", true, Some(0.2), false, false),
            make_step("s2", true, Some(0.1), false, false),
        ];
        let report = VLMCorrectionReport::from_steps(&steps);
        assert_eq!(report.n_corrections, 2);
        assert!(report.correction_effectiveness < 0.4);
        assert!(!report.keep_for_training);
    }

    #[test]
    fn test_empty_trajectory() {
        let report = VLMCorrectionReport::from_steps(&[]);
        assert_eq!(report.n_steps, 0);
        assert!(!report.keep_for_training);
    }
}