# Cycle 169 — Held-out attestation request binding candidate

## 结论
- 状态：部分达成（candidate/hold，本轮无晋升）
- 今日机制：**远端 evaluator 回执必须绑定 candidate hash + challenge nonce + evaluator identity**，否则“签名通过”仍可能接受旧回执重放或另一候选的结果。

## 代入公式
```text
candidate_score = G_base × signature_gate × request_binding × fail_closed × regression_safety
                = 0.50 × 1.0 × 1.0 × 1.0 × 1.0
                = 0.50
```
该数字仅表示本地 candidate 证据完整度；真实 held-out 泛化增益 = `unknown`，不作晋升声明。

## 找问题
复用 cycle165 off-host 接口后发现：原 `OffHostAttestation` 只含 verdict / expected hash / time / signature / evaluator key id，**没有把 candidate_id、candidate_sha256、challenge_nonce 纳入签名载荷**。因此协议层无法证明回执属于当前请求，存在 replay / candidate-swap 风险。

## 优化
新增最小、可回滚 candidate：
- `maintenance/heldout_attestation_binding/cycle169/gate.py`
- `tests/test_heldout_attestation_binding_gate.py`

门控只接收 request + attestation，不接收 sealed expected；验证：
1. evaluator key identity；
2. HMAC signature；
3. candidate_id / candidate_sha256 / challenge_nonce 三项绑定；
4. 缺字段、hash/verdict 格式失败闭合；
5. 即使全通过也只返回 `candidate_verify`，`promotion_allowed=false`。

## 验证与证据
```text
红灯基线：实现文件不存在时，6/6 测试失败（FileNotFoundError）。

python3.12 -m py_compile \
  maintenance/heldout_attestation_binding/cycle169/gate.py \
  tests/test_heldout_attestation_binding_gate.py
exit=0

python3.12 -m pytest tests/test_heldout_attestation_binding_gate.py -q
6 passed in 0.02s

回归集（held-out / independent evaluator / experience memory / skill lifecycle / daily acceptance）
88 passed in 2.81s
```

覆盖的负控：nonce replay、candidate hash swap、verdict tamper、wrong evaluator key、missing binding field。

## 边界 / 未验证
- 仅本地 HMAC replay；不是非对称签名、硬件密钥、真实跨主机传输或组织独立 evaluator。
- HMAC secret 与 verifier 同机，不能证明远端信任域；真实 off-host round trip 仍为 `unknown`。
- 未修改 cron、registry、genes、正式 Skill、SOUL 或生产配置；仓库历史脏状态未清理，本轮仅新增上述 candidate/test/report。
- web 检索 0 次，subagent 0 个，基础模型权重未修改。

## 下一轮唯一主题
held-out 泛化验证续作：**attestation freshness window + nonce 单次消费账本**，验证“绑定正确但重复提交同一已签回执”是否能被可靠拒绝；仍保持 candidate/hold，除非有独立 evaluator 证据。