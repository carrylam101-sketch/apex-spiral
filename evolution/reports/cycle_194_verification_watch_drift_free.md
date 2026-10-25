# cycle_194 — APEX V10.3 verification/watch drift-free
**Timestamp:** 2026-10-21T00:25:49+08:00
**Mode:** watch (no new measurable gate) + 6 bounded repairs to the housekeeping machinery
**alias_drift:** 0 (with the F5 caveat below — the gate is tautological under the symlink farm)
**Gates:** 9/9 canonical steps pass + 158/158 cargo tests
**Cron job:** `2ea5e66b83df` active, [CRON SYNC INVARIANT] present
**Variant:** A (standard forward roll; auto-classify showed `top_head == latest_in_cycles_dict`)

## 代入公式

Scope is larger than a pure clock bump (6 evidence-backed repairs to the standing
procedure + 1 registry registration), so Λ/Θ/Φ are adjusted up from the standard
tick. Computed with exact rational arithmetic (`fractions.Fraction`), not mental math:

| Factor | Value | Note |
|---|---|---|
| G_base | 0.50 | standard for issue scoring |
| Λ (goal strength) | 0.86 | 6 defects repaired, not just a clock bump |
| Θ (strategy complexity) | 0.77 | 4 distinct defect classes (counting / arithmetic / path / gate-design) |
| K (knowledge preserved) | 0.94 | measured baseline values kept verbatim |
| ξ (fidelity) | 0.97 | JSON parse + sha + readlink verified |
| Ψ (cross-domain) | 1.00 | no cross-domain change |
| Φ (entropy reduced) | 1.05 | 6 defects removed from the standing procedure |
| H (health drag) | 1.02 | routine wear |
| T (time decay) | 1.00 | 1-day forward roll |
| ε (noise) | 1.03 | stable |

```text
ΔG = 0.50 × (0.86·0.77·0.94·0.97·1.00·1.05) / (1.02·1.00·1.03)
   = 0.50 × 0.633983658 / 1.0506
   = 0.50 × 0.603449131
   = 0.301724566
```

exact: numerator = 316991829/500000000, denominator = 5253/5000, ΔG = 105663943/350200000.

Housekeeping tick ΔG ≈ **0.301725** (above the 0.224 "safe" band, below the 0.493
"gamble" band). Stored baseline `delta_g` remains `1.404` (gate_open=true, no breakthrough).

**F3 arithmetic correction:** the factor table in the recipe previously implied
`~0.2820`, and the cycle_191/192/193 reports all published `numer = 0.561602 →
ΔG = 0.267279`. Neither follows from the factors:

```text
numerator   = 0.84·0.75·0.94·0.97·1.00·1.02 = 0.5859226800
denominator = 1.02·1.00·1.03                 = 1.0506
ΔG (standard Variant A) = 0.50 × 0.58592268 / 1.0506 = 0.2788514563
```

The published 0.267279 understated the truth by 0.011572 (−4.15%) — the numerator
was mis-multiplied. The recipe table is now `0.278851 / 0.282720`, and the checklist
now requires tool computation. Historical reports for cycles 191–193 were left
unmodified (historical evidence) and are flagged in the recipe instead.

## 找问题

Auto-classify one-liner at start of tick:

```text
top_head: cycle_193
head_cycle: cycle_193
last_cycle: cycle_193
latest_in_cycles_dict: cycle_193
NO_GAP
variant: A
```

The quiet chain (cycle_191/192/193, three consecutive clean Variant A ticks) had
been hiding six defects in the verification machinery itself:

