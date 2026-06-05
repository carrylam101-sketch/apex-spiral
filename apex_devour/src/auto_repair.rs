//! Self-healing auto-repair module for apex-devour.
//! Implements the nanoGPT-claw auto-fix pattern: parse-error → cargo check → cargo fix loop.
//! Stops when: compilation succeeds, max iterations reached, or error count stops decreasing.
//!
//! Pattern来源: hernandez42/nanoGPT-claw/src/skill/auto_fix.rs
//! 核心逻辑：cargo check → parse errors → cargo fix → repeat (max 10 iterations)
//!
//! Purpose for APEX Devour:
//! - Native Rust port of the auto-fix closed-loop repair mechanism
//! - Integrates into apex-devour as --auto-repair subcommand
//! - Provides measurable repair_outcome with iterations count and total_fixed count

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::process::Command;
use std::time::Instant;

pub const DEFAULT_MAX_ITERATIONS: usize = 10;
pub const CARGO_CHECK_ARGS: &[&str] = &["check", "--message-format=short"];
pub const CARGO_FIX_ARGS: &[&str] = &[
    "fix",
    "--lib",
    "--allow-dirty",
    "--allow-staged",
    "--message-format=short",
];

/// Input for the auto-repair evaluation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutoRepairInput {
    /// Working directory for cargo commands (defaults to current dir)
    pub working_dir: Option<String>,
    /// Maximum repair iterations (default: 10)
    pub max_iterations: Option<usize>,
}

/// Parsed compile error extracted from cargo output
#[derive(Debug, Clone)]
struct CompileError {
    file: String,
    code: String,
    message: String,
}

/// Result of a single cargo check run
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CargoCheckResult {
    pub success: bool,
    pub stdout: String,
    pub stderr: String,
    pub error_count: usize,
    pub errors: Vec<SerializedError>,
}

/// Serializable version of CompileError
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SerializedError {
    pub file: String,
    pub code: String,
    pub message: String,
}

/// Outcome of the full auto-repair loop
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutoRepairResult {
    pub success: bool,
    pub final_status: String, // "fixed" | "failed" | "max_iterations"
    pub iterations: usize,
    pub total_fixed: usize,
    pub initial_error_count: usize,
    pub final_error_count: usize,
    pub duration_ms: u64,
    pub output: String,
    pub metadata: HashMap<String, String>,
}

/// The auto-repair engine — runs parse→check→fix loop until clean or stuck
pub struct AutoRepairEngine;

impl AutoRepairEngine {
    pub fn new() -> Self {
        Self
    }

    /// Run `cargo check` and parse errors from output
    fn run_cargo_check(&self, workdir: &Option<String>) -> CargoCheckResult {
        let workdir_str = workdir.as_deref();
        let output = Command::new("cargo")
            .args(CARGO_CHECK_ARGS)
            .current_dir(workdir_str.unwrap_or("."))
            .output();

        let (success, stdout, stderr) = match output {
            Ok(o) => (o.status.success(), String::from_utf8_lossy(&o.stdout).to_string(), String::from_utf8_lossy(&o.stderr).to_string()),
            Err(e) => {
                return CargoCheckResult {
                    success: false,
                    stdout: String::new(),
                    stderr: format!("Failed to run cargo check: {e}"),
                    error_count: 0,
                    errors: vec![],
                };
            }
        };

        let combined = format!("{}{}", stdout, stderr);
        let errors = Self::parse_errors(&combined);
        let error_count = errors.len();

        CargoCheckResult {
            success,
            stdout,
            stderr,
            error_count,
            errors: errors
                .into_iter()
                .map(|e| SerializedError {
                    file: e.file,
                    code: e.code,
                    message: e.message,
                })
                .collect(),
        }
    }

    /// Run `cargo fix` and count how many issues were fixed
    fn run_cargo_fix(&self, workdir: &Option<String>) -> usize {
        let workdir_str = workdir.as_deref();
        let output = match Command::new("cargo")
            .args(CARGO_FIX_ARGS)
            .current_dir(workdir_str.unwrap_or("."))
            .output()
        {
            Ok(o) => String::from_utf8_lossy(&o.stdout).to_string(),
            Err(e) => {
                eprintln!("Failed to run cargo fix: {e}");
                return 0;
            }
        };
        output.matches("Fixed").count()
    }

