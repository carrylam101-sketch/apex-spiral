# EvoMaster × CLAW 原生进化核心胶囊（Gene 601）

## 触发
CLAW 出现静态调用、重复犯错、轨迹不沉淀、复杂环境执行成功率不足时。

## 核心公式
- `J_claw = E[R_exec(τ)+λK_claw(τ)]`
- `π_claw(t+1)=GPT-Stream(τ(t),K_claw,Constraint_sandbox)`
- `K_claw=HashPool(Filter(τ_valid))`

## Rust 核心
路径：`/home/ubuntu/apex-spiral/evomaster_claw_core`
命令：`health`, `objective`, `cache`, `update`, `audit`

## 验证
`cargo test` + `cargo run -- audit --input sample_trajectory.jsonl --constraints sample_constraints.json`
