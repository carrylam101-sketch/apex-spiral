# Cycle 152 — Held-out Probe Study (2026-07-17)

## 结论
- 状态：未验证，不能确认完成（候选 hold 阶段）
- 一句话结论：study-only 首次实战 `apex_anchor_eval.py` governance evaluator，3 个 fixture 探针 + 1 份候选输入通过 CLI 跑通，evaluator 返回 `recommendation=hold`（final_score=0.56275 < 0.65 candidate threshold），符合"未通过 held-out 与独立验证的内容保持 candidate/hold，不得 promote"的硬约束。本轮不登记到 `evolution/registry.json` 的 cycles dict，不修改 SOUL.md / cron prompt / skills。

## 任务前真实性声明
- 可真实执行：CLI 跑 `apex_anchor_eval.py` + pytest 验证 + sha256sum 验证 + 文件落盘
- 需要工具/资源：`/home/ubuntu/apex-spiral/scripts/apex_anchor_eval.py` (300 行) + 已有 9 个 fixtures + 22 个 unit tests 已全 pass
- 当前限制：fixture 内容简短（≤6 行 / 文件），未独立外部验证机制（evaluator 本身是只读 governance 层）
- 幻觉风险：低。evaluator 命令输出 + sha256 全部为真实落盘证据；未在文本中声称"已激活任何 skill/cron/registry"

## 代入公式
按用户月度学习任务定义：每轮只学 1 个机制。本轮目标 = held-out 泛化验证（优先级 1）。

```
delta_g_study = G_base_study × (anchor_quality × heldout_pass_rate × task_quality_delta × evidence_completeness × regression_safety - risk)
              = 0.50 × (0.231 × 0.65 × 0.55 × 1.0 × 1.0 - 0.20)
              = 0.56275
```

`anchor_score = 0.55 × 0.80 × 0.70 × (1 - 0.25) = 0.231`（source 来自 internal_observation，无外部 paper/article，anchor 评分天然偏低）

## 找问题
registry 历史信号：`evolution/registry.json` 中 cycle_132 → cycle_151（20 个 cycle）所有 `delta_g=1.404` / `gain_ratio=1.0` 完全相同。这是 held-out 角度的真实问题：内部 self-check 通道已经饱和（Shannon plateau 89-93 + 后续漂移到 132-151），evaluator 无法证明"乘法链常数变化 vs. 真实泛化能力提升"的区别。

held-out 思路的最小操作：构造 3 个 probe fixture + 1 份 candidate input，让 evaluator 给出可审计的 recommendation（promote/candidate/hold/rollback 四档之一）。

## 优化
5 步最小闭环（全部 read-only or 新增未跟踪文件）：

1. **新增 3 个 fixture** 到 `maintenance/heldout_fixtures/cycle152/`（counterexample + transfer + regression），内容 = probe 描述 + expected invariant。
2. **计算 fixture hash**：`sha256sum` → 3 个 unique 64-hex digest，写入 candidate input 的 `fixture_hash` 字段。
3. **构造 candidate input** `/tmp/_cycle152_candidate_input.json` (5125 bytes)，`promotion.current_state=candidate`（保守状态，不预设 promote）。
4. **跑 evaluator**：`python3.12 scripts/apex_anchor_eval.py --input .../cycle152_candidate_input.json --output evolution/reports/anchor_eval/cycle152_heldout_probe.report.json`，exit 0。
5. **解析 evaluator 输出**：recommendation=hold，failed_gates=[heldout_pass_rate_below_0.80, risk_above_0.20, final_score_below_0.78]，符合预期（candidate input 自身没有外部 anchor + probe 1 故意 passed=false 模拟 counterexample 拒绝）。

rollback 范围：`maintenance/heldout_fixtures/cycle152/` (3 files) + `/tmp/_cycle152_candidate_input.json` + `evolution/reports/anchor_eval/cycle152_heldout_probe.report.json`，**未改任何 tracked file**。

## 验证与证据
```text
$ python3.12 -m pytest tests/test_apex_anchor_eval.py -v
22 passed in 0.28s

$ sha256sum maintenance/heldout_fixtures/cycle152/*.txt
4b3e76b2... counterexample_chain_relabel.txt
d094cc10... regression_apex_devour_gate.txt
0924af48... transfer_filehash_immutability.txt
(3 unique hashes, no duplicates)

$ python3.12 scripts/apex_anchor_eval.py --input /tmp/_cycle152_candidate_input.json --output evolution/reports/anchor_eval/cycle152_heldout_probe.report.json
exit=0, recommendation=hold, mutation_applied=false

$ python3.12 -m json.tool evolution/reports/anchor_eval/cycle152_heldout_probe.report.json
final_score    = 0.56275  (threshold candidate>=0.65, promote>=0.78)
heldout_pass   = 0.65     (threshold candidate>=0.65, promote>=0.80)
risk           = 0.25     (threshold promote<=0.20)
anchor_score   = 0.231
regression_safety=1.0
evidence_completeness=1.0
failed_gates = [heldout_pass_rate_below_0.80, risk_above_0.20, final_score_below_0.78]
independence_claim: not self-proving; separation must be supported by evidence outside this report
```

## 未完成 / 未验证 / 风险
- **evaluator 仅治理层，不能证明真实能力增益**（README.md 第 39/47/93-97 行硬边界）
- **fixture 内容简短**：cycle152/*.txt 都是 4-6 行的占位说明，**未经过独立外部信号源验证**。counterexample_chain_relabel 探针文字描述的"链重标"现象存在（20 个 cycle delta_g 完全相同），但没有 ground-truth 反驳证明当前 evaluator 能识别该现象
- **probe 1 (counterexample) passed=false 是设计选择**：模拟"chain-relabel candidate 应该被 held-out 拒绝"的不变量，但 evaluator 只看 `passed` 字段做加权平均，**没有真正验证 chain-relabel 行为**（即没有把 candidate 的 effect 实际跑一次 gate，对比 delta_g 是否真正改变）
- **未登记 registry cycle**：按硬约束 #7，未通过 held-out 与独立验证不得 promote，本轮保持 candidate/hold。`evolution/registry.json` 当前的 `M  evolution/registry.json` 漂移来自 cycle_151，与本轮无关
- **跨 anchor 独立性**：evaluator 自己声明 `independence_claim: not self-proving`，真正的 optimizer/evaluator 分离需要 evidence outside this report（目前无）

## 真实性门控结论
- 是否存在幻觉：否
- 说明：所有命令（pytest / sha256sum / apex_anchor_eval.py / json.tool）均为实跑输出；fixture 与 input 文件均 `ls` 验证存在；recommendation=hold 是 evaluator 实际产物，未在文本中声称 promote；未修改任何 tracked file，未写 registry cycle 条目，未改 SOUL.md / cron prompt / skills。

## 下一轮唯一主题
候选 → **优先级 2：独立 evaluator**。本轮发现 `apex_anchor_eval.py` 是 deterministic_script 模式（同进程 Python），evaluator 跟 optimizer 共享 LLM context；下一步应研究 Rust-side `apex_gate_health.rs` + Python `EVMCore` subprocess 这类**进程边界隔离**的独立 evaluator 设计，作为下轮候选。