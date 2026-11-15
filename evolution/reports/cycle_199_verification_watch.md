# cycle_199 — APEX V10.3 每周 verification/watch

## 结论
状态：部分达成。运行验证、Variant A 注册及本地归档完成；skill 独立基线待审批、技能 preflight 的 cargo 异常漏报仍未修复。不声称实测能力提升。
时间：2026-11-16T00:12:02.860969+08:00。

## 任务前真实性声明
可真实执行：声明工作目录 /home/ubuntu/apex-spiral 内的检查、备份、证据登记。只读访问 skill、EVM 和 scheduler 作为依赖；不改目录外 SOUL、共享 /tmp anchor 或 pinned skill。无 session_search/delegate_task 工具，未声称调用。用户未提交改动保留，stash 不 pop；不改 cron、生产站、provider、安全策略，不 push。幻觉风险通过原始 stdout/stderr/returncode 与注册后独立复读控制。

## 代入公式
ΔG = G_base × (Λ·Θ·K·ξ·Ψ·Φ)/(H·T·ε)。G_base=0.50 为政策默认，Λ、Θ、K、ξ、Ψ、Φ、H、T、ε 均 unknown；本轮实测 ΔG=unknown。
本轮实际运行 CLI 重算配置门控：ΔG_current=1.0581，G_neuro=1.1142，G_self=1.0908，G_evm=1.06，G_devour=1.0，ΔG_candidate=1.404。gate_open=true，5 项子门控通过。这是配置重算，不是新能力 benchmark；不把历史 housekeeping 因子表当测量。

## 找问题
1. 所有现有 head/head_cycle/last_cycle 初始一致为 cycle_198，最新 cycles 键也是 cycle_198，因此 Variant A，无旧 metadata gap。
2. 兼容入口 SKILL.md/references/scripts 均为指向 root 的 symlink farm，结构通过；自比较 SHA 和递归镜像相等不是独立内容证明。
3. 入口 live SHA 为 `f7a359c3b06a20f30a91f95baffbcbaa7d8a95f36aba24bafb9276e7279cb36a`，保留的 approved baseline 为 `8f9eb24e5d59e696c4b99570fc27fd1b00fd4f4bf36dad984b5c3d6f460a22e6`，仍不相符。没有把 cycle_198 的 observed SHA 自动转为批准基线。上轮与本轮 source payload 清单差异：["references/fail-closed-watch-verification.md"]。内容变化不等于已获批准，未自动背书。
4. skill preflight 的 cargo 异常聚合缺陷仍可复现：模拟 FileNotFoundError 时返回 error 且无 returncode，旧规则 `not in (0,None)` 未标失败；正确规则 `returncode != 0` 会失败。本轮独立直接执行三 crate 测试，不依赖这一缺陷分支。只报告，未越界修改技能。
5. gene_pool_stats 仍为 genes=19/cycles=75，实际 gene_pool=21、注册后 cycles=94；旧计数字段语义不确定，保留不改。SOUL 仍指向旧 tick，目录外文案未改。
6. 本轮未发现新的、有证据支持且可在授权范围内修复的运行缺陷，选择 watch；不为产生增益数字而改代码。

## 优化
- 备份 registry、experiments.jsonl、watch_archive.sqlite 到 maintenance/cycle_199/backup/，不在技能测量树中创建备份；本轮 SQLite 使用 backup API，不以裸文件复制假设 WAL 已落盘。
- 注册前比较 registry 快照以发现并发变化，但此比较不是 writer lock；多工件提交不具备跨文件原子性。
- 新增本轮证据 runner/audit/finalize 工件；alias/head/approved SHA/harness 四类门控各验证正反路径，共 8 项夹具通过。
- 新增 cycle_199 并滚动所有 head/timestamp 别名，保留全部旧 cycle、其他顶层数据及 list 类型 drift_repair_cycles。不新增基因、不声称新能力门控。
- 追加 experiments 与 SQLite watch archive，本地 session_anchor 留存当前状态；已知 SHA 批准基线连续保留。

## 验证
|真实命令/检查|本轮结果|
|---|---|
|根目录 cargo test --offline|95 passed / 0 failed|
|apex_devour/ cargo test --offline|60 passed / 0 failed|
|evomaster_claw_core/ cargo test --offline|3 passed / 0 failed|
|python3 -B -m pytest tests -q -p no:cacheprovider|198 passed|
|python3 -B scripts/apex_harness_cycle.py|verification_ok=true；decision=allow；risk=0.24|
|python3 -B scripts/indicator.py --json|V_H=true；I_continue=false；无坏 JSON、orphan、registry_without_file|
|apex_devour/ cargo run --offline --quiet -- gate|5 子门控通过|
|EVM venv EVMCore.calculate_evm()|0.7691199999999999；defect_total=0.0；非零项=0|
|python3 -B maintenance/cycle_199/audit.py|8 正反向夹具通过；独立 SHA 基线不匹配|
|preflight --cron-id 5f24f9cc168e|exit=0 但带 warnings，不等于全部审计项健康|

Rust 合计 158；pytest 已包含 harness 回归，不重复累加。Rust 编译 warning 保留在各 JSON stderr。EVM 零缺陷只是其模型输出，不表示整个系统无缺陷。
当前 scheduler 身份经 jobs.json 只读发现，并由 preflight 复核为 enabled、每周一 00:00 `0 0 * * 1`、marker 存在；未创建/修改任务。
参考文件顶层 119，递归 128；脚本顶层 6（已有 pycache 不计顶层源文件）。source payload 哈希清单在 verifier_audit.json。

## 输出证据 / 变更文件
- 修改：evolution/registry.json、evolution/experiments.jsonl、evolution/watch_archive.sqlite。
- 新增：evolution/reports/cycle_199_verification_watch.md；maintenance/cycle_199/ 下 runner、audit、finalize、备份、JSON 原始输出、registry diff、本地 session_anchor 和 final_verification。
- 核心证据：maintenance/cycle_199/final_verification.json；maintenance/cycle_199/verifier_audit.json；cargo_*.json、pytest.json、runtime_gate.json、harness_final.json、indicator_final.json。
- 回滚材料：maintenance/cycle_199/backup/。恢复前须确认没有新的并发注册/归档；禁止 git reset、stash pop 或批量删除。

## 未完成 / 风险 / 真实性门控
已达成：本轮命令验证及 watch 登记归档；未达成：skill approved baseline 审批与目录外 preflight 修复；未验证：真实能力提升（unknown）。SOUL 和共享 session anchor 未同步，当前准确状态以本地证据为准。已有 fail-closed-watch-verification.md 已覆盖本轮遇到的风险，不新增重复 skill、不修改 pinned skill。
最终复读和归档哈希以 final_verification.json 为准；任何断言失败均不得把本轮视为完成。维护动作不等于实测能力提升。
