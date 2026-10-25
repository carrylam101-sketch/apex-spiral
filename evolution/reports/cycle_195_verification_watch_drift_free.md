# cycle_195 — APEX V10.3 verification/watch drift-free

**Timestamp:** 2026-10-22T00:18:10+08:00
**Mode:** watch (no new measurable gate) + bounded reference/prose/machinery repairs
**Variant:** A — auto-classify at start: `top_head == latest_in_cycles_dict` → NO_GAP
**alias_drift:** 0 (see F5 — the gate is tautological under the symlink farm)
**Gates:** 9/9 canonical steps pass + 158/158 cargo tests
**Cron job:** `2ea5e66b83df` active, `[CRON SYNC INVARIANT]` marker present

## 代入公式

Scope is larger than a pure forward roll (3 bounded machinery repairs + 1 registry
registration + 4 SOUL line rolls + report + walkthrough + recipe pitfall updates), so
Λ/Θ/Φ are adjusted up from the standard tick. Computed with exact rational
arithmetic (`fractions.Fraction`):

| Factor | Value | Note |
|---|---|---|
| G_base | 0.50 | standard for issue scoring |
| Λ (goal strength) | 0.85 | 3 defects repaired, not just a clock bump |
| Θ (strategy complexity) | 0.76 | 3 distinct defect classes (counting / gate-logic / metadata-drift) |
| K (knowledge preserved) | 0.94 | measured baseline values kept verbatim |
| ξ (fidelity) | 0.97 | JSON parse + sha + readlink + 158/158 cargo verified |
| Ψ (cross-domain) | 1.00 | no cross-domain change |
| Φ (entropy reduced) | 1.04 | 3 defects removed from the standing procedure |
| H (health drag) | 1.02 | routine wear |
| T (time decay) | 1.00 | 1-day forward roll |
| ε (noise) | 1.03 | stable |

```text
ΔG = 0.50 × (0.85·0.76·0.94·0.97·1.00·1.04) / (1.02·1.00·1.03)
   = 0.50 × 0.306291856 / 1.0506
   = 0.291539935
```

Computed with `fractions.Fraction`: numerator = 19143241/62500000 exactly,
denominator = 5253/5000 exactly, ΔG = 1126073/3862500 exactly.

Housekeeping tick ΔG ≈ **0.291540** (above the 0.224 "safe" band, below the 0.493
"gamble" band). For reference the plain standard-tick value is 0.278851. Stored
baseline `delta_g` remains `1.404` (gate_open=true, no breakthrough).

## 找问题 (findings, with the exact evidence)

**F7 — the scripts/ tree was never re-counted per tick.**

cycle_194 repaired F1 (the `references/` count was stale at 116 for two ticks) but
established the count only for the `references/` tree. The `scripts/` tree kept
the value it had at the time the house convention was written:

```text
registry cycles[*].sync_check.scripts_count = 5   (cycle_190, 191, 192, 193, 194)
SOUL.md §11 prose                              = 5 scripts
live detector count                            = 6
```

The 6th file is `apex_housekeeping_preflight.py`, mtime **2026-10-21T00:32:42** —
i.e. it was created 7 minutes *after* the cycle_194 tick measured 5 at 00:25:49.
The count was therefore correct when cycle_194 measured it and stale from the
next tick onward, and it stayed stale through cycle_194's own report and prose
because nothing re-counted it. The preflight script had the same blind spot: it
computed `reference_counts` but had **no** `script_counts` probe at all, so even
running the preflight could not have caught it.

**F8 — the preflight SOUL staleness check could never converge.**

`apex_housekeeping_preflight.py` compared the bare label

```text
Current registry head is `cycle_193` (cycle_194 registered this tick)
           ^^^^^^^^^^^ prose_head                    ^^^^^^ registered this tick
```

against the registry head. But the house convention — visible in the cycle_191
and cycle_193 walkthroughs — is that the **bare label names the previous cycle**
(head-1) and the **parenthetical names the cycle actually registered**. Under
that convention `prose_head == registry_head` is *never* true after a correct
roll. The check therefore fired on every single tick, including ticks whose
prose was already correct, and could never report "not stale". A gate that can
never pass is as useless as one that can never fail.

Concretely: at the start of cycle_195 the prose was **already correct**
(`cycle_193` / `cycle_194 registered this tick` with registry head `cycle_194`),
and the preflight still reported `stale: true` and emitted a warning telling the
agent to roll prose that did not need rolling. Worse, a literal reading of the
warning ("prose head is cycle_193 but registry head is cycle_194 -> roll the prose")
would have pushed the prose to `cycle_195`/`cycle_196`, breaking the convention
and creating a *real* off-by-one that the corrected check would then flag.

**F9 — registry `gene_pool_stats` is frozen and diverges from live artifacts.**

```text
gene_pool_stats.total_genes  = 19   vs  len(gene_pool) = 21
gene_pool_stats.total_cycles = 75   vs  len(cycles)    = 89
gene_pool_stats.last_updated = 2026-10-10T00:02:56+08:00
```

