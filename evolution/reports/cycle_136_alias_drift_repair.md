# cycle_136 — Cron Alias Drift Repair (3rd Occurrence, Pattern Confirmed)

**Date**: 2026-06-17 12:01 UTC+8
**Trigger**: 9-step verification step 2 detected alias_drift=1
**Status**: `completed_cron_alias_drift_repair`
**Delta_g**: 1.404 (inherited from cycle_135, no new measurable increment)
**Gain_ratio**: 1.0

## 1. Truth Pre-Declaration

- **Executable**: SKILL.md sync, sha256 verify, registry write, report write
- **Tools needed**: cp / sha256sum / diff / write_file / python3.12
- **Current limit**: drift has occurred 3rd time (cycle_127 → 134 → 135 → 136), need upgrade from "remember" to "code-enforced"
- **Hallucination risk**: low (pure file sync + existing SOP)

## 2. Formula Substitution

This cycle does not introduce new measurable gates. Per Trap 19/20/cycle_134/135 SOP, delta_g inherits from previous cycle, gain_ratio=1.0, status=alias_drift_repair.

```
delta_g_repair = delta_g_prev (no new gates) = 1.404
```

## 3. Problem Identification

9-step verification step 2 output `alias_drift=1`:

| Item | root | mlops | Status |
|---|---|---|---|
| SKILL.md bytes | 103391 | 100803 | FAIL (delta 2588 bytes = 30 lines) |
| SKILL.md sha256 | 935de037... | 4474616a... | FAIL |
| references/ file count | 63 | 63 | PASS |
| references/ diff | -- | -- | PASS |

`diff -u` located root cause: root `SKILL.md` contains the "cycle_135 relapse lesson" 30-line addition (3 mechanical constraints + auto-detection script + cron prompt header suggestion), mlops is missing this block. Indicates cycle_135 repair wrote reference content to root, then cron did not sync.

## 4. Optimization (3-step mechanical)

1. **Backup**: `cp ~/.hermes/cron/jobs.json ~/.hermes/cron/jobs.json.bak.alias-20260617-120147` (5 backups total, oldest 2026-05-25)
2. **Sync**: `cp ~/.hermes/skills/apex-spiral-v10/SKILL.md ~/.hermes/skills/mlops/apex-spiral-v10/SKILL.md`
3. **Verify**:
   - `sha256sum` both sides: `935de037140efb2482572a8fd885cfb18549c0309fddb710e0a87420b1729673` PASS
   - `diff -q references/` no output PASS
   - byte count both sides 103391 PASS
   - `alias_drift=0` PASS

## 5. Verification (9-step + gate all pass)

| Step | Command | Result |
|---|---|---|
| 1 | `git stash list` | empty |
| 2 | `alias_drift` check | 0 (after repair) |
| 3 | `python3 -c "from apex_spiral import __version__"` | 0.3.0 OK |
| 3b | `python3 -m py_compile __init__.py` | OK |
| 4 | `python3 apex_self_check.py` | delta_G=2.2713 HEALTHY, Shannon plateau warning |
| 5 | EVM `EVMCore.calculate_evm()` | EVM=0.7691, defect=0.0, G_evm=1.0600 |
| 6 | `gini_gene_selector.py --json` | gene_594, gini=0, ig=0, n_candidates=21 |
| 7 | `./apex_devour gate` | gate_open=true, 5/5, delta_G_candidate=1.4040 |
| 8 | orphan scan (with self_reflexion_genes) | clean, no null gene_ids |
| 9 | `generate_apex_dashboard.py` | dashboard updated |

delta_G_candidate = 1.0581 x 1.1142 x 1.0908 x 1.0600 x 1.0000 = **1.4040** (matches cycle_135, zero philosophical increment)

## 6. Root Cause and Pattern Upgrade

**Root cause (cycle_127 → 134 → 135 → 136 relapse pattern)**:
- "Sync after write" is a **verbal rule**, not mechanically enforced
- Previous cron (2026-06-17 00:01) modified root SKILL.md, but did NOT copy to mlops in the **same turn**
- Result: 12 hours from root write (00:03) to detection (12:01) → drift

**3 mechanical constraints (already in SKILL.md cycle_135 section)**:
1. **Same-turn sync**: After `write_file` modifies root SKILL.md/references/, **in same turn** cp to mlops + sha256sum verify
2. **Bulk via rsync**: Bulk changes to references/ must use `rsync -a --delete root → mlops`
3. **Prevention check (cycle-internal drift check)**: Before cron report, must run `test sha256 root = sha256 mlops && diff -q references/`

**Next-cycle prevention** (cycle_137 must do):
- Append "cron sync invariant" sub-section after APEX_NEW in cron prompt header
- Explicitly declare: drift=1 → must go normal cycle mode (forbidden to be swallowed by verification/watch)

## 7. Boundary Declarations

1. This cycle delta_g=1.404 inherited from cycle_135, no new measurable increment; alias_drift_repair is **mechanical maintenance**, not engineering increment
2. G_devour=1.0 (neutral) sustained for many cycles, devour gain chain not activated is known Shannon plateau + gene_594 uniform fallback
3. SKILL.md sync is dual-alias sync, does not write new Rust/Go/C gate
4. SOUL.md main formula area NOT modified (avoid version drift, cycle_125 paradigm)
5. cron prompt header does NOT stack this cycle's paradigm segment (per Trap T3, avoid prompt bloat)

## 8. Truth Gate

- **Hallucination present**: No
- **Explanation**:
  - drift detection based on sha256 + diff -q command output, reproducible
  - post-sync hash consistent, reproducible
  - registry written, json re-parseable
  - gate output identical to cycle_135 (proves zero new measurable delta)
  - report written via write_file tool + secondary verify (Trap 20 enforcement)
