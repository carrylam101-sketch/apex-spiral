# Cycle 162 — Post-commit held-out fixture custody

## 结论
状态：部分达成（candidate/hold，本轮无晋升）

## 代入公式
`candidate_evidence_score = 0.50 × commit_order(1.0) × mutation_reject(1.0) × regression(1.0) = 0.5000`。仅为候选证据分；真实泛化增益为 `unknown`。

## 找问题
Cycle 161 已验证负对照辨别力，但 fixture 与候选仍由同一测试作者在同一工作区构造；仅有 hash 不能证明候选先冻结、fixture 后生成，也不能检测最小的预知/泄漏迹象。

## 优化
新增最小可回滚 candidate：`maintenance/heldout_custody/cycle162/gate.py`。流程为候选先 hash 冻结，再生成 128-bit 随机 canary，将 canary 写入至少 3 个 fixture，最后提交 fixture 与 transcript digest。门控拒绝顺序倒置、弱 canary、候选/fixture 变更，以及候选中出现后生成 canary。始终 `promotion_allowed=false`。

## 验证与证据
- `python3.12 -m py_compile maintenance/heldout_custody/cycle162/gate.py tests/test_heldout_custody_gate.py`：exit 0。
- `python3.12 -m pytest tests/test_heldout_custody_gate.py tests/test_heldout_discrimination_gate.py tests/test_heldout_owned_execution_gate.py -q`：`14 passed in 1.08s`。
- 正向路径：候选 commit 时间早于 fixture reveal，digest 完整，返回 `candidate_verify`。
- 反例：候选含 post-commit canary、顺序倒置、fixture 事后变更、canary 小于 128-bit 均 fail closed。
- web 检索：0 次；未修改 cron、registry、genes、正式 Skill 或生产配置。

## 边界 / 未验证
- canary 只能检测一个最小泄漏信号，不能证明 fixture 内容真正保密；生成器、文件权限与进程边界仍在同一主机。
- 时间戳不是可信硬件证明，transcript 也非外部签名；组织独立性与跨分布代表性仍为 `unknown`。
- 本轮无晋升。

## 下一轮唯一主题
held-out 泛化验证：研究“独立进程生成 fixture + 只向候选暴露输入、不暴露 expected”的最小可验证 candidate。
