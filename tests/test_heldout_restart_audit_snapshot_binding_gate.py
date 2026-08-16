"""Tests for candidate-only binding of restart audits to ledger bytes and evaluator challenge."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NONCE_GATE = ROOT / "maintenance" / "heldout_nonce_ledger" / "cycle171" / "gate.py"
MODULE_PATH = ROOT / "maintenance" / "heldout_nonce_ledger" / "cycle173" / "snapshot.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _record(nonce: str = "nonce-173") -> dict:
    return {
        "candidate_id": "candidate-173",
        "candidate_sha256": "a" * 64,
        "challenge_nonce": nonce,
        "evaluator_pubkey_sha256": "b" * 64,
        "signed_at": "2026-08-13T03:00:00+08:00",
    }


def _consume(ledger: Path, record: dict) -> Path:
    gate = _load(NONCE_GATE, "nonce_gate_cycle171_for_snapshot")
    report = gate.consume_nonce_durably(ledger, record)
    assert report["decision"] == "candidate_verify"
    return Path(report["marker_path"])


def test_clean_snapshot_verifies_against_same_ledger_and_challenge(tmp_path: Path) -> None:
    _consume(tmp_path, _record())
    gate = _load(MODULE_PATH, "snapshot_clean")
    snapshot = gate.create_bound_snapshot(tmp_path, "challenge-173")
    report = gate.verify_bound_snapshot(tmp_path, "challenge-173", snapshot)
    assert report["decision"] == "candidate_verify"
    assert report["ledger_digest_match"] is True
    assert report["challenge_match"] is True
    assert report["audit_report_match"] is True
    assert report["snapshot_integrity_match"] is True
    assert report["promotion_allowed"] is False


def test_ledger_mutation_after_snapshot_holds(tmp_path: Path) -> None:
    marker = _consume(tmp_path, _record())
    gate = _load(MODULE_PATH, "snapshot_mutation")
    snapshot = gate.create_bound_snapshot(tmp_path, "challenge-173")
    envelope = json.loads(marker.read_text(encoding="utf-8"))
    envelope["record"]["candidate_id"] = "tampered"
    marker.write_text(json.dumps(envelope), encoding="utf-8")
    report = gate.verify_bound_snapshot(tmp_path, "challenge-173", snapshot)
    assert report["decision"] == "hold"
    assert report["ledger_digest_match"] is False
    assert "ledger_changed_after_audit" in report["reasons"]


def test_reused_snapshot_with_different_challenge_holds(tmp_path: Path) -> None:
    _consume(tmp_path, _record())
    gate = _load(MODULE_PATH, "snapshot_replay")
    snapshot = gate.create_bound_snapshot(tmp_path, "challenge-173")
    report = gate.verify_bound_snapshot(tmp_path, "challenge-other", snapshot)
    assert report["decision"] == "hold"
    assert report["challenge_match"] is False
    assert "evaluator_challenge_mismatch" in report["reasons"]


def test_tampered_embedded_audit_report_holds(tmp_path: Path) -> None:
    _consume(tmp_path, _record())
    gate = _load(MODULE_PATH, "snapshot_report_tamper")
    snapshot = gate.create_bound_snapshot(tmp_path, "challenge-173")
    snapshot["audit_report"]["decision"] = "hold"
    report = gate.verify_bound_snapshot(tmp_path, "challenge-173", snapshot)
    assert report["decision"] == "hold"
    assert report["audit_report_match"] is False
    assert report["snapshot_integrity_match"] is False


def test_tampered_binding_digest_holds(tmp_path: Path) -> None:
    _consume(tmp_path, _record())
    gate = _load(MODULE_PATH, "snapshot_digest_tamper")
    snapshot = gate.create_bound_snapshot(tmp_path, "challenge-173")
    snapshot["ledger_manifest_sha256"] = "0" * 64
    report = gate.verify_bound_snapshot(tmp_path, "challenge-173", snapshot)
    assert report["decision"] == "hold"
    assert report["ledger_digest_match"] is False
    assert report["snapshot_integrity_match"] is False


def test_empty_challenge_cannot_create_verifiable_snapshot(tmp_path: Path) -> None:
    _consume(tmp_path, _record())
    gate = _load(MODULE_PATH, "snapshot_empty_challenge")
    snapshot = gate.create_bound_snapshot(tmp_path, "")
    report = gate.verify_bound_snapshot(tmp_path, "", snapshot)
    assert snapshot["audit_report"]["decision"] == "candidate_verify"
    assert report["decision"] == "hold"
    assert "evaluator_challenge_empty" in report["reasons"]


def test_corrupt_ledger_audit_cannot_become_candidate_verify(tmp_path: Path) -> None:
    marker = _consume(tmp_path, _record())
    marker.write_bytes(b"")
    gate = _load(MODULE_PATH, "snapshot_corrupt")
    snapshot = gate.create_bound_snapshot(tmp_path, "challenge-173")
    report = gate.verify_bound_snapshot(tmp_path, "challenge-173", snapshot)
    assert snapshot["audit_report"]["decision"] == "hold"
    assert report["decision"] == "hold"
    assert "embedded_audit_not_verified" in report["reasons"]
