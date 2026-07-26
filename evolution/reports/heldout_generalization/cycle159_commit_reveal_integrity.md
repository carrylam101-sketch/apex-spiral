# Cycle 159 — Held-out Commit-Reveal Integrity

## Status
Candidate/hold. No promotion, registry, gene, Skill, cron, model-weight, or production configuration change.

## Formula substitution
One mechanism only: held-out candidate/fixture immutability through commit-reveal.

`delta_g_study = 0.50 * (1.00 * 1.00 * 1.00 * 0.40 - 0.40) = 0.000000`

The 0.40 integrity-only utility and 0.40 residual leakage risk are conservative study labels, not universal measurements. Because hiddenness and semantic independence remain unverified, no gain is claimed.

## Problem found
The existing held-out evaluator verifies fixture location, hashes, uniqueness, and probe types, but the optimizer-facing record still supplies `passed` values. A fixture can therefore be honestly hashed yet already visible, or its result can be relabeled before evaluation. Hashing alone does not prove a real hold-out boundary.

## Minimal optimization
- Added isolated candidate `maintenance/heldout_commit_reveal/cycle159/gate.py`.
- It commits to the candidate bytes plus at least three unique fixture digests, then fails closed if candidate bytes, fixture bytes, or the manifest change after commitment.
- It explicitly reports `hiddenness_verified=false`, `semantic_independence_verified=false`, and `promotion_allowed=false`.
- Added only one focused test file; no existing tracked file was edited.

## Verification evidence
- `python3.12 -m py_compile maintenance/heldout_commit_reveal/cycle159/gate.py tests/test_heldout_commit_reveal_gate.py` -> exit 0.
- `python3.12 -m pytest tests/test_heldout_commit_reveal_gate.py -q` -> `5 passed in 0.05s`.
- Positive case: frozen candidate + three unique fixtures -> `candidate_verify`, but promotion remains false.
- Counterexamples fail closed: candidate mutation, fixture mutation, manifest relabel, and duplicate fixture digest.

## Boundaries
- Commit-reveal proves post-commit immutability, not pre-commit secrecy.
- It does not prove the optimizer never saw fixture contents or `passed` labels.
- It does not provide a semantically independent evaluator or real cross-task generalization estimate.
- Operational false-pass/false-hold rates are `unknown`.
- 本轮无晋升。

## Next single topic
Held-out generalization again: evaluator-owned probe execution, so the optimizer cannot self-declare each probe's `passed` result.
