# Cycle 164 — OS-level sealed-expected isolation capability gate

## 结论
状态：部分达成（candidate/hold，本轮无晋升）

## 代入公式
`candidate_evidence_score = 0.50 × capability_probe(1.0) × fail_closed(1.0) × regression(1.0) × isolation_available(0.0) = 0.0000`。真实泛化增益为 `unknown`。

## 找问题
Cycle 163 只证明 expected 不在 argv/env/cwd 且执行后才加载；同一 UID 的候选仍可能直接读取 sealed 文件。需要先验证当前环境是否具备 distinct UID 或 user namespace，不能把进程分离误称为 OS 保密。

## 优化
新增最小可回滚 candidate：
- `maintenance/heldout_os_isolation/cycle164/gate.py`：实测 `setpriv` 降权与 `unshare --user`；任一不可用即 fail closed，不启动候选、不披露 sealed 路径，始终禁止晋升。
- `tests/test_heldout_os_isolation_gate.py`：覆盖当前环境阻断、模拟能力存在但仍不晋升、虚假成功声明阻断。

## 验证与证据
- `python3.12 -m py_compile ...`：exit 0。
- held-out 回归：`23 passed in 1.82s`。
- live probe：`setpriv` returncode 127，`setresuid failed: Operation not permitted`；`unshare` returncode 1，`uid_map: Operation not permitted`。
- gate 输出：`decision=hold`、`candidate_execution_started=false`、`sealed_expected_path_disclosed=false`、`promotion_allowed=false`。
- web 检索：0 次；未修改 cron、registry、genes、正式 Skill 或生产配置。

## 边界 / 未验证
- 本轮验证的是“隔离能力不存在时可靠阻断”，没有建立 OS 隔离；`os_level_secrecy_verified=false`。
- 模拟 capability positive 仅验证控制逻辑，不是 live 安全证据；容器/Landlock/seccomp 等未验证。
- probe 分布仍很窄，组织独立性与跨任务泛化均为 `unknown`；本轮无晋升。

## 下一轮唯一主题
held-out 泛化验证：研究无需特权的 sealed-expected 外置 evaluator（候选执行主机不持有 expected），只做最小接口与离线回放验证。
