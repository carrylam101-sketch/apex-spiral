# Cycle 169: Trusted Watermark Externalization (Candidate)

## Status
status: candidate_hold (cycle_169 landed, tests passing, NOT promoted)
one-line summary: upgrade trusted_watermark from inline test dict into an independent abstract storage interface WatermarkStore, paired with two minimal implementations (InMemory + FileAppendOnly) and gated by 10 counterexample tests covering the interface boundary. Primes cycle_170 to wire freshness_gate.py against this interface.

## Pre-task truth statement
- executable: yes. New module at maintenance/experience_memory/cycle169/watermark_store.py, tests at tests/test_experience_memory_watermark_store_gate.py, runnable via python3.12 -m pytest.
- resources: python3.12, pytest 9.0.3, stdlib (json/os/hashlib/dataclasses).
- constraint: cycle_170 (NOT cycle_169) is the cycle that wires freshness_gate.py to consume WatermarkStore. This cycle ships interface + implementations only.
- hallucination risk: low. Interface and both implementations validated end-to-end; 10 counterexample tests cover 7+ invariants.

## Formula substitution / plan
Following the cycle_166/167/168 hardening path:

delta_G_candidate = delta_G_baseline * G_externalization * G_promotion_gate
  G_externalization = (backend is_append_only truth exposure) * (watermark decoupled from checkpoint)
  G_promotion_gate  = (verify_promotion_allowed() always returns candidate_hold)

Per APEX semantics, G_externalization > 1.0 (external abstraction enables backend swap), but cycle-internal promotion_allowed=False locks promotion so G_promotion_gate ~ 1.0. Aggregate delta_G_candidate ~ delta_G_baseline; cumulative delta_G is reserved for cycle_170 after wiring.

## Problem finding (motivation)
- cycle_168 freshness_gate.py currently takes trusted_watermark as dict[str, Any]. Source of truth is fully under caller control; if the checkpoint itself is rewritten, the paired watermark can be silently swapped with no interface-layer defense.
- Existing tests construct trusted_watermark as an inline dict - no append-only truth exposure, no way to prove "this watermark really came from an unrewritable storage."
- Missing: watermark source-selection policy, single-backend risk, cross-process/restart recovery paths.

## Optimization (5-step execution)
1. Define WatermarkEntry and WatermarkView as frozen dataclasses for immutability and hashability.
2. Define WatermarkStore ABC: is_append_only / get_watermark / put_watermark / audit_trail / chain_count / close.
3. Two minimal implementations:
   - InMemoryWatermarkStore (is_append_only=False, for tests/replay)
   - FileAppendOnlyWatermarkStore (is_append_only=True, O_APPEND + fsync, one log file per chain)
4. Adapter view_to_trusted_watermark() emits {seq, checkpoint_sha256, entry_count, backend_name, backend_append_only}.
5. Governance gate verify_promotion_allowed() always returns candidate_hold.

## Verification (command-level + end-to-end)

### Command-level
$ python3.12 -m pytest tests/test_experience_memory_watermark_store_gate.py -v
============================== 10 passed in 0.07s ==============================

Counterexample coverage (10 tests, requirement >=7):
1. test_in_memory_store_basic_monotonic - InMemory write/read basic path
2. test_file_append_only_store_persists_and_reconciles - FileAppendOnly truth persistence + reconciliation
3. test_chain_isolation_between_stores - chain isolation; unknown chain returns GENESIS view + empty audit
4. test_sequence_not_monotonic_rejected - seq skip must raise SequenceNotMonotonic
5. test_prev_checkpoint_sha256_mismatch_rejected - prev mismatch must raise PayloadMismatch
6. test_view_to_trusted_watermark_shape_matches_cycle168 - adapter output has all 5 fields
7. test_audit_trail_past_entries_immutable_via_canonical_bytes - frozen dataclass rejects mutation; canonical bytes stable across later writes
8. test_file_append_only_store_rejects_mid_stream_truncation - file truncation must raise PayloadMismatch
9. test_promotion_allowed_always_false_in_cycle169 - promotion gate hard-locked
10. test_in_memory_and_file_stores_round_trip_consistently - two backends produce same view from same input (except backend_name)

### End-to-end baseline non-regression
$ python3.12 -m pytest tests/ -q --ignore=tests/test_apex_v10.py
133 passed in 2.64s
baseline 123 + new 10 = 133, all pass.

### Mandatory boundary declarations
1. WatermarkStore is a candidate interface. cycle_170 is when freshness_gate.py switches to this interface. This cycle does NOT modify freshness_gate.py.
2. verify_promotion_allowed() always returns promotion_allowed=False. Any caller that promotes based on its result violates the governance contract.
3. FileAppendOnlyWatermarkStore defends against an attacker holding the non-root uid. It does NOT defend against a root-level holder. Production deployment requires a second backend cross-check or external audit process.
4. InMemoryWatermarkStore self-reports is_append_only=False. No artifact that depends solely on this backend may be promoted.
5. canonical_entry() output is byte-stable (sorted keys, separators=(",", ":"), ASCII), but is NOT signed. Signing remains the responsibility of the cycle_167 signed_checkpoint chain.
6. audit_trail returns tuple[WatermarkEntry, ...] (immutable snapshot), length bounded by limit (default 100).

## Incomplete / unverified / risk
- Not done: cycle_170 wiring (modifying maintenance/experience_memory/cycle168/freshness_gate.py so verify_fresh_checkpoint accepts a WatermarkStore parameter) - belongs to the next cycle.
- Not done: cross-process concurrency stress test for FileAppendOnlyWatermarkStore (O_APPEND provides an atomicity boundary on Linux but needs concurrent test coverage).
- Not done: third backend (e.g. SQLite or remote KV) - reserved as a future candidate; current two implementations suffice for tests.
- Risk: cycle_170 wiring may need to adjust the trusted_watermark shape (e.g. cycle_168 currently uses checkpoint_seq, view_to_trusted_watermark emits seq). Resolving this is cycle_170's work, not cycle_169's.

## Truth gate
- hallucination present: no
- evidence:
  - file landing verified: ls maintenance/experience_memory/cycle169/watermark_store.py (338 lines) + ls tests/test_experience_memory_watermark_store_gate.py (170 lines).
  - test execution verified: 10/10 pass command output captured.
  - baseline non-regression verified: 133/133 pass command output captured.
  - boundary declarations: promotion_allowed=False is hard-coded in verify_promotion_allowed() and covered by counterexample test.
