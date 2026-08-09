# Cycle 171 — Held-out nonce ledger crash-consistency candidate

## 结论
- 状态：部分达成（candidate/hold，本轮无晋升）
- 今日机制：一次性 nonce 的持久账本必须在接受前完成内容校验、文件 fsync 与目录 fsync，并对截断、篡改和中断写入 fail closed。

## 代入公式
```text
candidate_score = G_base × exclusive_create × integrity_check × file_sync × dir_sync × regression
                = 0.50 × 1.0 × 1.0 × 1.0 × 1.0 × 1.0
                = 0.50
```
该分数只表示本地 candidate 门控覆盖度；真实 held-out 泛化增益为 `unknown`。

## 找问题
Cycle 170 用 `O_CREAT|O_EXCL` 防并发重放并调用文件 fsync，但存在缺口：写入中断会留下空/截断 marker；旧逻辑只凭 marker 存在便视作已消费，且未验证 marker 内容、未 fsync 父目录。因此它虽偏 fail closed，却无法区分完整消费记录与损坏记录，也不能声称目录项已持久。

## 优化
新增最小、可回滚 candidate：
- `maintenance/heldout_nonce_ledger/cycle171/gate.py`
- `tests/test_heldout_nonce_ledger_crash_gate.py`

门控流程：
1. `O_CREAT|O_EXCL` 原子抢占 nonce marker；
2. 写入规范化 record 与 SHA-256 完整性摘要；
3. `fsync(marker)` 后回读并校验内容；
4. `fsync(parent directory)` 成功后才返回 `candidate_verify`；
5. 空文件、截断、篡改、写入异常、目录异常全部 `hold`；
6. 即使通过仍 `promotion_allowed=false`。

## 验证与证据
```text
红灯基线：实现文件不存在，7/7 测试失败（FileNotFoundError）。
python3.12 -m py_compile <candidate> <test>  -> exit 0
python3.12 -m pytest tests/test_heldout_nonce_ledger_crash_gate.py -q
7 passed in 0.06s

held-out 链回归集：
58 passed in 1.96s
```
负控覆盖：重复消费、空 marker、内容篡改、模拟首次写入中断、模拟目录 fsync 失败、ledger 路径损坏、8 路并发仅 1 路接受。

## 边界 / 未验证
- 仅本机文件系统 fault injection；未执行真实掉电、内核崩溃、磁盘缓存失效或重启恢复实验。
- 不证明所有文件系统的 fsync 语义，也不提供跨主机/分布式原子账本。
- SHA-256 只检查 marker 自一致性，不是外部签名或硬件信任根。
- 未修改 cron、registry、genes、正式 Skill、SOUL 或生产配置；web 检索 0 次，subagent 0 个。
- 本轮无晋升。

## 下一轮唯一主题
held-out 泛化验证续作：**重启恢复审计与账本枚举**，验证进程重启后能扫描并分类完整、损坏、冲突 marker，且任何不确定状态都保持 hold。