    /// Parse rustc error output into structured CompileError list
    fn parse_errors(output: &str) -> Vec<CompileError> {
        let mut errors = Vec::new();
        let lines: Vec<&str> = output.lines().collect();
        let mut i = 0;

        while i < lines.len() {
            let line = lines[i];
            if line.contains("error[E") || line.contains("error:") {
                let file = if let Some(pos) = line.find("-->") {
                    let path_part = &line[pos..];
                    path_part
                        .split(':')
                        .nth(1)
                        .unwrap_or("unknown")
                        .trim()
                        .to_string()
                } else {
                    "unknown".to_string()
                };

                let error_code = if let Some(start) = line.find("error[E") {
                    let end = line[start..]
                        .find(']')
                        .map(|p| start + p + 1)
                        .unwrap_or(line.len());
                    let full = &line[start..end];
                    // Strip "error[" prefix and "]" suffix to get just "E0308"
                    full.strip_prefix("error[").unwrap_or(full).trim_end_matches(']').to_string()
                } else {
                    "E0000".to_string()
                };

                let mut message = line.to_string();
                i += 1;
                while i < lines.len()
                    && !lines[i].contains("error[E")
                    && !lines[i].contains("error:")
                    && !lines[i].contains(" -->")
                    && !lines[i].is_empty()
                {
                    message.push_str(&format!("\n{}", lines[i]));
                    i += 1;
                }
                errors.push(CompileError {
                    file,
                    code: error_code,
                    message,
                });
            } else {
                i += 1;
            }
        }
        errors
    }

    /// Run the full auto-fix loop: check → if errors → fix → repeat
    pub fn run_auto_repair_loop(
        &self,
        workdir: &Option<String>,
        max_iterations: usize,
    ) -> AutoRepairResult {
        let start = Instant::now();
        let mut iteration = 0;
        let mut total_fixed = 0usize;
        let mut last_error_count = usize::MAX;

        // Initial check
        let initial = self.run_cargo_check(workdir);
        if initial.success {
            let duration_ms = start.elapsed().as_millis() as u64;
            return AutoRepairResult {
                success: true,
                final_status: "clean".to_string(),
                iterations: 0,
                total_fixed: 0,
                initial_error_count: 0,
                final_error_count: 0,
                duration_ms,
                output: "✅ No compilation errors — system is clean".to_string(),
                metadata: vec![
                    ("status".to_string(), "clean".to_string()),
                    ("iterations".to_string(), "0".to_string()),
                ]
                .into_iter()
                .collect(),
            };
        }

        let initial_error_count = initial.error_count;

        // Loop: check → fix → repeat
        loop {
            iteration += 1;

            if iteration > max_iterations {
                let final_check = self.run_cargo_check(workdir);
                let duration_ms = start.elapsed().as_millis() as u64;
                return AutoRepairResult {
                    success: false,
                    final_status: "max_iterations".to_string(),
                    iterations: iteration - 1,
                    total_fixed,
                    initial_error_count,
                    final_error_count: final_check.error_count,
                    duration_ms,
                    output: format!(
                        "⚠️  Reached max iterations {} with {} errors remaining.\n  Manual code review required.",
                        max_iterations, final_check.error_count
                    ),
                    metadata: vec![
                        ("status".to_string(), "max_iterations".to_string()),
                        ("iterations".to_string(), (iteration - 1).to_string()),
                        ("total_fixed".to_string(), total_fixed.to_string()),
                        ("final_error_count".to_string(), final_check.error_count.to_string()),
                    ]
                    .into_iter()
                    .collect(),
                };
            }

            let (success, output) = {
                let r = self.run_cargo_check(workdir);
                (r.success, format!("{}{}", r.stdout, r.stderr))
            };

            if success {
                let duration_ms = start.elapsed().as_millis() as u64;
                let output_text = format!(
                    "✅ Auto-repair complete!\n  Iterations: {}\n  Total fixed: {}\n  Duration: {}ms",
                    iteration, total_fixed, duration_ms
                );
                return AutoRepairResult {
                    success: true,
                    final_status: "fixed".to_string(),
                    iterations: iteration,
                    total_fixed,
                    initial_error_count,
                    final_error_count: 0,
                    duration_ms,
                    output: output_text.clone(),
                    metadata: vec![
                        ("status".to_string(), "fixed".to_string()),
                        ("iterations".to_string(), iteration.to_string()),
                        ("total_fixed".to_string(), total_fixed.to_string()),
                        ("duration_ms".to_string(), duration_ms.to_string()),
                    ]
                    .into_iter()
                    .collect(),
                };
            }

            let errors = Self::parse_errors(&output);
            let current_error_count = errors.len();

            // Convergence check: if error count isn't decreasing, stop — manual intervention needed
            if current_error_count >= last_error_count && iteration > 1 {
                let duration_ms = start.elapsed().as_millis() as u64;
                return AutoRepairResult {
                    success: false,
                    final_status: "stuck".to_string(),
                    iterations: iteration - 1,
                    total_fixed,
                    initial_error_count,
                    final_error_count: current_error_count,
                    duration_ms,
                    output: format!(
                        "⚠️  Auto-repair stuck at {} errors (no progress in last iteration).\n  These errors cannot be fixed by `cargo fix` alone — manual code changes required.",
                        current_error_count
                    ),
                    metadata: vec![
                        ("status".to_string(), "stuck".to_string()),
                        ("iterations".to_string(), (iteration - 1).to_string()),
                        ("total_fixed".to_string(), total_fixed.to_string()),
                        ("final_error_count".to_string(), current_error_count.to_string()),
                    ]
                    .into_iter()
                    .collect(),
                };
            }
            last_error_count = current_error_count;

            let fixed = self.run_cargo_fix(workdir);
            total_fixed += fixed;

            if fixed == 0 {
                // cargo fix found nothing to fix but errors remain — stuck
                let duration_ms = start.elapsed().as_millis() as u64;
                return AutoRepairResult {
                    success: false,
                    final_status: "stuck".to_string(),
                    iterations: iteration,
                    total_fixed,
                    initial_error_count,
                    final_error_count: current_error_count,
                    duration_ms,
                    output: format!(
                        "⚠️  {} errors remain but `cargo fix` made no changes.\n  These are likely semantic/logic errors requiring manual fixes.",
                        current_error_count
                    ),
                    metadata: vec![
                        ("status".to_string(), "stuck".to_string()),
                        ("iterations".to_string(), iteration.to_string()),
                        ("total_fixed".to_string(), total_fixed.to_string()),
                        ("final_error_count".to_string(), current_error_count.to_string()),
                    ]
                    .into_iter()
                    .collect(),
                };
            }
        }
    }

