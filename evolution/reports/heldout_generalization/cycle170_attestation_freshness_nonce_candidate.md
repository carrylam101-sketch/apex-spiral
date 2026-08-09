# Cycle 170 — Held-out attestation freshness + one-time nonce candidate

## 结论
- 状态：部分达成（candidate/hold，本轮无晋升）
- 今日机制：已绑定请求的 evaluator 回执还必须通过**新鲜度窗口**，并由原子账本保证 challenge nonce 只消费一次。

## 代入公式
```text
candidate_score = G_base × binding × freshness × one_time_use × regression
                = 0.50 × 1.0 × 1.0 × 1.0 × 1.0
                = 0.50
```
该分数只表示本地 candidate 证据完整度；真实 held-out 泛化增益为 `unknown`。

## 找问题
Cycle 169 已把回执绑定到 candidate hash、nonce 与 evaluator identity，但同一份合法签名回执可被重复提交；`signed_at` 也只被签名、未做时效判定。签名正确不等于当前且未使用。

## 优化
新增最小、可回滚 candidate：
- `maintenance/heldout_attestation_freshness/cycle170/gate.py`
- `tests/test_heldout_attestation_freshness_gate.py`

门控在请求绑定与 HMAC 验证后：
1. 解析带时区的 `signed_at`；
2. 拒绝超过 300 秒的旧回执与超过 30 秒未来偏移；
3. 使用 `O_CREAT|O_EXCL` 创建 evaluator-id + nonce 的消费标记，原子拒绝重复/并发重放；
4. 无效签名或过期回执不消耗 nonce；
5. 即使通过仍 `promotion_allowed=false`。

## 验证与证据
```text
红灯基线：实现文件不存在，6/6 测试失败（FileNotFoundError）。
python3.12 -m py_compile <candidate> <test>  -> exit 0
python3.12 -m pytest tests/test_heldout_attestation_freshness_gate.py -q
6 passed in 0.05s

跨机制回归集：
94 passed in 2.64s
```
负控覆盖：同一回执二次提交、301 秒旧回执、31 秒未来回执、非法时间戳、坏签名不烧 nonce，以及 8 路并发仅 1 路接受。

## 边界 / 未验证
- 仅本机文件系统账本与本机时钟；无可信时间源、跨主机共享账本、崩溃恢复或分布式原子性证明。
- HMAC secret 仍与 verifier 同机，不构成组织独立 evaluator 或硬件密钥证明。
- 300/30 秒阈值是 candidate 默认值，业务标定为 `unknown`。
- 未修改 cron、registry、genes、正式 Skill、SOUL 或生产配置；web 检索 0 次，subagent 0 个。
- 本轮无晋升。

## 下一轮唯一主题
held-out 泛化验证续作：**持久账本的崩溃一致性与损坏 fail-closed**，验证 nonce 标记在写入中断、目录损坏或重启后不会产生重复接受。