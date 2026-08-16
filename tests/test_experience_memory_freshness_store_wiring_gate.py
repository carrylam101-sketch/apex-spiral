"""Counterexample tests for cycle 170 freshness-gate wiring.

Wires cycle 168 freshness_gate.py with cycle 169 WatermarkStore via an additive
adapter verify_fresh_checkpoint_v2. Both backends (InMemory + FileAppendOnly)
are exercised; the cycle 168 inline-dict path is regression-tested.
"""
from __future__ import annotations

import copy
import importlib.util
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CHAIN = _load(
    "experience_memory_hash_chain_gate_cycle166",
    ROOT / "maintenance" / "experience_memory" / "cycle166" / "hash_chain_gate.py",
)
FRESHNESS = _load(
    "experience_memory_freshness_gate_cycle168",
    ROOT / "maintenance" / "experience_memory" / "cycle168" / "freshness_gate.py",
)
WATERMARK_STORE = _load(
    "experience_memory_watermark_store_cycle169",
    ROOT / "maintenance" / "experience_memory" / "cycle169" / "watermark_store.py",
)
WIRING = _load(
    "experience_memory_freshness_gate_wiring_cycle170",
    ROOT / "maintenance" / "experience_memory" / "cycle170" / "freshness_gate_wiring.py",
)


def _chain(contents):
    events = []
    prev_hash = CHAIN.GENESIS_HASH
    for sequence, content in enumerate(contents, start=1):
        event = CHAIN.seal_event(
            {
                "sequence": sequence,
                "event_id": f"evt-{sequence}",
                "session_id": f"session-{sequence}",
                "memory_key": "python.empty_input.policy",
                "content": content,
                "task_scope": "python-parser",
                "source_ref": f"test-run:evt-{sequence}",
                "verification_status": "verified",
                "evidence_types": ["task_result", "independent_eval", "held_out"],
            },
            prev_hash,
        )
        events.append(event)
        prev_hash = event["event_hash"]
    return CHAIN.verify_chain(events)


def _checkpoint(report, key, seq, prev_hash):
    return FRESHNESS.create_checkpoint(
        chain_id="experience-memory/main",
        checkpoint_seq=seq,
        event_count=report["events_checked"],
        head_hash=report["head_hash"],
        issued_at=f"2026-08-11T03:0{seq}:00Z",
        prev_checkpoint_sha256=prev_hash,
        signer_id="external-evaluator-a",
        private_key=key,
    )


def _two_checkpoints():
    key = __import__("cryptography").hazmat.primitives.asymmetric.ed25519.Ed25519PrivateKey.generate()
    report1 = _chain(("first",))
    checkpoint1 = _checkpoint(report1, key, 1, FRESHNESS.GENESIS_CHECKPOINT_HASH)
    watermark1_dict = {
        "checkpoint_seq": 1,
        "checkpoint_sha256": FRESHNESS.checkpoint_sha256(checkpoint1),
    }
    report2 = _chain(("first", "second"))
    checkpoint2 = _checkpoint(report2, key, 2, watermark1_dict["checkpoint_sha256"])
    return key, report1, checkpoint1, watermark1_dict, report2, checkpoint2


def test_inline_dict_path_still_works_unmodified() -> None:
    """Backward-compat: cycle 168 inline-dict watermark keeps working via v2."""
    key, _, _, watermark1, report2, checkpoint2 = _two_checkpoints()
    legacy = FRESHNESS.verify_fresh_checkpoint(
        chain_report=report2,
        checkpoint=checkpoint2,
        expected_chain_id="experience-memory/main",
        trusted_public_keys={"external-evaluator-a": key.public_key()},
        trusted_watermark=watermark1,
    )
    wired = WIRING.verify_fresh_checkpoint_v2(
        chain_report=report2,
        checkpoint=checkpoint2,
        expected_chain_id="experience-memory/main",
        trusted_public_keys={"external-evaluator-a": key.public_key()},
        trusted_watermark=watermark1,
    )
    assert wired["decision"] == legacy["decision"] == "candidate_fresh_checkpoint"
    assert wired["proposed_next_watermark"] == legacy["proposed_next_watermark"]
    assert wired["reasons"] == legacy["reasons"]
    assert wired["promotion_allowed"] is False
    assert wired["writes_trusted_watermark"] is False
    assert wired["watermark_source_provided"] is False