The block has been frozen since 2026-10-10 (the cycle_181 backup carries the
identical values with an even older `last_updated` of 2026-06-02, so it has not
been meaningfully maintained for months). Git history shows the same staleness:
`total_genes` tracked the pool size only through the early commits (12→17→18)
and then stopped.

This was **deliberately not auto-mutated.** `references/cycle-96-registry-
consistency-lessons.md` lesson 3 documents that this field is a legacy
accumulator whose `total_genes` was *already* untrustworthy at cycle_96 (it read
21 while the real addressable gene count was 18), and the block's own `note`
claims it "reflects registry gene IDs" while `total_cycles` counts something
else entirely. The two counters have different semantics, no writer is known to
maintain them, and the field is not consumed by any live gate. Blindly setting
`total_genes=21, total_cycles=89` would publish numbers whose meaning is
unestablished. A divergence probe was added instead, so the gap is surfaced on
every tick until a separately-authorized tick can establish the correct semantics.

## 找问题 — additional finding

**F10 — the umbrella `SKILL.md` advertised a stale walkthrough range.**

`SKILL.md` L261 pointed at the module's nested worked examples as
`references/cycle-188-walkthrough.md` through `cycle-191-walkthrough.md`. The
umbrella file was last rolled at cycle_191, and cycles 192, 193, 194 and 195
each appended a walkthrough to that directory — so the advertised range was
stale by four entries and would have sent a reader to a truncated set (the
`cycle_192`–`cycle_195` examples, including the one describing the six
cycle_194 repairs, were not reachable from the entrypoint). The range was rolled
to `188`–`195` and both ends were made fully-qualified module-relative paths
(`references/cycle-188-walkthrough.md` through
`references/cycle-195-walkthrough.md`); all 8 files were verified present.

**Side effect:** editing `SKILL.md` changed its sha256 from `b7269d91…` to
`8f9eb24e…`. Per pitfall #12 the new value was **re-measured live** and written
into this cycle's `sync_check` and the SOUL.md §11 prose — it was not carried
over from cycle_194.

## 优化 (what was changed)

1. `~/.hermes/skills/apex-spiral-v10/scripts/apex_housekeeping_preflight.py`:
   - **F7** — new `count_script_files()` probe applying the same detector
     convention (`find -L <dir> -maxdepth 1 -type f | wc -l`) to the `scripts/`
     tree; wired into the report as `checks.script_counts`, with a blocking
     failure if the tree is empty/missing.
   - **F7** — new warning: SOUL.md prose scripts count vs live detector count.
   - **F7** — new warning: registry `sync_check.scripts_count` vs live detector
     count (this is the check that would have caught the staleness).
   - **F8** — `soul_prose_state()` now parses the
     `(cycle_N registered this tick)` parenthetical and compares *that* against
     the registry head; it falls back to the old comparison only when the
     parenthetical is absent. The docstring records the two-part convention and
     why the old comparison could never converge.
   - **F9** — new `gene_pool_stats_divergence()` probe reporting
     `total_genes` vs `len(gene_pool)` and `total_cycles` vs `len(cycles)`,
     plus a warning. Reports only; does not mutate.
   - Backup of the pre-patch script kept at
     `~/.hermes/skills/apex-spiral-v10/apex_housekeeping_preflight.py.bak.cycle195`
     (placed at the skill root, **not** inside `scripts/`, so it does not perturb
     the very count it measures).
2. `references/modules/apex-cron-watch-mode-housekeeping/REFERENCE.md`:
   - Pitfalls #17 (new), #18 (new), #19 (new) added; pitfall #3 extended to
     cover the scripts/ tree; the SOUL roll template's scripts row now says to
     re-count the scripts tree the same way as references.
