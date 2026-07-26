# Candidate: Atomic Skill Lifecycle Gate

One mechanism only: keep each Skill candidate limited to one capability and require a tested rollback contract before it can even become promotion-ready.

## Formula

```text
S_atomic = A_one * B_scope * I_hash * E_independent * H_heldout * R_tested
```

Every factor is binary in this candidate. Unknown operational false-admit/false-hold rates remain `unknown`.

## Contract

- exactly one capability per candidate;
- non-global scope;
- content-addressed artifact manifest;
- unit-test, held-out, and independent-evaluator evidence labels;
- rollback snapshot, restore command, and tested flag;
- output is advisory only: `promotion_allowed=false`, `writes_skill=false`.

## Boundary

Passing this gate means only `candidate_ready`. It does not promote, install, edit, or activate any formal Skill, registry entry, gene, cron job, or model weight. Real held-out fixtures and a semantically independent evaluator are still required before promotion.
