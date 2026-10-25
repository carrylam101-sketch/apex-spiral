# cycle_196 — APEX 每周 verification/watch + 有限验证器修复

状态：部分达成。日期：2026-10-26（Asia/Shanghai）。Variant A；未发现前轮 registry head gap。

## 任务前真实性声明
可执行范围为 /home/ubuntu/apex-spiral 的本地验证、有限修复、注册与归档。已有未提交文件保留；stash 实查为空。无 delegate_task/session_search 工具，因此主会话直接执行，不声称有子 agent 或跨会话搜索。未修改 cron、生产站点、provider、安全策略或技能文件，未 push。SOUL 与共享 /tmp anchor 属于本轮声明工作目录外，未写；本地状态锚点见 maintenance/cycle_196/session_anchor.json。

## 代入公式
ΔG = G_base × (Λ·Θ·K·ξ·Ψ·Φ)/(H·T·ε)。G_base=0.50 仅为政策默认，其余九个因子均 unknown；本轮实测能力 ΔG=unknown，不从历史赋值。
CLI 本轮重新执行得到 ΔG_current=1.0581、G_neuro=1.1142、G_self=1.0908、G_evm=1.0600、G_devour=1.0000、G_apex_ib=1.0300、ΔG_candidate=1.4040，gate_open=true。这是配置基线的程序重算，不是新能力基准测试。
历史 cycle_195 报告公式中间行把 G_base 重复乘入：六因子乘积实际为 0.612583712，乘 0.5 后为 0.306291856，最终 0.29153993527508093。保留历史原件，只记录纠错证据，不计本轮增益。

## 找问题
1. `scripts/apex_harness_cycle.py` 只打印子进程 JSON，不依据拒绝、非零退出或解析错误设置进程失败；可导致命令成功与门控成功混淆。6 项 test-first 测试均先失败，再修复。
2. skill 结构仍为 symlink farm，但入口 SHA 与 cycle_195 独立记录不一致：旧 `8f9eb24e5d59e696c4b99570fc27fd1b00fd4f4bf36dad984b5c3d6f460a22e6`，现 `ee6fc831609d4a039999f49d7ea487ae06c3260ce6fb1fff6d24948531941d53`。来源未确证，未批准替换 known-good。
3. skill preflight 的 cargo 异常被包装为 error，聚合却接受 returncode=None；通过 FileNotFoundError 注入复现，legacy_aggregation_would_flag=false。未改工作目录外技能，报告待维护。
4. preflight 文案要求独立 SHA 对比但实现未做；本轮额外 audit 已补足检查。默认 cron ID 过时，本轮显式传当前只读发现的 `5f24f9cc168e`；调度 `0 0 * * 1`，enabled=true，marker 存在；无修改。
5. `gene_pool_stats` 仍为 genes=19/cycles=75，实际 gene_pool=21、本轮注册后 cycles=91；字段语义未建立，未擅改。SOUL 中旧计数/周期未同步，明确保留风险。

## 优化
- 对 harness 最小修复：新增 verification_ok，要求三个子进程 returncode=0、omega registry.ok=true、harness decision=allow、V_H=true、I_continue=false；不满足返回 1。
- 新增 `tests/test_apex_harness_exit_gate.py`，覆盖健康、非零、非法 JSON、拒绝、indicator 不健康、registry 失败。
- registry 注册 cycle_196，并同步 head/head_cycle/last_cycle、last_updated/last_verified/updated_at。既有 cycles、基因池和 list 类型 drift_repair_cycles 不改。
- 使用本地 `evolution/experiments.jsonl` 与 `evolution/watch_archive.sqlite` 保存本轮记录；工作目录内未发现既有同类归档，本轮初始化专用 watch 归档，不触碰外部研究库。
- 不新增基因，不引入外部机制，不声称 APEX_NEW 能力升级。

## 验证
|真实命令/检查|结果|
|---|---|
|根目录 `cargo test --offline`|95 passed，0 failed|
|apex_devour/ `cargo test --offline`|60 passed，0 failed|
|evomaster_claw_core/ `cargo test --offline`|3 passed，0 failed|
|`python3 -m unittest discover -s tests -p test_apex_harness_exit_gate.py -v`|RED 6 failures → GREEN 6 passes|
|`python3 -m pytest tests -q -p no:cacheprovider`|198 passed|
|`python3 scripts/apex_harness_cycle.py`|verification_ok=true；V_H=true；I_continue=false；risk_score=0.24|
|apex_devour/ `cargo run --offline --quiet -- gate`|5 子门控通过，gate_open=true|
|EVM venv / EVMCore.calculate_evm()|0.7691199999999999；defects 总和 0；非零项 0|
|`python3 maintenance/cycle_196/audit_verifier.py`|alias/head/SHA 正反向夹具 6 项通过；实际 skill 基线不匹配|
|preflight，显式 --cron-id 5f24f9cc168e|exit=0，但不将其解释为所有审计项无问题|

Rust 共 158 项，本轮 pytest 198 项（已包含 harness 6 项，不重复累加）。unittest 全目录发现只运行 6 项，不能代替 pytest；该次还输出 PyTorch 未安装、使用纯 Python 模式的 warning。Rust stderr 警告保留在原始 JSON 日志，不声称零警告。

## 输出证据
- 主报告：`evolution/reports/cycle_196_verification_watch.md`
- 原始命令、stdout/stderr/returncode：`maintenance/cycle_196/*.json`
- test-first：`maintenance/cycle_196/tdd_red.log`、`tdd_green.log`
- 独立基线与递归 payload SHA 清单：`maintenance/cycle_196/verifier_audit.json`
- 变更前原件：`maintenance/cycle_196/backup/registry.json`、`backup/apex_harness_cycle.py`
- 最终核查：`maintenance/cycle_196/final_verification.json`
- 归档：`evolution/experiments.jsonl`、`evolution/watch_archive.sqlite`
- 本轮复测 skill references 顶层文件 118、递归文件 127，scripts 顶层文件 6；pycache 不作为源码 payload。三个兼容入口解析到相同 root 目标；这种自比较不是独立内容验证。

## 风险、回滚与真实性门控
整体为部分达成：代码修复与本地运行验证完成；skill 独立基线差异、技能 preflight 缺陷、旧 SOUL 文案仍待处理。未证明任何能力提升。
回滚仅限先检查后恢复本轮 backup 中 harness/registry，保留本轮新增证据文件，不做 git reset、stash pop、批量删除。恢复 registry 前须确认无人追加新 cycle。
技能维护建议保存在本地证据，不修改可能 pinned 的技能，不另建同名 skill。后续如获授权，应把 cargo 异常聚合回归测试加入规范；本轮不等待人工确认、不越界执行。
真实性门控：所有完成声明均对应本轮工具输出；未运行项与未解决项显式区分。EVM 的零缺陷是其当前模型输出，不表示全系统真实零缺陷。
