# APEX External Anchor / Held-out Evaluation

This directory adds a small governance layer for daily APEX/Hermes tasks that learn from articles, papers, incidents, or completed work.

It operationalizes four conservative rules:

1. **External anchor** — a source is input evidence, never truth by default.
2. **Held-out probes** — at least three validation probes must be withheld from optimization, with unique frozen fixture hashes and mandatory counterexample + transfer coverage.
3. **Deterministic evaluator mode** — recommendation is computed from the evidence record, not from free-form self-assessment; actual optimizer/evaluator separation still needs external evidence.
4. **Promotion is advisory and reversible** — output is restricted to `evolution/reports/anchor_eval/`; the evaluator never activates skills, memory, cron, registry changes, or model weights.

## APEX loop

```text
代入公式 → 找问题 → 优化 → 验证 → 输出证据
```

Mapping:

- 代入公式: score source quality, mechanism clarity, mapping fit, risk.
- 找问题: define explicit acceptance criteria and historical regression probes.
- 优化: create a candidate workflow/rule/skill; do not activate it yet.
- 验证: run held-out probes, existing Harness gate, Ralph `V_H`, and tests.
- 输出证据: store the input record and evaluator report with hashes.

## Formula

```text
A_anchor = Q_source × M_mech × F_map × (1 - Ω_risk)

S_eval = 0.25 × A_anchor
       + 0.30 × H_pass
       + 0.20 × Q_task
       + 0.15 × E_evidence
       + 0.10 × R_safety
       - 0.20 × Ω_risk
```

The formula is a governance score, not proof of intelligence gain. Unknown inputs must not be inflated.

## Recommendations

- `promote`: all hard gates pass, `S_eval >= 0.78`, held-out >= 0.80, evidence >= 0.75, risk <= 0.20.
- `candidate`: partial evidence with `S_eval >= 0.65`, held-out >= 0.65, risk <= 0.30.
- `hold`: acceptance failure, Harness block, false `V_H`, critical regression, or weak score.
- `rollback`: an already active artifact develops a critical regression, held-out < 0.60, false `V_H`, or a blocking Harness decision.

A `promote` result is still only a recommendation about the evaluated artifact. It does not validate every factual claim in the source and does not prove a general capability gain. Activation requires the normal skill/memory conflict policy and, when applicable, human approval.

## Daily-task record requirements

Every evaluated task needs:

- source URL/title/retrieval time/content SHA-256;
- `not_directly_trusted: true`;
- required acceptance criteria bound to evidence;
- at least three held-out probes with explicit pass/fail results, `hidden_from_optimizer: true`, a `fixture_ref` under `maintenance/heldout_fixtures/`, SHA-256 verified against the actual fixture bytes, unique fixture hashes, and both `counterexample` and `transfer` types;
- verified evidence entries;
- current Harness and Ralph results;
- rollback reference.

Suggested held-out set for daily work:

1. factual fidelity probe;
2. counterexample / over-generalization probe;
3. transfer probe in a different task class;
4. historical regression probe;
5. executable probe for code or operations.

The optimizer may know probe categories, but should not receive hidden fixtures or expected answers before producing the candidate.

## Run

```bash
cd /home/ubuntu/apex-spiral
python3 scripts/apex_anchor_eval.py \
  --input maintenance/sample_wechat_anchor_eval.json \
  --output evolution/reports/anchor_eval/sample_wechat_anchor_eval.report.json
```

Run tests:

```bash
python3 -m pytest tests/test_apex_anchor_eval.py -q
python3 -m pytest tests -q
python3 scripts/indicator.py --json
```

## Hard boundaries

This mechanism does **not**:

- train, fine-tune, or change model weights;
- let the optimizer grade itself through free-form prose;
- automatically update a skill, memory, cron job, registry entry, or production system;
- treat an article's popularity, company valuation, repository count, or author confidence as technical evidence;
- prove a general intelligence increase from one passing sample.
