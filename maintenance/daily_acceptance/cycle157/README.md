# Candidate: Daily-task acceptance contract

Status: `candidate_hold`; no production writes and no automatic promotion.

One mechanism only: turn a daily task's completion claim into explicit, executable acceptance criteria bound to immutable evidence.

```text
A_daily = C_explicit * V_executable * E_hashed * N_negative * R_rollback * S_bounded
```

All factors are observed binary gates. A task is only `candidate_pass` when every criterion has a verifier, exit code 0, `passed=true`, a SHA-256 evidence reference, at least one negative case, bounded scope, declared side effects, and a tested rollback contract.

Passing remains advisory: `promotion_allowed=false`, `writes_production=false`. Operational false-pass and false-hold rates are `unknown`; real held-out fixtures and a semantically independent evaluator are still required before any promotion.
