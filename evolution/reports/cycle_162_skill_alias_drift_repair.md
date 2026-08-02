# cycle_162 — cron alias drift repair (2026-07-29)

**Cycle index**: 162 (17th consecutive drift-repair cycle: 134→162)
**Timestamp**: 2026-07-29T00:00:00+08:00
**Status**: `completed_cron_alias_drift_repair`
**Mode**: normal cycle (drift=1 → MUST NOT be verification/watch)

## What happened

9-step cron verification step 2 (alias drift auto-detect) returned **alias_drift=1**:

- SKILL.md hash mismatch: root `6c032f6e...` vs mlops `1058d3f0...`
- `diff -q references/` non-empty: only root had `cycle-161-verification-watch-soul-sync.md`
- `diff -q scripts/` empty (3/3)

**Drift source**: cycle_161 verification/watch-mode entry on 2026-07-28 wrote
`references/cycle-161-verification-watch-soul-sync.md` to root alias only.

## Trap reaffirmations

- **Trap 24 confirmed**: drift latency can span multiple cycles. cycle_161 watch-mode
  reference write (drift source) created drift that was first detected in cycle_162
  (latency = 1 day = 1 cron run interval).
- **Trap 26 reaffirmed**: cron prompt `[CRON SYNC INVARIANT]` exact marker IS present
  (verified via `grep -c "[CRON SYNC INVARIANT]" jobs.json` = 1), but the invariant
  is text-only enforcement — drift remains structural until write_file post-action
  auto-cp wrapper hook is implemented at the Hermes tool level.
- **Trap 23 fixed correctly**: `references_count = 89` was set AFTER both the
  cp-sync AND the catch-up reference file creation (cycle-161 was actually written
  during cycle_161 itself; this cycle's repair did not add a new reference file).
  Verification: `ls ~/.hermes/skills/{root,mlops}/references/ | wc -l` both return 89.

## Drift repair executed (same-turn sync)

1. `cp ~/.hermes/skills/apex-spiral-v10/references/cycle-161-verification-watch-soul-sync.md \
       ~/.hermes/skills/mlops/apex-spiral-v10/references/`
2. `cp ~/.hermes/skills/apex-spiral-v10/SKILL.md \
       ~/.hermes/skills/mlops/apex-spiral-v10/SKILL.md`
3. `sha256sum` both sides: `6c032f6ebca0fcacedd0b62719d8b3921340be392dd5e0c136b0a68a8579f437`
4. `diff -q references/` → empty (89/89) ✓
5. `diff -q scripts/` → empty (3/3) ✓
6. Final `alias_drift` = 0 ✓

## All 9 verification steps passed

| Step | Check | Result |
|------|-------|--------|
| 1 | `git stash list` | empty (no stash) ✓ |
| 2 | alias drift auto-detect | drift=1 → repair ✓ |
| 3 | `apex_spiral.__version__` | 0.3.0 ✓ |
| 4 | `apex_self_check` | cycle 101, ΔG=2.2713, HEALTHY (Shannon plateau) ✓ |
| 5 | EVM Python | EVM=0.7531, defect_rate=0.0208, G_evm=1.0579 ✓ |
| 6 | Gini selector | gene_594 (uniform fallback, n_history=62) ✓ |
| 7 | `apex_devour gate` | gate_open=true, 5/5 pass, ΔG_candidate=1.4040 ✓ |
| 8 | registry null/orphan scan | 0 nulls, 0 orphans, 66 cycles ✓ |
| 9 | dashboard refresh | 3809B HTML + 1079B MD ✓ |

## Registry entry summary (cycle_162)

- `status`: `completed_cron_alias_drift_repair`
- `selected_gene`: `skill_alias_drift_repair`
- `delta_g`: 1.8088 (inherited from cycle_160 — no new measurable gate)
- `gain_ratio`: 1.0
- `references_count`: **89** (post-sync, per Trap 23)
- `scripts_count`: 3
- `sha256`: `6c032f6ebca0fcacedd0b62719d8b3921340be392dd5e0c136b0a68a8579f437`
- `verification.gates`: all 9 steps PASS

## Structural diagnosis

Drift has been endemic since cycle_134 (16 cycles). Each drift repair correctly
restores both aliases, but the **next** cron run always re-introduces drift
because:

1. Cycle repair only fixes known files; any subsequent `write_file` to root
   `references/` (including the new cycle's report before it's cp'd) reopens drift.
2. `cp` is not in the Hermes `write_file` post-action hook, so agent must
   remember to do it in the SAME turn.
3. verification/watch mode allows reference writes (per cycle_133 precedent)
   which compounds the opportunity for drift.

**Mitigation candidates** (NOT executed this cycle, governance-only):

1. Promote invariant to `write_file` post-action hook at Hermes tool level
   (P0 candidate — needs Hermes team change, not agent-changeable).
2. Add a cron prompt pre-execution `rsync -a --delete root → mlops` step so
   cron always starts with clean alias state.
3. Constrain cron to root-only writes during normal cycle mode and require
   verification/watch mode to do nothing (only write a short markdown report).

Until a structural fix lands, every drift repair cycle will continue to be a
normal cycle (status=`completed_cron_alias_drift_repair`).

## Boundary declarations

- This cycle is governance-only, no new measurable gate, no new gene JSON,
  no V10.3 formula change.
- `delta_g` and `gain_ratio` inherited from cycle_160 (paradigm-only).
- The 17th consecutive repair is structural evidence of an endemic problem,
  not agent error.
- Cron prompt invariant enforcement is text-only; real fix requires Hermes
  tool-level change.
