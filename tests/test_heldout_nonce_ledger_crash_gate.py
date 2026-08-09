"""Tests for candidate-only crash-consistent nonce consumption."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "maintenance" / "heldout_nonce_ledger" / "cycle171" / "gate.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("heldout_nonce_ledger_cycle171", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _record(nonce: str = "nonce-171") -> dict:
    return {
        "candidate_id": "candidate-171",
        "candidate_sha256": "a" * 64,
        "challenge_nonce": nonce,
        "evaluator_pubkey_sha256": "b" * 64,
        "signed_at": "2026-08-07T03:00:00+08:00",
    }


def test_first_consume_is_durable_and_replay_holds(tmp_path: Path) -> None:
    module = _load_module()
    first = module.consume_nonce_durably(tmp_path, _record())
    second = module.consume_nonce_durably(tmp_path, _record())
    assert first["decision"] == "candidate_verify"
    assert first["durable_commit"] is True
    assert second["decision"] == "hold"
    assert "challenge_nonce_already_consumed" in second["reasons"]


def test_truncated_existing_marker_fails_closed(tmp_path: Path) -> None:
    module = _load_module()
    marker = module.marker_path(tmp_path, _record())
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_bytes(b"")
    report = module.consume_nonce_durably(tmp_path, _record())
    assert report["decision"] == "hold"
    assert "ledger_marker_corrupt" in report["reasons"]


def test_tampered_existing_marker_fails_closed(tmp_path: Path) -> None:
    module = _load_module()
    accepted = module.consume_nonce_durably(tmp_path, _record())
    marker = Path(accepted["marker_path"])
    payload = json.loads(marker.read_text())
    payload["record"]["candidate_id"] = "swapped"
    marker.write_text(json.dumps(payload))
    report = module.consume_nonce_durably(tmp_path, _record())
    assert report["decision"] == "hold"
    assert "ledger_marker_corrupt" in report["reasons"]


def test_write_failure_leaves_fail_closed_marker(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    real_write = os.write
    calls = {"count": 0}

    def fail_after_create(fd: int, data: bytes) -> int:
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError("simulated write interruption")
        return real_write(fd, data)

    monkeypatch.setattr(module.os, "write", fail_after_create)
    first = module.consume_nonce_durably(tmp_path, _record())
    monkeypatch.setattr(module.os, "write", real_write)
    second = module.consume_nonce_durably(tmp_path, _record())
    assert first["decision"] == "hold"
    assert "ledger_commit_failed" in first["reasons"]
    assert second["decision"] == "hold"
    assert "ledger_marker_corrupt" in second["reasons"]


def test_directory_fsync_failure_never_accepts(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    real_fsync = os.fsync
    calls = {"count": 0}

    def fail_directory_sync(fd: int) -> None:
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("simulated directory fsync failure")
        real_fsync(fd)

    monkeypatch.setattr(module.os, "fsync", fail_directory_sync)
    report = module.consume_nonce_durably(tmp_path, _record())
    assert report["decision"] == "hold"
    assert report["durable_commit"] is False
    assert "ledger_commit_failed" in report["reasons"]


def test_ledger_path_as_file_fails_closed(tmp_path: Path) -> None:
    module = _load_module()
    ledger = tmp_path / "not-a-directory"
    ledger.write_text("occupied")
    report = module.consume_nonce_durably(ledger, _record())
    assert report["decision"] == "hold"
    assert "ledger_unavailable" in report["reasons"]


def test_concurrent_consumption_accepts_exactly_one(tmp_path: Path) -> None:
    module = _load_module()

    def consume(_: int) -> dict:
        return module.consume_nonce_durably(tmp_path, _record())

    with ThreadPoolExecutor(max_workers=8) as pool:
        reports = list(pool.map(consume, range(8)))
    assert sum(report["decision"] == "candidate_verify" for report in reports) == 1
    assert sum(report["decision"] == "hold" for report in reports) == 7