def test_in_memory_store_path_matches_inline_dict_semantics() -> None:
    """Same logical state, two paths -> same decision + proposed watermark."""
    key, report1, checkpoint1, _, report2, checkpoint2 = _two_checkpoints()
    store = WATERMARK_STORE.InMemoryWatermarkStore()
    store.put_watermark(
        chain_id="experience-memory/main",
        seq=1,
        checkpoint_sha256=FRESHNESS.checkpoint_sha256(checkpoint1),
        prev_checkpoint_sha256=FRESHNESS.GENESIS_CHECKPOINT_HASH,
        written_at="2026-08-11T03:01:00Z",
    )
    inline_watermark = {
        "checkpoint_seq": 1,
        "checkpoint_sha256": FRESHNESS.checkpoint_sha256(checkpoint1),
    }
    store_path = WIRING.verify_fresh_checkpoint_v2(
        chain_report=report2,
        checkpoint=checkpoint2,
        expected_chain_id="experience-memory/main",
        trusted_public_keys={"external-evaluator-a": key.public_key()},
        watermark_source=store,
        source_chain_id="experience-memory/main",
    )
    inline_path = WIRING.verify_fresh_checkpoint_v2(
        chain_report=report2,
        checkpoint=checkpoint2,
        expected_chain_id="experience-memory/main",
        trusted_public_keys={"external-evaluator-a": key.public_key()},
        trusted_watermark=inline_watermark,
    )
    assert store_path["decision"] == inline_path["decision"] == "candidate_fresh_checkpoint"
    assert store_path["proposed_next_watermark"]["checkpoint_seq"] == 2
    assert store_path["proposed_next_watermark"]["checkpoint_sha256"] == FRESHNESS.checkpoint_sha256(checkpoint2)
    assert store_path["reasons"] == inline_path["reasons"]
    assert store_path["watermark_source_provided"] is True
    assert store_path["watermark_backend_name"] == "in_memory_dict"
    assert store_path["watermark_backend_append_only"] is False
    assert store_path["watermark_entry_count"] == 1


def test_store_path_rejects_rollback_with_same_reasons_as_legacy() -> None:
    """A store watermark far ahead of the candidate must trip rollback + predecessor_mismatch."""
    key, report1, checkpoint1, _, _, _ = _two_checkpoints()
    store = WATERMARK_STORE.InMemoryWatermarkStore()
    store.put_watermark(
        chain_id="experience-memory/main",
        seq=1,
        checkpoint_sha256="f" * 64,
        prev_checkpoint_sha256="0" * 64,
        written_at="2026-08-11T03:01:00Z",
    )
    result = WIRING.verify_fresh_checkpoint_v2(
        chain_report=report1,
        checkpoint=checkpoint1,
        expected_chain_id="experience-memory/main",
        trusted_public_keys={"external-evaluator-a": key.public_key()},
        watermark_source=store,
        source_chain_id="experience-memory/main",
    )
    assert result["decision"] == "quarantine"
    assert "checkpoint_rollback_or_replay" in result["reasons"]
    assert "checkpoint_predecessor_mismatch" in result["reasons"]
    assert result["promotion_allowed"] is False


def test_file_append_only_store_persists_across_restart() -> None:
    """FileAppendOnlyWatermarkStore survives process restart and gates v2 correctly."""
    key, report1, checkpoint1, _, report2, checkpoint2 = _two_checkpoints()
    with tempfile.TemporaryDirectory() as td:
        s1 = WATERMARK_STORE.FileAppendOnlyWatermarkStore(root_dir=td)
        s1.put_watermark(
            chain_id="experience-memory/main",
            seq=1,
            checkpoint_sha256=FRESHNESS.checkpoint_sha256(checkpoint1),
            prev_checkpoint_sha256=FRESHNESS.GENESIS_CHECKPOINT_HASH,
            written_at="2026-08-11T03:01:00Z",
        )
        s1.close()
        s2 = WATERMARK_STORE.FileAppendOnlyWatermarkStore(root_dir=td)
        assert s2.is_append_only() is True
        assert s2.get_watermark(chain_id="experience-memory/main").seq == 1
        result = WIRING.verify_fresh_checkpoint_v2(
            chain_report=report2,
            checkpoint=checkpoint2,
            expected_chain_id="experience-memory/main",
            trusted_public_keys={"external-evaluator-a": key.public_key()},
            watermark_source=s2,
            source_chain_id="experience-memory/main",
        )
        assert result["decision"] == "candidate_fresh_checkpoint"
        assert result["watermark_backend_append_only"] is True
        assert result["watermark_backend_name"] == "file_append_only"
        assert result["watermark_entry_count"] == 1
        s2.close()


