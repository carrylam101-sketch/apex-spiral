# Candidate: provenance-bound experience-memory quarantine

Status: `candidate_hold`; no active-memory writes and no automatic promotion.

Formula:

```text
M_clean = V_verified * I_integrity * E_independent * H_heldout * S_scoped * (1 - C_conflict)
```

All factors are observed binary gates in this candidate. No empirical gain is claimed.
A record is only `candidate_admit` when every gate is 1. Missing evidence, global scope,
or conflict causes quarantine; payload-hash failure causes rejection.

This candidate addresses one mechanism only: preventing unverified, mutated,
over-generalized, or conflicting experience records from contaminating active memory.
It is isolated under `maintenance/` and does not modify memory, registry, genes, Skill,
cron, model weights, or production configuration.
