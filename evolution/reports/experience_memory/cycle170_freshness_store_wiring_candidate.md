# Cycle 170: Freshness Gate consumes WatermarkStore (Candidate Wiring)

## Status
status: candidate_hold (cycle_170 landed, 7/7 wiring tests pass, 140/140 suite non-regression, NOT promoted)
one-line summary: additive wiring layer verify_fresh_checkpoint_v2 that delegates to cycle 168 verify_fresh_checkpoint with the same invariants but resolves the trusted watermark from a cycle 169 WatermarkStore view when supplied; resolves the seq vs checkpoint_seq naming gap; preserves inline-dict call sites unchanged; new observability fields expose backend_append_only.

## Pre-task truth statement
- executable: yes. New module maintenance/experience_memory/cycle170/freshness_gate_wiring.py (load-time wires cycle 168 + cycle 169 modules via importlib.util.spec_from_file_location with sys.modules pre-registration per the cycle 169 frozen-dataclass pitfall).
- resources: python3.12, pytest 9.0.3, stdlib (importlib/sys/pathlib), no new dependencies.
- constraints: cycle 168 freshness_gate.py is NOT modified (existing test suite still passes); cycle 169 watermark_store.py is NOT modified (existing 10 tests still pass); no writes to active memory, no writes to watermark, no promotion, no SOUL.md/registry/cron/SKILL.md/genes.json changes.
- hallucination risk: low. All 7 wiring tests run; full suite 140/140; inline-dict path proven bit-identical to legacy; store path proven to behave equivalently for the same logical watermark state.

## Formula substitution / plan
delta_G_candidate = delta_G_baseline * G_externalization * G_promotion_gate * G_non_regression
  G_externalization   = (cycle_168 freshness_gate.py consumes cycle_169 WatermarkStore via additive adapter) * (seq vs checkpoint_seq naming gap resolved) * (observability fields expose backend_append_only)
  G_promotion_gate    = (writes_trusted_watermark=False hard-coded) * (promotion_allowed=False hard-coded)
  G_non_regression    = (full suite 140/140 = baseline 133 + new 7)

Per APEX semantics, G_externalization > 1.0 because the watermark backend can now be swapped (InMemory vs FileAppendOnly vs future SQLite/remote) without rewriting cycle 168. G_promotion_gate ~ 1.0 (still locked candidate_hold). Aggregate delta_G_candidate ~ delta_G_baseline; cumulative delta_G is reserved for cycle_171+ which would wire a fully independent evaluator over this adapter.

## Problem finding (motivation)
- cycle 168 verify_fresh_checkpoint takes trusted_watermark as inline dict[str, Any]. The source of truth is fully under caller control: if the checkpoint file is rewritten together with the watermark dict, no interface-layer defense catches it.
- cycle 169 introduced the WatermarkStore abstract backend but explicitly deferred wiring: cycle 169 risk section flags "cycle_168 currently uses checkpoint_seq, view_to_trusted_watermark emits seq. Resolving this is cycle_170's work, not cycle_169's."
- The gap was both real (field-name mismatch) and structural (no contract for callers to say "this watermark really came from an append-only backend"). Without cycle 170, cycle 169's interface cannot reach production use.
- Two pre-existing tests pin cycle 168's behavior; cycle 170 must not break either.

## Optimization (5-step execution)
1. Snapshot backup: cp maintenance/experience_memory/cycle168/freshness_gate.py -> .bak.cycle170-<ts>. Verified via ls.
2. Write additive adapter maintenance/experience_memory/cycle170/freshness_gate_wiring.py containing verify_fresh_checkpoint_v2. No edits to cycle 168 or cycle 169 modules.
3. Resolve seq vs checkpoint_seq: adapter emits {checkpoint_seq, checkpoint_sha256} (the keys cycle 168 reads), while ALSO exposing entry_count, backend_name, backend_append_only for downstream observability. The original view's `seq` field is renamed to `checkpoint_seq` at the boundary.
4. Mutual-exclusion rule: watermark_source (when provided) wins over inline trusted_watermark; the override is recorded in result['reasons'] so callers can audit which input drove the verdict.
5. Add 7 counterexample tests in tests/test_experience_memory_freshness_store_wiring_gate.py covering: inline-dict byte-equivalence (no regression), in-memory store path, store-driven rollback + predecessor_mismatch, FileAppendOnly persistence across restart, FileAppendOnly truncation still trips, override observability, and read-only contract (v2 does not mutate store).

## Verification (command-level + end-to-end)

### Command-level (wiring tests only)
$ python3.12 -m pytest tests/test_experience_memory_freshness_store_wiring_gate.py -v
============================== 7 passed in 0.11s ==============================

