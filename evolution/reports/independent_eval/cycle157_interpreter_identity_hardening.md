# Cycle 157 — Independent Evaluator Interpreter Identity Hardening

## Status
Candidate/hold. No promotion, registry, gene, Skill, cron, or production configuration change.

## Formula substitution
One mechanism only: independent evaluator identity boundary.

`delta_g_study = 0.50 * (1.00 * 0.55 * 1.00 * 1.00 * 1.00 - 0.35) = 0.100000`

The 0.55 process-isolation score and 0.35 residual risk are conservative study labels, not measured universal constants. Semantic and organizational independence remain unverified.

## Problem found
The existing runner pinned evaluator path and SHA-256, but launched it with `sys.executable`. Therefore the executable that interprets the pinned evaluator source was not itself part of the attested identity. A changed interpreter could alter evaluator behavior while the evaluator file hash stayed unchanged.

## Minimal optimization
- Backed up runner, identity JSON, and test before editing.
- Added pinned `interpreter_path` and `interpreter_sha256` to the candidate identity document.
- Runner now executes the pinned interpreter and fails closed if either interpreter path or digest differs.
- Added a regression test proving that a byte-identical interpreter at an unpinned path is rejected.

## Verification evidence
- `python3.12 -m pytest tests/test_independent_evaluator_runner.py -q` -> `5 passed in 0.52s`.
- Python compile and JSON parse checks -> exit 0.
- Positive attestation: `cycle157_interpreter_pinned_attestation.json` -> process boundary true, evaluator identity match true, interpreter path `/usr/bin/python3.12`, interpreter digest match true, input unchanged true, `promotion_allowed=false`.
- Counterexample: copied byte-identical Python interpreter to a temporary path; runner exited 2 with `failure_mode=evaluator_identity_mismatch`, while actual and expected interpreter SHA-256 were equal. This verifies path pinning fails closed rather than accepting digest-only aliases.

## Boundaries
- Process, source, and interpreter identity isolation is necessary but not sufficient for independent evaluation.
- Semantic independence, separate authorship, separate data provenance, and organizational independence remain false/unverified.
- The child recommendation remains `candidate`; this runner never authorizes promotion.
- 本轮无晋升。

## Next single topic
Experience-memory contamination prevention: test a quarantine boundary that prevents evaluator outputs from becoming trusted memory before independent acceptance.
