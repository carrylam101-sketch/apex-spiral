"""Tests for candidate-only restart recovery audit of a nonce ledger."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_GATE = ROOT / "maintenance" / "heldout_nonce_ledger" / "cycle171" / "gate.py"
MODULE_PATH = ROOT / "maintenance" / "heldout_nonce_ledger" / "cycle172" / "audit.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _record(nonce: str = "nonce-172") -> dict:
    return {
        "candidate_id": "candidate-172",
        "candidate_sha256": "a" * 64,
        "challenge_nonce": nonce,
        "evaluator_pubkey_sha256": "b" * 64,
        "signed_at": "2026-08-12T03:00:00+08:00",
    }


def _consume(ledger: Path, record: dict) -> Path:
    gate = _load(PREVIOUS_GATE, "nonce_gate_cycle171_for_restart")
    report = gate.consume_nonce_durably(ledger, record)
    assert report["decision"] == "candidate_verify"
    return Path(report["marker_path"])


def test_clean_ledger_survives_cold_subprocess_restart(tmp_path: Path) -> None:
    _consume(tmp_path, _record())
    proc = subprocess.run(
        [sys.executable, str(MODULE_PATH), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    report = json.loads(proc.stdout)
    assert report["decision"] == "candidate_verify"
    assert report["counts"] == {"complete": 1, "conflict": 0, "corrupt": 0, "unexpected": 0}
    assert report["restart_scan_complete"] is True


def test_truncated_marker_is_classified_corrupt_and_holds(tmp_path: Path) -> None:
    marker = _consume(tmp_path, _record())
    marker.write_bytes(b"")
    audit = _load(MODULE_PATH, "restart_audit_truncated")
    report = audit.audit_ledger(tmp_path)
    assert report["decision"] == "hold"
    assert report["counts"]["corrupt"] == 1
    assert "corrupt_marker_present" in report["reasons"]


def test_filename_binding_mismatch_is_corrupt(tmp_path: Path) -> None:
    marker = _consume(tmp_path, _record())
    marker.rename(tmp_path / ("f" * 64 + ".used"))
    audit = _load(MODULE_PATH, "restart_audit_filename")
    report = audit.audit_ledger(tmp_path)
    assert report["decision"] == "hold"
    assert report["entries"][0]["classification"] == "corrupt"
    assert report["entries"][0]["reason"] == "marker_name_binding_mismatch"


def test_duplicate_logical_nonce_is_conflict_and_holds(tmp_path: Path) -> None:
    marker = _consume(tmp_path, _record())
    duplicate = tmp_path / ("e" * 64 + ".used")
    duplicate.write_bytes(marker.read_bytes())
    audit = _load(MODULE_PATH, "restart_audit_duplicate")
    report = audit.audit_ledger(tmp_path)
    assert report["decision"] == "hold"
    assert report["counts"]["conflict"] == 2
    assert "logical_nonce_conflict" in report["reasons"]


def test_mixed_directory_is_fully_enumerated_fail_closed(tmp_path: Path) -> None:
    _consume(tmp_path, _record("good"))
    (tmp_path / ("c" * 64 + ".used")).write_text("not-json", encoding="utf-8")
    (tmp_path / "foreign.tmp").write_text("partial", encoding="utf-8")
    audit = _load(MODULE_PATH, "restart_audit_mixed")
    report = audit.audit_ledger(tmp_path)
    assert report["decision"] == "hold"
    assert report["scanned_entries"] == 3
    assert report["counts"] == {"complete": 1, "conflict": 0, "corrupt": 1, "unexpected": 1}


def test_missing_ledger_is_unavailable_not_empty_success(tmp_path: Path) -> None:
    audit = _load(MODULE_PATH, "restart_audit_missing")
    report = audit.audit_ledger(tmp_path / "missing")
    assert report["decision"] == "hold"
    assert report["restart_scan_complete"] is False
    assert "ledger_unavailable" in report["reasons"]


def test_empty_existing_ledger_holds_as_no_recovery_evidence(tmp_path: Path) -> None:
    audit = _load(MODULE_PATH, "restart_audit_empty")
    report = audit.audit_ledger(tmp_path)
    assert report["decision"] == "hold"
    assert report["restart_scan_complete"] is True
    assert "no_consumption_evidence" in report["reasons"]
