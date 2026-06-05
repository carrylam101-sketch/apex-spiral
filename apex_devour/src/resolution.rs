//! Issue-resolution benchmark gate for coding agents.
//! Native Rust gate inspired by public coding-agent mechanisms such as SWE-agent's
//! issue→patch→test loop, OpenHands' event-driven software-agent execution, and
//! SWE-EVO/SWE-bench-style long-horizon verification — without copying external code.
//!
//! Purpose for APEX Devour:
//! - Convert coding-agent issue-resolution runs into measurable training/audit signals.
//! - Reward reproducible issues, generated patches, passing tests, regression tests, and sandboxing.
//! - Penalize tool errors, missing verification, overly broad file changes, and human-review blockers.
//! - Decide whether solved runs are safe to keep for CLAW/Hermes training memory.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IssueResolutionRun {
    pub run_id: String,
    pub issue_hash: String,
    #[serde(default)]
    pub reproduction_present: bool,
    #[serde(default)]
    pub patch_generated: bool,
    #[serde(default)]
    pub tests_run: bool,
    #[serde(default)]
    pub tests_passed: bool,
    #[serde(default)]
    pub regression_tests_added: bool,
    #[serde(default)]
    pub files_touched: u32,
    #[serde(default)]
    pub sandboxed: bool,
    #[serde(default)]
    pub tool_errors: u32,
    #[serde(default)]
    pub human_review_required: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunResolutionScore {
    pub run_id: String,
    pub verification_signal: f64,
    pub patch_signal: f64,
    pub safety_signal: f64,
    pub scope_penalty: f64,
    pub error_penalty: f64,
    pub resolution_credit: f64,
    pub gate: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResolutionReport {
    pub n_runs: usize,
    pub solve_rate: f64,
    pub test_pass_rate: f64,
    pub regression_coverage_rate: f64,
    pub sandbox_rate: f64,
    pub tool_error_rate: f64,
    pub mean_resolution_credit: f64,
    pub keep_for_training: bool,
    pub runs: Vec<RunResolutionScore>,
}

pub struct ResolutionGate;

impl ResolutionGate {
    /// Evaluate issue→patch→test resolution quality.
    /// verification_signal = 0.30*repro + 0.35*tests_run + 0.35*tests_passed
    /// patch_signal = 0.70*patch_generated + 0.30*regression_tests_added
    /// safety_signal = 0.70*sandboxed + 0.30*(no human review blocker)
    /// scope_penalty = min(max(files_touched - 8, 0) / 20, 0.30)
    /// error_penalty = min(0.12*tool_errors + 0.18*(tests_run && !tests_passed), 0.45)
    /// resolution_credit = clamp(0.45*verification + 0.30*patch + 0.25*safety - scope_penalty - error_penalty, 0, 1)
    pub fn evaluate(runs: &[IssueResolutionRun]) -> ResolutionReport {
        if runs.is_empty() {
            return ResolutionReport {
                n_runs: 0,
                solve_rate: 0.0,
                test_pass_rate: 0.0,
                regression_coverage_rate: 0.0,
                sandbox_rate: 0.0,
                tool_error_rate: 0.0,
                mean_resolution_credit: 0.0,
                keep_for_training: false,
                runs: vec![],
            };
        }

        let mut scores = Vec::with_capacity(runs.len());
        let mut solved = 0usize;
        let mut tests_passed = 0usize;
        let mut regression_added = 0usize;
        let mut sandboxed = 0usize;
        let mut tool_error_runs = 0usize;

        for r in runs {
            if r.patch_generated && r.tests_run && r.tests_passed {
                solved += 1;
            }
            if r.tests_passed {
                tests_passed += 1;
            }
            if r.regression_tests_added {
                regression_added += 1;
            }
            if r.sandboxed {
                sandboxed += 1;
            }
            if r.tool_errors > 0 {
                tool_error_runs += 1;
            }

            let verification_signal: f64 = (0.30_f64
                * if r.reproduction_present {
                    1.0_f64
                } else {
                    0.0_f64
                }
                + 0.35_f64 * if r.tests_run { 1.0_f64 } else { 0.0_f64 }
                + 0.35_f64 * if r.tests_passed { 1.0_f64 } else { 0.0_f64 })
            .clamp(0.0, 1.0);
            let patch_signal: f64 = (0.70_f64 * if r.patch_generated { 1.0_f64 } else { 0.0_f64 }
                + 0.30_f64
                    * if r.regression_tests_added {
                        1.0_f64
                    } else {
                        0.0_f64
                    })
            .clamp(0.0, 1.0);
            let safety_signal: f64 = (0.70_f64 * if r.sandboxed { 1.0_f64 } else { 0.0_f64 }
                + 0.30_f64
                    * if r.human_review_required {
                        0.0_f64
                    } else {
                        1.0_f64
                    })
            .clamp(0.0, 1.0);
            let scope_penalty = ((r.files_touched.saturating_sub(8)) as f64 / 20.0).min(0.30);
            let error_penalty = (0.12 * r.tool_errors as f64
                + 0.18
                    * if r.tests_run && !r.tests_passed {
                        1.0
                    } else {
                        0.0
                    })
            .min(0.45);
            let resolution_credit =
                (0.45 * verification_signal + 0.30 * patch_signal + 0.25 * safety_signal
                    - scope_penalty
                    - error_penalty)
                    .clamp(0.0, 1.0);
            let gate = if resolution_credit >= 0.75 {
                "train".to_string()
            } else if resolution_credit >= 0.50 {
                "review".to_string()
            } else {
                "reject".to_string()
            };

            scores.push(RunResolutionScore {
                run_id: r.run_id.clone(),
                verification_signal,
                patch_signal,
                safety_signal,
                scope_penalty,
                error_penalty,
                resolution_credit,
                gate,
            });
        }

        let n = runs.len() as f64;
        let total_credit: f64 = scores.iter().map(|s| s.resolution_credit).sum();
        let solve_rate = solved as f64 / n;
        let test_pass_rate = tests_passed as f64 / n;
        let regression_coverage_rate = regression_added as f64 / n;
        let sandbox_rate = sandboxed as f64 / n;
        let tool_error_rate = tool_error_runs as f64 / n;
        let mean_resolution_credit = total_credit / n;
        let keep_for_training = mean_resolution_credit >= 0.62
            && solve_rate >= 0.50
            && test_pass_rate >= 0.60
            && tool_error_rate <= 0.25;

        ResolutionReport {
            n_runs: runs.len(),
            solve_rate,
            test_pass_rate,
            regression_coverage_rate,
            sandbox_rate,
            tool_error_rate,
            mean_resolution_credit,
            keep_for_training,
            runs: scores,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn trains_verified_sandboxed_resolution_runs() {
        let runs = vec![IssueResolutionRun {
            run_id: "r1".into(),
            issue_hash: "abc".into(),
            reproduction_present: true,
            patch_generated: true,
            tests_run: true,
            tests_passed: true,
            regression_tests_added: true,
            files_touched: 3,
            sandboxed: true,
            tool_errors: 0,
            human_review_required: false,
        }];
        let report = ResolutionGate::evaluate(&runs);
        assert_eq!(report.n_runs, 1);
        assert!(report.mean_resolution_credit >= 0.95);
        assert!(report.keep_for_training);
        assert_eq!(report.runs[0].gate, "train");
    }

    #[test]
    fn rejects_broad_unverified_tool_error_runs() {
        let runs = vec![IssueResolutionRun {
            run_id: "r1".into(),
            issue_hash: "def".into(),
            reproduction_present: false,
            patch_generated: true,
            tests_run: true,
            tests_passed: false,
            regression_tests_added: false,
            files_touched: 30,
            sandboxed: false,
            tool_errors: 2,
            human_review_required: true,
        }];
        let report = ResolutionGate::evaluate(&runs);
        assert!(!report.keep_for_training);
        assert_eq!(report.runs[0].gate, "reject");
    }
}