1. **F1 — reference count stale at 116 (should be 117).** `find -L …/references -maxdepth 1 -type f | wc -l` → 117; the detector reports 117/117; cycle_192 AND cycle_193 both recorded 116. Cause: the curator umbrella pass added `watch-mode-housekeeping-migration.md` at 2026-10-18T11:52, *after* the cycle_191 tick (2026-10-18T00:03) that measured 116. Cycles 192/193 copied the number forward without re-counting — pitfall #3 failure. (Counting convention: `ls -1` → 118 because it counts the `modules/` directory as an entry; recursive → 124.)
2. **F2 — drift-repair count mechanically incremented to 41.** Deriving it from the registry over cycles 134→193: 34 cycles with `status=completed_cron_alias_drift_repair` + 2 with `delta_g_self_repair>0` (cycle_186, cycle_187) = **36**. The extra 5 came from +1 per clean tick plus counting combined Variant-B gap-closure ticks the phrase does not define. The recipe's own migration reference forbids this ("do not… increment a drift-repair count on every clean watch tick").
3. **F3 — ΔG arithmetic error** in the recipe table and in three published reports (see above).
4. **F4 — `apex_impl/` path does not exist.** `apex_impl` is the **root package** (`/home/ubuntu/apex-spiral/Cargo.toml` → `[package] name = "apex_impl"`, lib `apex_v10.rs`). `cd /home/ubuntu/apex-spiral/apex_impl` → "No such file or directory". The recipe's checklist step 2 only ran apex_devour, and the cycle_192/193 reports plus the cycle_192 walkthrough cited `apex_impl/` as a directory.
5. **F5 — the alias sha/diff gates cannot fail.** `readlink -f` shows the mlops tree (`SKILL.md`, `references`, `scripts`) is a symlink farm into the root tree — same inode. So `sha256sum` compares a file with itself, `diff -q` diffs a directory with itself, and `cp` exits 1 with "are the same file". `alias_drift=0` has been reported every tick since 2026-08-16 without ever being *capable* of reporting drift.
6. **F6 — the cron prompt's `[CRON SYNC INVARIANT]` repair recipe is unrunnable.** The live prompt prescribes `cp "$FILE" "$HOME/.hermes/skills/mlops/apex-spiral-v10/$REL"` + `sha256sum`; under the farm that `cp` exits 1. The `rsync -a --delete` variant is a self-target no-op and a latent foot-gun. **The cron prompt was NOT edited** (pitfall #7: housekeeping ticks never rewrite the cron prompt); the defect and the corrected logic are recorded for a separately authorized scheduler migration.

SOUL.md §11 lines rolled this tick: L261 (Last verified), L264 (registry head + corrected
drift-repair count), L266 (live gate baseline date), L270 (alias line + corrected
reference count + symlink-farm caveat). L268 (gene-pool "cycle_190 incremented",
n_candidates=21) deliberately left untouched — no new gene registered (cycle_193 Lesson D).

## 优化

- `references/modules/apex-cron-watch-mode-housekeeping/REFERENCE.md`:
  ΔG table row → `0.278851 / 0.282720` + F3 correction block; checklist step 1
  annotated tautological + new step 1b structural `readlink -f` check; checklist
  step 2 now runs all three crates with the correct root-package path; pitfall #3
  (counting convention + F1 fact), #4 (derive, never increment), #13 (`apex_impl/`
  → root package + F4), #14 (new: vacuous alias gate), #15 (new: cron prompt `cp`
  recipe + corrected logic); roll template corrected for the drift-repair count,
  the gene-pool line and the reference count.
