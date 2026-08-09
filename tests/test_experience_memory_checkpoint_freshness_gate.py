"""Counterexample tests for monotonic signed-checkpoint freshness."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHAIN = _load(
    "experience_memory_hash_chain_gate_cycle166",
    ROOT / "maintenance" / "experience_memory" / "cycle166" / "hash_chain_gate.py",
)
FRESHNESS = _load(
    "experience_memory_checkpoint_freshness_gate_cycle168",
    ROOT / "maintenance" / "experience_memory" / "cycle168" / "freshness_gate.py",
)


def _chain(contents: tuple[str, ...]) -> dict:
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


def _checkpoint(report: dict, key: Ed25519PrivateKey, seq: int, prev_hash: str) -> dict:
    return FRESHNESS.create_checkpoint(
        chain_id="experience-memory/main",
        checkpoint_seq=seq,
        event_count=report["events_checked"],
        head_hash=report["head_hash"],
        issued_at=f"2026-08-03T03:0{seq}:00Z",
        prev_checkpoint_sha256=prev_hash,
        signer_id="external-evaluator-a",
        private_key=key,
    )


def _verify(report: dict, checkpoint: dict, key: Ed25519PrivateKey, watermark: dict) -> dict:
    return FRESHNESS.verify_fresh_checkpoint(
        chain_report=report,
        checkpoint=checkpoint,
        expected_chain_id="experience-memory/main",
        trusted_public_keys={"external-evaluator-a": key.public_key()},
        trusted_watermark=watermark,
    )


def _fixture():
    key = Ed25519PrivateKey.generate()
    report1 = _chain(("first",))
    checkpoint1 = _checkpoint(report1, key, 1, FRESHNESS.GENESIS_CHECKPOINT_HASH)
    watermark1 = {
        "checkpoint_seq": 1,
        "checkpoint_sha256": FRESHNESS.checkpoint_sha256(checkpoint1),
    }
    report2 = _chain(("first", "second"))
    checkpoint2 = _checkpoint(report2, key, 2, watermark1["checkpoint_sha256"])
    return key, report1, checkpoint1, watermark1, report2, checkpoint2


def test_next_monotonic_checkpoint_is_candidate_only() -> None:
    key, _, _, watermark1, report2, checkpoint2 = _fixture()
    result = _verify(report2, checkpoint2, key, watermark1)
    assert result["decision"] == "candidate_fresh_checkpoint"
    assert result["freshness_valid"] is True
    assert result["writes_trusted_watermark"] is False
    assert result["promotion_allowed"] is False
    assert result["proposed_next_watermark"]["checkpoint_seq"] == 2


def test_old_but_validly_signed_checkpoint_is_rejected() -> None:
    key, report1, checkpoint1, watermark1, _, _ = _fixture()
    result = _verify(report1, checkpoint1, key, watermark1)
    assert result["decision"] == "quarantine"
    assert "checkpoint_rollback_or_replay" in result["reasons"]


def test_same_sequence_replay_with_different_valid_content_is_rejected() -> None:
    key, _, _, watermark1, _, _ = _fixture()
    alternate = _chain(("different", "history"))
    replay = _checkpoint(alternate, key, 1, FRESHNESS.GENESIS_CHECKPOINT_HASH)
    result = _verify(alternate, replay, key, watermark1)
    assert "checkpoint_rollback_or_replay" in result["reasons"]
    assert "checkpoint_predecessor_mismatch" in result["reasons"]


def test_sequence_gap_is_rejected() -> None:
    key, _, _, watermark1, report2, _ = _fixture()
    skipped = _checkpoint(report2, key, 3, watermark1["checkpoint_sha256"])
    result = _verify(report2, skipped, key, watermark1)
    assert "checkpoint_sequence_gap" in result["reasons"]


def test_wrong_predecessor_hash_is_rejected_even_with_valid_signature() -> None:
    key, _, _, watermark1, report2, _ = _fixture()
    forked = _checkpoint(report2, key, 2, "f" * 64)
    result = _verify(report2, forked, key, watermark1)
    assert "checkpoint_predecessor_mismatch" in result["reasons"]


def test_sequence_tampering_breaks_signature() -> None:
    key, _, _, watermark1, report2, checkpoint2 = _fixture()
    attacked = copy.deepcopy(checkpoint2)
    attacked["checkpoint_seq"] = 3
    result = _verify(report2, attacked, key, watermark1)
    assert "checkpoint_sequence_gap" in result["reasons"]
    assert "invalid_signature" in result["reasons"]


def test_stale_or_invalid_watermark_fails_closed() -> None:
    key, _, _, _, report2, checkpoint2 = _fixture()
    result = _verify(
        report2,
        checkpoint2,
        key,
        {"checkpoint_seq": -1, "checkpoint_sha256": "bad"},
    )
    assert result["decision"] == "quarantine"
    assert "invalid_trusted_watermark_seq" in result["reasons"]
    assert "invalid_trusted_watermark_hash" in result["reasons"]
