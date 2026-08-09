# Cycle 168 — Experience-memory checkpoint freshness (2026-08-04)

## 今日机制
经验记忆防污染：用签名的单调 `checkpoint_seq`、前序 checkpoint digest 与外部 trusted watermark，检出“旧但签名仍有效”的 checkpoint 回滚/重放。

## 代入公式
`candidate_score = G_base × rollback_detection × fail_closed × regression_safety × no_active_write = 0.50 × 1 × 1 × 1 × 1 = 0.50`。

该值只表示本轮候选证据完整度，不代表真实自我进化增益；真实污染降低率和跨任务泛化增益均为 `unknown`。状态保持 `candidate/hold`，本轮无晋升。

## 找问题
cycle167 的 Ed25519 checkpoint 可识别整链重写与错误持钥方，但一个历史 checkpoint 即使已经过期，签名仍然有效。若验证器没有链外最新 watermark，攻击者可回滚到旧链与旧 checkpoint，签名验证仍可能通过。

## 优化
- 复核并验证隔离 candidate：`maintenance/experience_memory/cycle168/freshness_gate.py`。
- v2 checkpoint 签名绑定 `checkpoint_seq` 与 `prev_checkpoint_sha256`；验证器要求序号恰为 watermark+1 且 predecessor digest 完全匹配。
- 只返回 `proposed_next_watermark`，不写 active memory、不写 trusted watermark，`promotion_allowed=false`。
- 复核 `tests/test_experience_memory_checkpoint_freshness_gate.py` 的 7 个正反例：正常下一序号、旧 checkpoint、同序号异内容、跳号、错误 predecessor、序号篡改、非法 watermark。
- 未修改 cron、registry、genes、正式 Skill、SOUL 或生产配置；web 检索 0 次；subagent 0 个。

## 验证证据
- `python3.12 -m py_compile ...`：pass。
- focused pytest：`7 passed in 0.15s`。
- 相关全回归：`82 passed in 2.52s`。
- live counterexample：底层 memory chain `chain_valid=true`，旧且签名有效的 checkpoint 对当前 watermark 返回 `quarantine`；reasons=`checkpoint_rollback_or_replay`, `checkpoint_predecessor_mismatch`；`promotion_allowed=false`。
- SHA-256：
  - gate: `dceddfd2d1b0d58faae2af48e0b1fdbe80485eb1790bc9a276e794b4771d09e7`
  - tests: `9ba2a846f94208a66e874434442d25a42cfda49427bc508e03b0b315f8a7b090`

## 边界 / 未验证
- trusted watermark 仍由测试内 dict 模拟，未外置到独立进程、主机、HSM、WORM 或透明日志；能同时改 checkpoint 与 watermark 的攻击者仍可回滚。
- 当前策略强制无跳号；真实分布式并发、多 signer、key rotation/revocation 与 checkpoint 丢失恢复未验证。
- 测试仍是合成小链；真实跨会话污染率、长期性能与组织独立 evaluator 均为 `unknown`。
- 本轮没有自动写入任何 memory 或正式配置，未达到 promote 条件。

## 下一轮唯一主题
经验记忆防污染续作：**trusted watermark 外置持久化边界**。只验证 watermark 在独立只读/append-only 存储中的原子更新与回滚检测；仍保持 candidate/hold。