    /// Top-level evaluate: runs auto-repair and returns structured result
    pub fn evaluate(&self, input: AutoRepairInput) -> AutoRepairResult {
        let max_iter = input.max_iterations.unwrap_or(DEFAULT_MAX_ITERATIONS);
        self.run_auto_repair_loop(&input.working_dir, max_iter)
    }
}

impl Default for AutoRepairEngine {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_errors_with_real_format() {
        let output = r#"
error[E0308]: mismatched types
  --> src/main.rs:10:5
   |
10 |     let x: i32 = "hello";
   |              --   ^^^^^ expected `i32`, found `&str`
   |
error[E0425]: cannot find value `fooo` in this scope
  --> src/lib.rs:5:12
   |
5  |     let y = fooo + 1;
    |            ^^^^ help: did you mean `foo`?
"#;
        let errors = AutoRepairEngine::parse_errors(output);
        assert_eq!(errors.len(), 2);
        assert_eq!(errors[0].code, "E0308");
        assert_eq!(errors[1].code, "E0425");
        assert!(errors[0].message.contains("mismatched types"));
        assert!(errors[1].message.contains("cannot find value"));
    }

    #[test]
    fn test_parse_errors_empty() {
        let output = "    Finished `dev` profile [optimized + target output]";
        let errors = AutoRepairEngine::parse_errors(output);
        assert!(errors.is_empty());
    }

    #[test]
    fn test_serialized_error_roundtrip() {
        let se = SerializedError {
            file: "main.rs".to_string(),
            code: "E0308".to_string(),
            message: "mismatched types".to_string(),
        };
        let json = serde_json::to_string(&se).unwrap();
        let deserialized: SerializedError = serde_json::from_str(&json).unwrap();
        assert_eq!(deserialized.code, "E0308");
    }

    #[test]
    fn test_auto_repair_result_json() {
        let r = AutoRepairResult {
            success: true,
            final_status: "fixed".to_string(),
            iterations: 3,
            total_fixed: 5,
            initial_error_count: 7,
            final_error_count: 0,
            duration_ms: 1234,
            output: "done".to_string(),
            metadata: Default::default(),
        };
        let json = serde_json::to_string(&r).unwrap();
        assert!(json.contains("\"success\":true"));
        assert!(json.contains("\"iterations\":3"));
    }
}