- New `references/modules/apex-cron-watch-mode-housekeeping/references/cycle-194-walkthrough.md`.
- `~/.hermes/SOUL.md` §11: 4 lines rolled with corrected F1/F2 values.
- `evolution/registry.json`: `cycles['cycle_194']` appended; top-level
  `head`/`head_cycle`/`last_cycle`/`last_updated`/`last_verified`/`updated_at`
  rolled to `cycle_194` / `2026-10-21T00:25:49+08:00`. `drift_repair_cycles` left
  untouched (it is a list, not a counter — pitfall #11; still `['cycle_170']`).
  Backup written to `evolution/registry.json.bak.cycle_194-watch-20261021-002549`.
- This report.

## 验证

| # | Check | Result |
|---|---|---|
| 1 | `sha256sum` root vs mlops SKILL.md | **PASS** (both `b7269d91698dea66ed4d375b0823685ccd25d4eb2d4a107bd53d0fad33905bee`) — but tautological (F5) |
| 2 | `diff -r references/` root vs mlops | **PASS** (no output) — but tautological (F5) |
| 3 | `diff -r scripts/` root vs mlops | **PASS** (no output) — but tautological (F5) |
| 4 | `readlink -f` alias farm structural check | **PASS** (`ALIAS_FARM_OK`) — NEW real check (F5) |
| 5 | `cargo test` root crate (`apex_impl`) | **PASS** (95 passed / 0 failed) |
| 6 | `cargo test` `apex_devour/` | **PASS** (60 passed / 0 failed) |
| 7 | `cargo test` `evomaster_claw_core/` | **PASS** (3 passed / 0 failed) |
| 8 | `EVMCore.calculate_evm()` | **PASS** (EVM=0.7691, defect_total=0.0, defect_nonzero_count=0) |
| 9 | `scripts/indicator.py` | **PASS** (V_H=true, I_continue=false, evm 0.7691, orphan=[], bad_json=[]) |
| 10 | `scripts/apex_harness_cycle.py` | **PASS** (risk_score=0.24, decision=allow, V_H=true, I_continue=false) |
| 11 | `apex_devour gate` | **PASS** (5/5 sub-gates, ΔG_candidate=1.4040, gate_open=true) |
| 12 | `py/apex_spiral/gini_gene_selector.py` | **PASS** (n_candidates=21, selected `gene_594`, gini_gain=0.0, ig_gain=0.0) |
| 13 | `from apex_spiral import __version__` | **PASS** (0.3.0) |
| 14 | `git stash list` | **PASS** (0 entries — nothing popped) |
| 15 | `scripts/refresh_apex_dashboard.py` | **PASS** (dashboard refreshed, 2026-10-21T00:18:58) |
| 16 | registry JSON parse | **PASS** (89 cycles, head=cycle_194, head_cycle=cycle_194, last_cycle=cycle_194) |
| 17 | cron job `2ea5e66b83df` enabled + marker | **PASS** (enabled=true, `[CRON SYNC INVARIANT]` present) |
| 18 | Auto-classify re-check (post-edit) | `top_head=cycle_194 == latest_in_cycles_dict=cycle_194` → NO_GAP (no residual) |
| 19 | Skill mirror hashes after this tick's reference writes | **PASS** (root == mlops for SKILL.md, REFERENCE.md, cycle-194-walkthrough.md) |

## 输出证据

- Registry: `head=cycle_194`, `head_cycle=cycle_194`, `last_cycle=cycle_194`,
  `last_verified=2026-10-21T00:25:49+08:00`, total cycles=89, last entry
  `delta_g_self_repair=0.0`, `status=completed_cron_verification_watch`,
  `delta_g_housekeeping=0.301725`.
- `sync_check` (live-measured, not inherited): `references_count_root=117`,
  `references_count_mlops=117`, `scripts_count=5`, sha root == mlops ==
  `b7269d91698dea66ed4d375b0823685ccd25d4eb2d4a107bd53d0fad33905bee`,
  `alias_mode=symlink_farm`, `alias_farm_structural_check=ALIAS_FARM_OK`.
- `defect_repairs_this_cycle` records all six F1–F6 with was → now and root cause.
- SOUL.md §11 (post-roll): "Last verified: 2026-10-21T00:25:49+08:00 (cycle_194 tick) …";
  "Current registry head is `cycle_193` (cycle_194 registered this tick) … cycles 134→193 = 36
  drift-repair cycles — evidence-derived"; "Active skill aliases verified clean at
  2026-10-21T00:25+08:00 … (117 references, 5 scripts)".
- EVM: 0.7691, defect_total=0.0, G_evm=1.06, gate_open=true.
- cargo test: 158/158 (apex_impl 95/95 + apex_devour 60/60 + evomaster_claw_core 3/3).
- Devour gate: G_neuro=1.1142, G_self=1.0908, G_evm=1.0600, G_devour=1.0000,
  G_apex_ib=1.0300, ΔG_candidate=1.4040, gate_open=true.

## Self-repair scope (≤20 lines)

This is a **clean Variant A** tick (`delta_g_self_repair=0.0`): the top-level
`head`/`head_cycle`/`last_cycle` all equalled `cycle_193` and equalled the
max numeric key in `cycles` at the start of the tick, so there was no metadata gap
to close. Scope is therefore: (part 1) a standard forward roll to `cycle_194`
across the registry, the SOUL.md §11 prose and a new report; and (part 2) six
bounded, evidence-backed repairs to the housekeeping machinery itself (F1–F6),
each of which is a defect in the verification path rather than in the APEX
capability chain. No capability-gain credit is claimed for any of them: the
stored baseline `delta_g=1.404` and `live_gate_baseline` are unchanged, and no
new measurable gate was added.

## Unresolved / carry-watch

- **F6 needs a separately authorized scheduler migration.** The cron prompt for
  job `2ea5e66b83df` still prescribes the `cp`/`rsync` sync recipe that fails
  under the symlink farm. The corrected logic is in the recipe's pitfall #16; the
  prompt was not edited by this tick.
- **The alias gates remain structurally weak until the farm is re-grounded.**
  `alias_drift=0` is now recorded with `alias_mode=symlink_farm` and the
  structural check, but the sha/diff comparisons themselves still carry no
  information. The archived real copies under `~/.hermes/skills/.archive/` and
  `~/.hermes/curator-backups/` are the only independent comparison targets and
  are all stale (`db06a76b…`, `4aedb617…`, `32942f1a…` vs live `b7269d91…`).
- **Self-check history is stale.** `/tmp/apex_self_check_history.json` has not
  been appended to since 2026-10-14T00:02 (cycle_count=101, 100 entries), so the
  ΔG≈2.2713 Shannon plateau (plateau_score=1.0, eta_capacity=0.5541) is a
  carry-watch reading, not a fresh measurement.
- T/Vt probes and third-party installs remain carry-watch / environment-limited.
- Uncommitted repo state persists from earlier cycles (`genes.json`,
  `py/apex_spiral/__init__.py` modified; `apex_devour/` Rust sources and
  `APEX_*.md` docs untracked). Left untouched — committing is outside the scope
  of a housekeeping tick.
