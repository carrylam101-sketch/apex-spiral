# Cycle 105 — Issue-Resolution Benchmark Gate

- timestamp: 2026-05-26T04:04:01Z
- status: completed_native_rust_module
- selected_gene: issue_resolution_benchmark_gate

## 代入公式

APEX conservative ΔG = 0.477315 with G_base=0.7513, Λ=0.91, Θ=0.86, K=0.88, ξ=0.95, Ψ=1.03, Φ=1.02, H=1.03, T=1.01, ε=1.04.

Devour: D_devour = 0.381888; G_devour = 1.026551; ΔG_candidate = 1.058072 from ΔG_current=1.030706.

## source → mechanism → APEX mapping → measurable gate

| source | mechanism | APEX mapping | measurable gate |
|---|---|---|---|
| SWE-agent GitHub repository / SWE-bench issue-resolution loop | GitHub issue → reproduction → patch → tests; coding-agent task environment | P_decompose + IssueRepair + V_audit + Sandbox | ResolutionReport.solve_rate / test_pass_rate / regression_coverage_rate / tool_error_rate / keep_for_training |
| OpenHands OpenReview/arXiv platform papers and public project | Event-driven software-agent execution with sandboxed tools, logs, and remote runtime | LongPlan + ToolAct + Sandbox + Workflow | ResolutionReport.sandbox_rate + verification_signal + error_penalty |
| SWE-EVO/SWE-bench-style long-horizon coding-agent benchmarks | Version/history-derived issue resolution requiring tests and long-horizon codebase maintenance | V_audit + Workflow + SkillMemory + IssueRepair | Regression coverage + scope_penalty + keep_for_training gate |

## 找问题

Existing devour gates covered transition credit, reflection memory, maintenance sessions, and StraTA orchestration, but did not separately gate coding-agent issue-resolution quality. In particular, a patch could be remembered without explicit reproduction/test/regression/sandbox/scope/tool-error metrics.

## 优化

Added native Rust module `apex_devour/src/resolution.rs`, CLI subcommand `resolution`, sample `sample_resolution_runs.json`, gene JSON `evolution/genes/608_issue_resolution_benchmark_gate.json`, and registry cycle_105.

## 验证

- `cargo test` → PASS (24 tests)
- `cargo build --release` → PASS
- `./target/release/apex_devour resolution --input sample_resolution_runs.json` → PASS, n_runs=3, mean_resolution_credit=0.58, solve_rate=0.666667, tool_error_rate=0.666667, keep_for_training=false

## 边界

This is a measurable governance/benchmark gate. It is not a full RL trainer, not fine-tuning, not autonomous online learning, and does not prove superiority over SWE-agent/OpenHands/SWE-EVO.
