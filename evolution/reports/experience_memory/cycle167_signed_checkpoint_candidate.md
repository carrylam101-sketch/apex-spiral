# Cycle 167 — Experience-memory external signed checkpoint (2026-08-02)

## 今日机制
经验记忆防污染：用独立持钥方的 Ed25519 签名 checkpoint 绑定 `chain_id + event_count + head_hash + issued_at + signer_id`，补上普通 hash chain 无法识别“攻击者重写整链并重新计算全部哈希”的缺口。

## 代入公式
`candidate_score = G_base × rewrite_detection × fail_closed × regression_safety × no_active_write = 0.50 × 1 × 1 × 1 × 1 = 0.50`。

该分数只表示候选工件证据完整度，不代表真实自我进化增益；真实污染降低率与泛化增益均为 `unknown`。状态保持 `candidate/hold`，本轮无晋升。

## 找问题
cycle166 的 SHA-256 前向链能检测局部篡改、删除、重排与回放，但拥有写权限的攻击者可重写全部历史并重算一条内部自洽的新链。若没有链外可信锚点，验证器会把重写后的链判为有效。

## 优化
- 新增 `maintenance/experience_memory/cycle167/signed_checkpoint_gate.py`。
- 采用环境已有 `cryptography 41.0.7` 的 Ed25519；验证器只接收 trusted public key，不接触外部私钥。
- checkpoint 与 chain report 交叉核对 event count/head hash，并对未知 signer、字段篡改、错误签名编码、错误私钥重签全部失败闭合。
- 新增 `tests/test_experience_memory_signed_checkpoint_gate.py`，共 7 个正反例。
- 未修改 cron、registry、genes、正式 Skill、SOUL 或生产配置；未做 web 检索；未启动 subagent。

## 验证证据
- `python3.12 -m py_compile ...`：pass。
- focused pytest：`7 passed in 0.10s`。
- 相关全回归：`75 passed in 2.39s`。
- live counterexample：原链与整链重写各自 `chain_valid=true`；旧外部 checkpoint 对重写链返回 `quarantine`，reason=`head_hash_mismatch`。
- SHA-256：
  - gate: `4c71f268889753571603c56ef1a522b0bda8ccba082b9d7f5826c3110322fd99`
  - tests: `6a143078a497808656961138535ccf2f7fdf7242f3e64c2b81720304f0acf39a`

## 边界 / 未验证
- 本轮“外部”仅由测试中的独立密钥对象模拟；私钥尚未放在另一进程、主机、HSM 或 WORM 日志中。
- 没有 checkpoint freshness、单调序号、撤销/轮换、透明日志 inclusion proof；签名 checkpoint 可被回滚到旧的合法版本。
- 测试数据仍是合成小链；真实跨会话语义污染、并发 checkpoint 与性能未验证。
- 独立 evaluator 尚未在组织/进程边界外复核该候选，因此不得 promote。

## 下一轮唯一主题
经验记忆防污染续作：**checkpoint rollback/freshness 防护**，只验证“旧但签名有效的 checkpoint”能否通过单调序号或透明日志 head 被检出；仍保持 candidate/hold。
