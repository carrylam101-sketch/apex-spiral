# Cycle 172 — Held-out restart recovery audit candidate

## 结论
- 状态：部分达成（candidate/hold，本轮无晋升）
- 今日机制：进程重启后必须完整枚举一次性 nonce 账本，并将完整、损坏、逻辑冲突和意外条目分类；任何不确定状态 fail closed。

## 代入公式
```text
candidate_score = G_base × cold_restart × full_enumeration × integrity × conflict_detection × regression
                = 0.50 × 1.0 × 1.0 × 1.0 × 1.0 × 1.0
                = 0.50
```
该分数只表示本地 candidate 门控覆盖度；真实 held-out 泛化增益为 `unknown`。

## 找问题
Cycle 171 能原子写入、校验并 fsync 单个 nonce marker，但没有启动时恢复审计：进程重启后无法证明账本被完整扫描，也无法集中识别损坏 marker、文件名与 record 绑定错位、重复逻辑 nonce 或遗留临时文件。仅在下一次 nonce 被碰到时再发现异常，会留下未审计窗口。

## 优化
新增最小、可回滚 candidate：
- `maintenance/heldout_nonce_ledger/cycle172/audit.py`
- `tests/test_heldout_nonce_ledger_restart_audit_gate.py`

门控行为：
1. 以全新 Python 子进程模拟 cold-process restart；
2. 枚举账本目录全部条目，不把缺失目录误判为空账本成功；
3. 校验 schema/state、必填字段、record SHA-256 和 marker 文件名绑定；
4. 按 evaluator+nonce 逻辑键检测重复冲突；
5. 将非规范文件列为 unexpected；
6. corrupt/conflict/unexpected/empty/unavailable 任一存在即 `hold`；即使 clean 仍 `promotion_allowed=false`。

## 验证与证据
```text
红灯基线：实现文件不存在，7/7 测试失败。
第一次实现：5 passed, 2 failed；暴露重复逻辑 nonce 被文件名绑定错误提前遮蔽，以及负控文件名未进入 marker 解析路径。
修正后：
python3.12 -m py_compile <candidate> <test>  -> exit 0
python3.12 -m pytest tests/test_heldout_nonce_ledger_restart_audit_gate.py -q
7 passed in 0.11s

held-out 链回归集：
65 passed in 1.95s
```
负控覆盖：截断 marker、文件名绑定错位、重复逻辑 nonce、混合目录全枚举、账本缺失、空账本，以及全新解释器进程恢复 clean ledger。

## 边界 / 未验证
- 仅验证进程级冷启动，不是真实 OS reboot、掉电、磁盘缓存丢失或文件系统 journal 恢复。
- 扫描结果未签名、未保存独立审计快照，也没有 off-host evaluator 复核。
- 不提供分布式账本、跨主机一致性或可信时间。
- 未修改 cron、registry、genes、正式 Skill、SOUL 或生产配置；web 检索 0 次，subagent 0 个。
- 本轮无晋升。

## 下一轮唯一主题
held-out 泛化验证续作：**恢复审计快照的独立绑定**，让审计结果绑定到账本目录内容摘要与 evaluator challenge，防止扫描后账本变化或复用旧审计结果。