3. `references/modules/apex-cron-watch-mode-housekeeping/references/cycle-195-walkthrough.md`
   added (this tick's worked example).
4. `~/.hermes/SOUL.md` §11: 4 lines rolled (L261, L264, L266, L270) with the
   corrected F7 scripts count (5→6) and the F7/F9 caveats; the gene-pool line
   (L268) left untouched per cycle_193 Lesson D (no new gene registered).
5. `~/.hermes/skills/apex-spiral-v10/SKILL.md`: L261 walkthrough range rolled from
   `cycle-188`…`cycle-191` to `cycle-188`…`cycle-195` (F10) — the umbrella
   entrypoint was last rolled at cycle_191 and was advertising a truncated set
   of worked examples. This changed the live SKILL.md sha256 from `b7269d91…` to
   `8f9eb24e…`; the new value was re-measured live and written into this
   cycle's `sync_check` and the SOUL.md §11 prose (pitfall #12).
6. `evolution/registry.json`: `cycles['cycle_195']` appended; top-level
   `head`/`head_cycle`/`last_cycle`/`last_updated`/`last_verified`/`updated_at`
   rolled to `cycle_195`. `drift_repair_cycles` left untouched (list, pitfall #11).
   `gene_pool_stats` left untouched (F9 — semantics unestablished).
7. `evolution/reports/cycle_195_verification_watch_drift_free.md` written (this file).

## 验证 (verification, all re-run this tick)

| # | Check | Result |
|---|---|---|
| 1 | `sha256sum` root vs mlops SKILL.md | **PASS** (both `8f9eb24e…`) — but tautological (F5) |
| 2 | `diff -q` root vs mlops `references/` | **PASS** (no output) — but tautological (F5) |
| 3 | `readlink -f` alias farm structural check | **PASS** (`ALIAS_FARM_OK`) — the real check |
| 4 | live sha vs registry `sync_check` last-known-good | **PASS** (`8f9eb24e…` == `8f9eb24e…`; changed from `b7269d91…` by the F10 SKILL.md edit, re-measured live) |
| 5 | `cargo test` root crate (`apex_impl`) | **PASS** (95/95) |
| 6 | `cargo test` `apex_devour/` | **PASS** (60/60) |
| 7 | `cargo test` `evomaster_claw_core/` | **PASS** (3/3) — 158/158 total |
| 8 | `EVMCore.calculate_evm()` | **PASS** (EVM=0.7691, defect_total=0.0, nonzero=0) |
| 9 | `scripts/indicator.py` | **PASS** (V_H=true, I_continue=false, evm 0.7691, orphan=[]) |
| 10 | `scripts/apex_harness_cycle.py` | **PASS** (cycle_count=90, head_cycle=cycle_195) |
| 11 | `apex_devour gate` | **PASS** (5/5 sub-gates, ΔG_candidate=1.4040, gate_open=true) |
| 12 | `py/apex_spiral/gini_gene_selector.py` | **PASS** (n_candidates=21, selected gene_594, gini_gain=0.0) |
| 13 | `PYTHONPATH=py python3 -c "from apex_spiral import __version__"` | **PASS** (0.3.0) |
| 14 | `git stash list` | **PASS** (0 entries — nothing popped) |
| 15 | registry JSON parse | **PASS** (90 cycles, head=cycle_195) |
| 16 | cron job `2ea5e66b83df` enabled + `[CRON SYNC INVARIANT]` marker | **PASS** (enabled=true, marker present) |
| 17 | preflight after this tick's script patches | **PASS** (verdict=PASS, 0 failures) |
| 18 | preflight F8 convergence | **PASS** (post-roll `stale=false`; pre-roll prose was already correct and is now correctly reported as not stale) |
| 19 | Auto-classify re-check (post-edit) | `top_head=cycle_195 == latest_in_cycles_dict=cycle_195` → NO_GAP |
| 20 | reference-file link check (SKILL.md + REFERENCE.md) | **PASS** (0 broken relative refs) |

## Self-repair scope

Standard watch-mode housekeeping tick (Variant A) on top of cycle_194, PLUS 3
bounded repairs to the housekeeping machinery itself, each evidence-backed and
reversible: **F7** (scripts/ count never re-measured → stale 5 while live is 6;
now re-counted live and given a dedicated preflight probe plus two new
comparisons), **F8** (preflight SOUL staleness check compared the wrong half of
the two-part head convention, so it fired on every tick and could never
converge; now parses the `(cycle_N registered this tick)` parenthetical), **F9**
(registry `gene_pool_stats` frozen at 2026-10-10 and diverging from live
artifacts — reported via a new divergence probe, deliberately **not**
auto-mutated because its semantics are documented as ambiguous and no writer is
known to maintain it).

No metadata gap was found: `head`, `head_cycle` and `last_cycle` all read
`cycle_194` and matched the newest `cycles` key at the start of the tick.

## What this tick did NOT do (and why)

- No new measurable gate. The Shannon plateau (self-check ΔG estimate 2.2713,
  `plateau_score=1.0`, `eta_capacity=0.5541`) is unchanged — the self-check
  history has not been appended to since 2026-10-14T00:02, so this is a
  carry-watch item, not a new claim.
- No cron job edits. The prompt's `cp`/`rsync` recipe remains unrunnable under
  the symlink farm (F6 from cycle_194) — reported for a separately authorized
  scheduler migration (pitfall #7).
- No `drift_repair_cycles` mutation (still `['cycle_170']`).
- No `gene_pool_stats` mutation (F9 — semantics unestablished; reported only).
- No pop stashes (0 entries present). No rewrite of `~/.hermes/cron/jobs.json`.
- The umbrella `SKILL.md` was edited only for F10 (one line, L261 — the stale
  walkthrough range). No other umbrella content changed, and the resulting live
  sha (`8f9eb24e…`) was re-measured rather than assumed.
- No SOUL.md line-roll for the gene-pool line (L268, "cycle_190 incremented") —
  no new gene was registered, so it stays (cycle_193 Lesson D).
- No edit to the historical cycle_191/192/193/194 reports.
