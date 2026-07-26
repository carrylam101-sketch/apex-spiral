# cycle_156 — skill alias drift repair (14th consecutive drift)

**Date**: 2026-07-23 (Thursday)
**Status**: completed_cron_alias_drift_repair
**Mode**: normal cycle (NOT verification/watch)
**Trigger**: 9-step cron verification step 2 detected alias_drift=1

## Truth Gate Pre-Statement

- Can really execute: yes — bash shell + cp/rsync/sha256/diff + python3 registry read
- Resources needed: filesystem write to root + mlops alias
- Current limit: inline heredoc Python with nested structures may be intercepted (Trap 22/22b) — using shell `cp` and `diff -q` instead
- Hallucination risk: low (every step is sha256/diff verified before claim)

## 代入公式

Per the mandatory invariant at cron prompt top:
- alias_drift=1 → MUST go normal cycle mode (status=completed_cron_alias_drift_repair)
- Cycle delta_g carries forward from previous cycle (no new measurable gate this run)
- gain_ratio=1.0 (paradigm-style: drift repair is governance, not new capability)

## 找问题

Step 2 of the 9-step cron verification auto-detected drift:

```text
ROOT_SKILL   = b420765ab35386f0b2972fdd7aa8db78dc105b3705de533cda8e04236d993969
MLOPS_SKILL  = bcfef5ddd02a8021c37e2c4cdeeff6ae95905bdbeca0d84ada748d637ea51999
diff -q references/  → Only in root: cycle-155-skill-alias-drift-repair.md (expanded version)
diff -q scripts/     → Only in root: detect_skill_alias_drift.sh
```

Three drift sources identified:

1. **SKILL.md** (1 line missing in mlops): the new support-file bullet for
   `cycle-155-skill-alias-drift-repair.md` was added on 2026-07-22 during the cycle_155
   drift-repair run, but was not cp'd to mlops in the same turn.
2. **references/cycle-155-skill-alias-drift-repair.md** (differing content): root has the
   expanded version (Trap-23 fix-order section + canonical detector announcement + expanded
   evidence), mlops has the short version.
3. **scripts/detect_skill_alias_drift.sh** (only in root): promoted from inline detector
   in cycle_155, but `cp` to mlops was not done in the same turn.

This is **Trap 24** at work again: the drift source is a previously-successful alias-repair
cycle's own follow-up write (the SKILL.md support-file bullet + detector script + reference
expansion were all written AFTER cycle_155 closed its repair step).

## 优化

Standard cycle_134+ SOP, executed in this exact order:

```text
1. rsync -a --delete root/references/  → mlops/references/
2. cp root/SKILL.md  → mlops/SKILL.md
3. cp root/scripts/detect_skill_alias_drift.sh  → mlops/scripts/
4. chmod 600 mlops/scripts/detect_skill_alias_drift.sh
5. Verify sha256sum on both SKILL.md (must match)
6. Verify diff -q on both references/ and scripts/ (must be silent)
```

## 验证

Post-sync verification (all in the same turn):

```text
ROOT_SKILL   = b420765ab35386f0b2972fdd7aa8db78dc105b3705de533cda8e04236d993969
MLOPS_SKILL  = b420765ab35386f0b2972fdd7aa8db78dc105b3705de533cda8e04236d993969
ROOT_REFS    = 84
MLOPS_REFS   = 84
ROOT_SCRIPTS = 3
MLOPS_SCRIPTS = 3
diff -q references/  → silent
diff -q scripts/     → silent
bash scripts/detect_skill_alias_drift.sh --json → alias_drift=0
```

Canonical detector output:

```json
{
  "root_skill_sha":   "b420765ab35386f0b2972fdd7aa8db78dc105b3705de533cda8e04236d993969",
  "mlops_skill_sha":  "b420765ab35386f0b2972fdd7aa8db78dc105b3705de533cda8e04236d993969",
  "root_references_count":   84,
  "mlops_references_count":  84,
  "root_scripts_count":   3,
  "mlops_scripts_count":  3,
  "alias_drift": 0
}
```

## Standard 9-step Verification (post-repair)

| # | Step | Result |
|---|------|--------|
| 1 | `git stash list` | empty |
| 2 | Skill alias drift (canonical detector) | **alias_drift=0** ✓ |
| 3 | apex_spiral version | **0.3.0** ✓ |
| 4 | `apex_self_check.py` | ΔG=2.2713, HEALTHY (Shannon plateau still on) |
| 5 | EVM health (Python) | EVM=0.7531, defect_rate=0.0208, G_evm=1.0579 ✓ |
| 6 | Gini selector | gene_594 (uniform fallback, gini=ig=0) |
| 7 | apex_devour gate | ΔG_candidate=1.4040, gate_open=true, 5/5 gates pass |
| 8 | Orphan scan | 0 orphans across 7 sections + self_reflexion_genes ✓ |
| 9 | Dashboard refresh | next step |

## Trap 23 fix-order applied (Trap 23 re-hit avoided)

This cycle's `references_count` field is computed **after** the rsync, not before:

```text
Step 1: rsync  → 84 files
Step 2: os.listdir count → 84
Step 3: registry.artifacts.drift_repair.references_count = 84
Step 4: verify both sides still 84
```

This avoids the cycle_151 mistake where `references_count` was set to 83 pre-sync and
remained stuck at the wrong value.

## Trap 24 Latency (still biting)

Drift source this cycle = cycle_155's follow-up writes (SKILL.md bullet, reference expansion,
detector script). Confirmed Trap 24 once more: alias drift can live for any number of cron
runs between two cp operations, and the detector fires reliably when the next detector-capable
cron run arrives.

**Cycle count of consecutive drift occurrences (cycles 134 → 156)**: 14.
**Root cause category**: structural — the `[CRON SYNC INVARIANT]` is in the cron prompt body
but does not auto-trigger filesystem sync. Drift repair SOP requires manual cp/rsync in
the same turn. Until the cron orchestrator gains a "post-write auto-sync" hook, this trap
will keep recurring every time new skill content is added.

## Honest Boundary Declaration

1. This cycle is a **governance-only** repair — no new measurable APEX gate was added.
2. delta_g for cycle_156 = cycle_155's delta_g (1.8088). No gain or loss claimed.
3. gain_ratio = 1.0 (paradigm-only / drift-repair marker).
4. The skill alias drift is **structural**, not operator error. Carrying it forward as a
   cycle entry is honest reporting, not signal inflation.
5. The Shannon plateau is **still present** in cycle_156 (ΔG_estimate=2.2713 unchanged from
   cycles 89-93). No breakthrough this cycle.
6. G_devour=1.0 (neutral) is a separate, pre-existing issue (Trap 13). Not addressed this cycle.

## Files Written This Cycle

- `evolution/reports/cycle_156_skill_alias_drift_repair.md` (this file, ~post-sync)
- `evolution/registry.json` updated with `cycle_156` entry (drift_repair block, references_count=84)
- mlops alias updated: SKILL.md + references/cycle-155-skill-alias-drift-repair.md + scripts/detect_skill_alias_drift.sh

## Evidence

- Pre-repair `sha256sum` mismatch — captured above (ROOT vs MLOPS).
- Post-repair `sha256sum` match — captured above.
- `diff -q references/` exit 0 (silent) post-repair.
- `diff -q scripts/` exit 0 post-repair.
- Canonical detector `bash scripts/detect_skill_alias_drift.sh --json` → alias_drift=0.
- registry head advanced from `cycle_155` → `cycle_156` with `drift_repair` block populated.
- All references/ files written in this cycle are tracked at count 84 (post-sync, Trap 23 safe).