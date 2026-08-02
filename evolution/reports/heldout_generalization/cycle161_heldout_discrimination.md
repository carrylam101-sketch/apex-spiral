# Cycle 161 — Held-out negative-control discrimination

## 结论
状态：部分达成（candidate/hold，本轮无晋升）

## 代入公式
`candidate_evidence_score = 0.50 × target_pass(1.0) × control_reject(1.0) × regression(1.0) = 0.5000`。这只是本轮候选证据分，不等同 APEX 增益；未知的真实泛化增益保持 `unknown`。

## 找问题
Cycle 160 已让 evaluator 自己执行探针，但“目标全通过”仍不能证明探针有辨别力：一个行为等价或过宽的负对照也可能全通过。缺少已知坏控制组会把空洞测试误当成泛化证据。

## 优化
新增最小可回滚候选 `maintenance/heldout_discrimination/cycle161/gate.py`：同一冻结 fixture 集分别执行目标与 committed negative control；仅当目标通过、负对照至少失败一项且 pass-rate separation > 0 时返回 `candidate_verify`。无论结果如何均 `promotion_allowed=false`，不修改 registry、genes、Skill、cron 或生产配置。

## 验证与证据
- `python3.12 -m py_compile ...`：exit 0。
- `python3.12 -m pytest tests/test_heldout_discrimination_gate.py tests/test_heldout_owned_execution_gate.py -q`：`9 passed in 1.03s`。
- 正向单测实测：target pass rate `1.0`，negative control pass rate `0.0`，separation `1.0`，负对照失败 `3/3`。
- 反例单测实测：行为等价的 distinct control 全通过时必须 `hold`；fixture 集不同或 control 与 target 相同也必须 `hold`。

## 边界 / 未验证
- fixture 与正负候选均由本地测试作者构造，未证明预提交隐藏性、真实任务代表性或组织独立性。
- 该门控只证明测试具备一个最小的负对照辨别能力，不证明跨分布泛化，也不允许晋升。
- 本轮复用了仓库既有资料，web 检索次数为 0。

## 下一轮唯一主题
held-out 泛化验证：研究“fixture 泄漏/预知检测”的最小可验证候选，仍保持 candidate/hold。
