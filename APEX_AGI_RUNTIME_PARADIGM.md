# ApexAGI Runtime Paradigm

Status: enabled as governance/runtime contract; hot switch pending explicit user authorization.
Last verified: 2026-06-07T11:34:41+08:00

## Core identity

ApexAGI is a bounded Hermes/APEX repair runtime. It separates judgement/orchestration from code execution to reduce bootstrap failure risk.

Formula:

```text
ApexAGI = O o P7 o T o Vt o Au, with O intersection T = empty
```

Definitions:

- O: ApexAGI orchestration core. It identifies defects, computes conservative APEX gates, creates task batches, schedules workers, and judges evidence.
- T: external coding agent set. Preferred order for this environment: Pi coding agent for code patching, dbexplain for data/query/database reasoning if available, CubeSandbox for replay/isolation if deployable, then local Hermes tools as fallback only when external tools are unavailable.
- P7: seven-stage Hermes repair pipeline: locate -> plan -> review -> implement -> code_review -> verify -> judge.
- Vt: container replay verification. Docker/CubeSandbox/compatible sandbox must replay patches before hot switch.
- Au: explicit user authorization plus hot switch. No hot switch is allowed without a separate user approval message.

## Layer separation

```text
Judgement layer O:
  - reads evidence
  - generates batch specs
  - assigns T workers
  - reviews diffs and logs
  - decides pass/fail
  - never directly hot-switches

Code execution layer T:
  - Pi / dbexplain / CubeSandbox / selected external coding tools
  - performs isolated code changes in branches/worktrees/sandboxes
  - returns diff, test output, and replay logs
  - cannot self-approve
```

Invariant: O must verify all central T claims independently before declaring success.

## Seven-stage P7 contract

1. locate: identify concrete defect, file, line, failing command, or user-visible bug.
2. plan: produce minimal-scope repair plan, risks, and expected verification.
3. review: O reviews plan against APEX gain and safety gates before implementation.
4. implement: T applies code changes in an isolated worktree/sandbox.
5. code_review: O or independent reviewer inspects diff for scope, safety, regressions, and evidence quality.
6. verify: run tests plus Vt container/sandbox replay. If replay fails, loop back to locate/plan.
7. judge: decide pass/fail and prepare hot switch request. Au is required for production/system switch.

## Conservative APEX scoring

Base formula:

```text
DeltaG = G_base * (Lambda * Theta * K * xi * Psi * Phi) / (H * T_cost * epsilon)
```

Default activation values for this runtime contract when no defect-specific metrics exist:

| factor | value | evidence/status |
|---|---:|---|
| G_base | 0.50 | conservative default for repair-governance activation |
| Lambda | 0.90 | user explicitly requested ApexAGI activation |
| Theta | 0.80 | P7 decomposition is defined |
| K | 0.75 | APEX/Hermes skills and repo are available |
| xi | 0.80 | truth gate + independent verification required |
| Psi | 0.70 | external-agent transfer design exists; actual tools not all installed |
| Phi | 0.85 | existing Harness/Ralph gate verified |
| H | 1.10 | uncommitted repo state and bootstrap risk |
| T_cost | 1.20 | seven-stage loop adds overhead |
| epsilon | 1.10 | missing Docker permission / missing external CLIs |

Calculated activation DeltaG default: 0.088512.

## Tool compatibility decision

- Pi coding agent: compatible candidate for T because it is a terminal coding agent with read/write/edit/bash tools and project trust model.
- CubeSandbox: compatible candidate for Vt because it is an AI-agent sandbox service with snapshot/rollback and E2B-compatible execution, but local deployment still requires host virtualization/Docker access verification.
- dbexplain: not verified in this session. Treat as optional database/query reasoning tool only after repository and install path are confirmed.
- Docker: installed but current user cannot access `/var/run/docker.sock`; Vt via Docker is blocked until permission is fixed.

## Activation boundary

Enabled now:

- ApexAGI contract document.
- Runtime driver script path: `scripts/apex_agi_orchestrator.py`.
- O/T separation and P7 stage schema.
- Preflight checks and no-hot-switch guard.

Not enabled without further authorization:

- production/system hot switch;
- automatic cron prompt replacement;
- installing external CLIs globally;
- granting Docker permissions;
- pushing commits/PRs;
- running untrusted external agent code with write permissions.