Counterexample coverage (7 tests):
1. test_inline_dict_path_still_works_unmodified - v2 with inline dict is bit-identical to legacy verify_fresh_checkpoint for the same inputs (decision + reasons + proposed_next_watermark)
2. test_in_memory_store_path_matches_inline_dict_semantics - same logical watermark state via store vs inline dict produces identical decision + proposed_next_watermark; backend_name="in_memory_dict", backend_append_only=False exposed
3. test_store_path_rejects_rollback_with_same_reasons_as_legacy - store-backed stale watermark trips checkpoint_rollback_or_replay + checkpoint_predecessor_mismatch (the cycle 168 invariants propagate through the adapter)
4. test_file_append_only_store_persists_across_restart - FileAppendOnly backend survives process restart (separate FileAppendOnlyWatermarkStore instances reading same root_dir); v2 returns candidate_fresh_checkpoint with backend_append_only=True
5. test_file_append_only_store_truncation_still_quarantines_v2 - mid-stream file truncation raises PayloadMismatch before v2 even runs the freshness check; defense-in-depth preserved
6. test_store_source_overrides_inline_dict_and_is_observable - if both inputs are passed, store wins AND watermark_source_overrides_inline_dict is added to result['reasons']; the override is observable, not silent
7. test_store_path_does_not_mutate_store - v2 never writes: audit_trail length and chain_count unchanged after a v2 call; head entry identical

### End-to-end baseline non-regression
$ python3.12 -m pytest tests/ -q --ignore=tests/test_apex_v10.py
140 passed in 2.83s
baseline 133 + new 7 = 140, all pass. test_experience_memory_checkpoint_freshness_gate.py still 7/7 (no regression in cycle 168 path). test_experience_memory_watermark_store_gate.py still 10/10 (no regression in cycle 169 path).

### Module + file landing verification
$ ls maintenance/experience_memory/cycle170/
freshness_gate_wiring.py          (5603 bytes; py_compile OK)
$ ls tests/test_experience_memory_freshness_store_wiring_gate.py
~ 13420 bytes; py_compile OK; 7 tests collected
$ ls maintenance/experience_memory/cycle168/
freshness_gate.py                 (untouched)
freshness_gate.py.bak.cycle170-20260811-030150   (backup of pre-cycle_170 state)

## Incomplete / unverified / risk
- Not done: cycle_171+ fully independent evaluator over v2 (multi-evaluator quorum, evaluator-owned execution). Cycle 170 ships the adapter only.
- Not done: third WatermarkStore backend (e.g. SQLite or remote KV). Two backends are sufficient to prove the interface is swappable.
- Not done: cross-process concurrency stress test on FileAppendOnlyWatermarkStore (O_APPEND atomicity boundary proven in cycle 169; multi-process stress was not added by cycle 170).
- Risk: callers that destructure result['reasons'] and assert exact set equality (not just membership) will see one new possible reason `watermark_source_overrides_inline_dict` if they pass both inputs. No existing test does this; the change is additive.
- Risk: Field rename seq -> checkpoint_seq happens ONLY at the boundary inside the adapter; cycle 169 view_to_trusted_watermark still emits `seq`. Downstream code reading the cycle 169 view directly still gets `seq`. The two surfaces are intentionally separate.

## Mandatory boundary declarations
1. verify_fresh_checkpoint_v2 is additive. The cycle 168 verify_fresh_checkpoint signature is unchanged; all existing callers continue to work without modification.
2. verify_fresh_checkpoint_v2 is read-only against WatermarkStore. It calls get_watermark exactly once per invocation and never invokes put_watermark, audit_trail mutation, or any chain-writing operation.
3. promotion_allowed is still False. The adapter does not promote candidates, does not write the new watermark, and does not flip the cycle 168 promotion gate.
4. When watermark_source is provided, the inline trusted_watermark is ignored AND the override is recorded in result['reasons']. This makes the override observable rather than silent; downstream audits can grep for the reason string.
5. The adapter resolves the seq vs checkpoint_seq field-name mismatch ONLY at the internal boundary. cycle 169 view_to_trusted_watermark is unchanged; cycle 168 verify_fresh_checkpoint is unchanged.
6. cycle 170 does not modify SOUL.md, evolution/registry.json, evolution/genes/*.json, ~/.hermes/cron/jobs.json, ~/.hermes/skills/apex-spiral-v10/SKILL.md, or apex-devour Rust crates. All cycle artifacts live in maintenance/experience_memory/cycle170/ + tests/test_experience_memory_freshness_store_wiring_gate.py.

## Truth gate
- hallucination present: no
- evidence:
  - file landing verified: ls maintenance/experience_memory/cycle170/ + ls tests/test_experience_memory_freshness_store_wiring_gate.py + py_compile both pass.
  - test execution verified: 7/7 wiring tests pass; 140/140 full suite pass.
  - baseline non-regression verified: test_experience_memory_checkpoint_freshness_gate.py (7 tests) still 7/7; test_experience_memory_watermark_store_gate.py (10 tests) still 10/10.
  - backup verified: freshness_gate.py.bak.cycle170-20260811-030150 exists with same byte size as pre-cycle_170 file.
  - boundary declarations: promotion_allowed=False hard-coded and pinned by 6/7 wiring tests (all store-path tests assert it).