def test_file_append_only_store_truncation_still_quarantines_v2() -> None:
    """Truncating the watermark file mid-stream must NOT silently pass v2."""
    key, report1, checkpoint1, _, report2, checkpoint2 = _two_checkpoints()
    with tempfile.TemporaryDirectory() as td:
        s1 = WATERMARK_STORE.FileAppendOnlyWatermarkStore(root_dir=td)
        s1.put_watermark(
            chain_id="experience-memory/main",
            seq=1,
            checkpoint_sha256=FRESHNESS.checkpoint_sha256(checkpoint1),
            prev_checkpoint_sha256=FRESHNESS.GENESIS_CHECKPOINT_HASH,
            written_at="2026-08-11T03:01:00Z",
        )
        s1.close()
        files = list(Path(td).glob("experience-memory_main.log"))
        assert len(files) == 1
        p = files[0]
        good = p.read_bytes()
        p.write_bytes(good[: len(good) // 2])
        s2 = WATERMARK_STORE.FileAppendOnlyWatermarkStore(root_dir=td)
        try:
            WIRING.verify_fresh_checkpoint_v2(
                chain_report=report2,
                checkpoint=checkpoint2,
                expected_chain_id="experience-memory/main",
                trusted_public_keys={"external-evaluator-a": key.public_key()},
                watermark_source=s2,
                source_chain_id="experience-memory/main",
            )
            raised_payload = False
        except WATERMARK_STORE.PayloadMismatch:
            raised_payload = True
        assert raised_payload, "truncated file was accepted silently by v2"
        s2.close()


def test_store_source_overrides_inline_dict_and_is_observable() -> None:
    """If both inputs are given, store wins AND the override is logged."""
    key, _, checkpoint1, _, report2, checkpoint2 = _two_checkpoints()
    store = WATERMARK_STORE.InMemoryWatermarkStore()
    store.put_watermark(
        chain_id="experience-memory/main",
        seq=1,
        checkpoint_sha256=FRESHNESS.checkpoint_sha256(checkpoint1),
        prev_checkpoint_sha256=FRESHNESS.GENESIS_CHECKPOINT_HASH,
        written_at="2026-08-11T03:01:00Z",
    )
    poisoned_inline = {"checkpoint_seq": 99, "checkpoint_sha256": "a" * 64}
    result = WIRING.verify_fresh_checkpoint_v2(
        chain_report=report2,
        checkpoint=checkpoint2,
        expected_chain_id="experience-memory/main",
        trusted_public_keys={"external-evaluator-a": key.public_key()},
        trusted_watermark=poisoned_inline,
        watermark_source=store,
        source_chain_id="experience-memory/main",
    )
    assert "watermark_source_overrides_inline_dict" in result["reasons"]
    assert result["watermark_source_provided"] is True
    assert result["decision"] == "candidate_fresh_checkpoint"


def test_store_path_does_not_mutate_store() -> None:
    """v2 is read-only against the WatermarkStore; no chain_count or audit_trail change."""
    key, _, checkpoint1, _, _, _ = _two_checkpoints()
    store = WATERMARK_STORE.InMemoryWatermarkStore()
    store.put_watermark(
        chain_id="experience-memory/main",
        seq=1,
        checkpoint_sha256=FRESHNESS.checkpoint_sha256(checkpoint1),
        prev_checkpoint_sha256=FRESHNESS.GENESIS_CHECKPOINT_HASH,
        written_at="2026-08-11T03:01:00Z",
    )
    audit_before = store.audit_trail(chain_id="experience-memory/main")
    count_before = store.chain_count()
    WIRING.verify_fresh_checkpoint_v2(
        chain_report={"chain_valid": True, "events_checked": 1, "head_hash": "x"},
        checkpoint=checkpoint1,
        expected_chain_id="experience-memory/main",
        trusted_public_keys={"external-evaluator-a": key.public_key()},
        watermark_source=store,
        source_chain_id="experience-memory/main",
    )
    audit_after = store.audit_trail(chain_id="experience-memory/main")
    count_after = store.chain_count()
    assert len(audit_after) == len(audit_before) == 1
    assert audit_after[0] == audit_before[0]
    assert count_after == count_before == 1
    assert store.get_watermark(chain_id="experience-memory/main").seq == 1