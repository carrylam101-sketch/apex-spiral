"""Counterexample tests for the candidate external signed checkpoint."""
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
CHECKPOINT = _load(
    "experience_memory_signed_checkpoint_gate_cycle167",
    ROOT
    / "maintenance"
    / "experience_memory"
    / "cycle167"
    / "signed_checkpoint_gate.py",
)


def _event(sequence: int, event_id: str, content: str) -> dict:
    return {
        "sequence": sequence,
        "event_id": event_id,
        "session_id": f"session-{sequence}",
        "memory_key": "python.empty_input.policy",
        "content": content,
        "task_scope": "python-parser",
        "source_ref": f"test-run:{event_id}",
        "verification_status": "verified",
        "evidence_types": ["task_result", "independent_eval", "held_out"],
    }


def _chain(contents: tuple[str, ...]) -> list[dict]:
    events: list[dict] = []
    prev_hash = CHAIN.GENESIS_HASH
    for sequence, content in enumerate(contents, start=1):
        event = CHAIN.seal_event(
            _event(sequence, f"evt-{sequence}", content),
            prev_hash,
        )
        events.append(event)
        prev_hash = event["event_hash"]
    return events


def _fixture() -> tuple[dict, dict, Ed25519PrivateKey]:
    private_key = Ed25519PrivateKey.generate()
    report = CHAIN.verify_chain(_chain(("first", "second", "third")))
    checkpoint = CHECKPOINT.create_checkpoint(
        chain_id="experience-memory/main",
        event_count=report["events_checked"],
        head_hash=report["head_hash"],
        issued_at="2026-08-02T03:00:00Z",
        signer_id="external-evaluator-a",
        private_key=private_key,
    )
    return report, checkpoint, private_key


def _verify(report: dict, checkpoint: dict, private_key: Ed25519PrivateKey) -> dict:
    return CHECKPOINT.verify_signed_checkpoint(
        chain_report=report,
        checkpoint=checkpoint,
        expected_chain_id="experience-memory/main",
        trusted_public_keys={"external-evaluator-a": private_key.public_key()},
    )


def test_valid_external_checkpoint_is_candidate_only() -> None:
    report, checkpoint, key = _fixture()
    result = _verify(report, checkpoint, key)
    assert result["decision"] == "candidate_checkpoint_valid"
    assert result["checkpoint_valid"] is True
    assert result["writes_active_memory"] is False
    assert result["promotion_allowed"] is False


def test_whole_chain_rewrite_is_detected_by_old_checkpoint() -> None:
    _, checkpoint, key = _fixture()
    rewritten = CHAIN.verify_chain(_chain(("rewritten-1", "rewritten-2", "rewritten-3")))
    assert rewritten["chain_valid"] is True
    result = _verify(rewritten, checkpoint, key)
    assert result["decision"] == "quarantine"
    assert "head_hash_mismatch" in result["reasons"]


def test_truncated_chain_is_detected() -> None:
    _, checkpoint, key = _fixture()
    truncated = CHAIN.verify_chain(_chain(("first", "second")))
    result = _verify(truncated, checkpoint, key)
    assert "event_count_mismatch" in result["reasons"]
    assert "head_hash_mismatch" in result["reasons"]


def test_checkpoint_field_tampering_breaks_signature() -> None:
    report, checkpoint, key = _fixture()
    attacked = copy.deepcopy(checkpoint)
    attacked["issued_at"] = "2026-08-03T03:00:00Z"
    result = _verify(report, attacked, key)
    assert "invalid_signature" in result["reasons"]


def test_untrusted_signer_is_rejected_even_with_valid_signature() -> None:
    report, _, trusted_key = _fixture()
    attacker_key = Ed25519PrivateKey.generate()
    forged = CHECKPOINT.create_checkpoint(
        chain_id="experience-memory/main",
        event_count=report["events_checked"],
        head_hash=report["head_hash"],
        issued_at="2026-08-02T03:00:00Z",
        signer_id="attacker",
        private_key=attacker_key,
    )
    result = _verify(report, forged, trusted_key)
    assert result["decision"] == "quarantine"
    assert "untrusted_signer" in result["reasons"]


def test_re_signed_rewrite_with_wrong_key_is_rejected() -> None:
    _, _, trusted_key = _fixture()
    rewritten = CHAIN.verify_chain(_chain(("rewritten-1", "rewritten-2", "rewritten-3")))
    attacker_key = Ed25519PrivateKey.generate()
    forged = CHECKPOINT.create_checkpoint(
        chain_id="experience-memory/main",
        event_count=rewritten["events_checked"],
        head_hash=rewritten["head_hash"],
        issued_at="2026-08-02T03:05:00Z",
        signer_id="external-evaluator-a",
        private_key=attacker_key,
    )
    result = _verify(rewritten, forged, trusted_key)
    assert "invalid_signature" in result["reasons"]


def test_invalid_signature_encoding_fails_closed() -> None:
    report, checkpoint, key = _fixture()
    checkpoint["signature_b64"] = "not base64!"
    result = _verify(report, checkpoint, key)
    assert "invalid_signature_encoding" in result["reasons"]
