# Cycle 160 — Evaluator-Owned Held-out Execution

## Status
Candidate/hold. No promotion and no cron, registry, gene, formal Skill, model-weight, or production configuration change.

## 代入公式
One mechanism only: remove optimizer-supplied held-out `passed` labels and let the evaluator derive outcomes from subprocess observations.

`delta_g_study = unknown`

No gain is claimed because fixture secrecy, semantic independence, and operational error rates remain unverified.

## 找问题
The existing deterministic anchor evaluator accepts `held_out_probes[].passed` from the evidence record. Hash and location checks protect fixture bytes, but they do not stop an optimizer-facing record from self-declaring success.

## 优化
- Added isolated candidate `maintenance/heldout_owned_execution/cycle160/gate.py`.
- Candidate and at least three fixture files are frozen by a commitment digest before execution.
- Fixture schema contains input plus expected exit/stdout only; optimizer-supplied result fields such as `passed`, `result`, or `score` are rejected.
- The evaluator launches the frozen candidate in a subprocess, observes exit code/stdout, and computes each outcome itself.
- Added one focused test file. Pre-existing dirty files were not edited.

## 验证
- `python3.12 -m py_compile maintenance/heldout_owned_execution/cycle160/gate.py tests/test_heldout_owned_execution_gate.py` -> exit 0.
- `python3.12 -m pytest tests/test_heldout_owned_execution_gate.py -q` -> `5 passed in 0.23s`.
- Live positive sample -> `candidate_verify`, `probe_count=3`, `probe_pass_count=3`, `optimizer_supplied_pass_labels_accepted=false`, `promotion_allowed=false`.
- Fail-closed cases: supplied `passed` label, wrong expected output, post-commit candidate mutation, and post-commit fixture mutation.

## 边界 / 未验证
- Expected outputs are still stored with fixtures; pre-commit secrecy from the optimizer is not proven.
- Process execution does not establish semantic or organizational evaluator independence.
- Candidate execution has timeout and environment allowlisting, but no OS sandbox or resource quota.
- False-pass/false-hold rates and cross-task generalization are `unknown`.
- 本轮无晋升。

## 下一轮唯一主题
Held-out generalization: pre-commit fixture custody/secrecy attestation, without expanding into evaluator quality or Skill lifecycle.
