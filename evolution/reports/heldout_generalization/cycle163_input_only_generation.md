# Cycle 163 — Separate-process input-only held-out generation

## 结论
状态：部分达成（candidate/hold，本轮无晋升）

## 代入公式
`candidate_evidence_score = 0.50 × fresh_generation(1.0) × input_only_protocol(1.0) × regression(1.0) = 0.5000`。仅为候选证据分；真实泛化增益为 `unknown`。

## 找问题
Cycle 162 已冻结候选并用 post-commit canary 约束 fixture custody，但候选仍可能接触包含 expected output 的完整 fixture。现有协议没有证明“执行时只暴露输入、执行后 evaluator 才读取 expected”。

## 优化
新增最小可回滚 candidate：
- `maintenance/heldout_input_only/cycle163/generator.py`：独立子进程在候选冻结后生成随机 probe，将公开输入与 sealed expected 分文件落盘。
- `maintenance/heldout_input_only/cycle163/gate.py`：候选仅收到 stdin；argv、白名单环境和空临时 cwd 不含 sealed 路径。全部执行结束后才加载 sealed expected 并评分；始终 `promotion_allowed=false`。
- `tests/test_heldout_input_only_gate.py`：覆盖正向、公开字段泄漏、argv/env/cwd 探测、候选变更和错误候选反例。

## 验证与证据
- `python3.12 -m py_compile ...`：exit 0。
- `python3.12 -m pytest tests/test_heldout_input_only_gate.py tests/test_heldout_custody_gate.py tests/test_heldout_discrimination_gate.py tests/test_heldout_owned_execution_gate.py -q`：`20 passed in 1.76s`。
- 实测 generator PID 与 evaluator PID 不同，生成时间晚于候选冻结时间。
- public schema 仅含 `probe_id/probe_type/stdin/custody_canary`；注入 `expected` 字段会 fail closed。
- 错误候选在 3 个 fresh probes 上均失败；候选冻结后变更时执行数为 0。
- web 检索：0 次；未修改 cron、registry、genes、正式 Skill 或生产配置。

## 边界 / 未验证
- “独立进程”不是独立 evaluator，也不是 OS 安全边界；同一用户仍可读取 sealed 文件。
- expected 的“执行后加载”由本 gate 控制流与测试证明，不是外部签名或系统调用级信息流证明。
- probe 只覆盖字符串大写这一小分布，跨任务泛化为 `unknown`；本轮无晋升。

## 下一轮唯一主题
held-out 泛化验证：研究 sealed expected 的文件权限/进程能力隔离，让 candidate 子进程在 OS 层无法读取 expected，而不扩展到其他机制。
