# Cycle 166 — Experience-memory append-only hash chain (2026-08-01)

## 今日机制
经验记忆防污染：为跨会话经验记录增加确定性 append-only hash chain，检测历史内容篡改、删除、重排与重复回放。

## 代入公式
`candidate_score = G_base × integrity × fail_closed × regression_safety × no_active_write = 0.50 × 1 × 1 × 1 × 1 = 0.50`。

该分数只表示候选工件证据完整度，不表示真实自我进化增益；真实泛化增益为 `unknown`。状态保持 `candidate/hold`，本轮无晋升。

## 找问题
已有 `cycle155/quarantine_gate.py` 只验证单条记录的 payload hash、证据与 scope。它不能发现：旧记录被删除、跨会话顺序被重排、合法旧事件被重复回放，或链中间记录被替换。

## 优化
- 新增 `maintenance/experience_memory/cycle166/hash_chain_gate.py`：canonical event、SHA-256 前向链、sequence/event_id 去重、证据与 scope 门控。
- 新增 `tests/test_experience_memory_hash_chain_gate.py`：7 个 counterexample 测试。
- 工件永不写 active memory，`promotion_allowed` 恒为 false。
- 未修改 cron、registry、genes、正式 Skill、SOUL 或生产配置；未做 web 检索；未启动 subagent。

## 验证证据
- `python3.12 -m py_compile ...`：pass。
- focused pytest：`7 passed in 0.03s`。
- 相关全回归：`68 passed in 2.42s`。
- live smoke：合法 2-event chain → `candidate_chain_valid`; 篡改 event 2 → `quarantine`, reason=`event_hash_mismatch:2`。
- SHA-256：
  - gate: `ca4ba553c90eb637e83b1f1a10a21fd79d5a23ca1db08b3cff13e966538efe64`
  - tests: `a6754790eb46ec656993f8ead82880a6c854c8c015dffbd80e3d2ef10a954cb7`

## 边界 / 未验证
- 普通 SHA-256 链只能检测篡改，不能阻止有写权限者重写整条链；缺少外部签名/checkpoint/WORM storage。
- 测试数据是合成的 3-session records；真实跨会话语义污染与大规模性能未验证。
- 本轮只研究 hash-chain provenance；未研究主动遗忘、confidence decay 或 semantic conflict detection。
- 独立 evaluator 尚未对该候选工件作组织/进程边界外复核，因此不得 promote。

## 下一轮唯一主题
经验记忆防污染续作：**外部签名 checkpoint**，验证整链重写攻击能否被独立 checkpoint 检出；仍只做 candidate/hold。