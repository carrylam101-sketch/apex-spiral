"""Tests for candidate-only attestation freshness and one-time nonce use."""
from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "maintenance" / "heldout_attestation_freshness" / "cycle170" / "gate.py"
NOW = datetime(2026, 8, 6, 3, 0, 0, tzinfo=timezone(timedelta(hours=8)))


def _load_module():
    spec = importlib.util.spec_from_file_location("heldout_attestation_freshness_cycle170", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _case(signed_at: datetime = NOW, nonce: str = "nonce-170") -> tuple[dict, dict, bytes]:
    secret = b"cycle170-test-key"
    request = {
        "candidate_id": "candidate-170",
        "candidate_sha256": hashlib.sha256(b"candidate-body").hexdigest(),
        "challenge_nonce": nonce,
    }
    attestation = {
        "verdict": "pass",
        "expected_sha256": hashlib.sha256(b"sealed-expected").hexdigest(),
        "signed_at": signed_at.isoformat(),
        "evaluator_pubkey_sha256": hashlib.sha256(secret).hexdigest(),
        "candidate_id": request["candidate_id"],
        "candidate_sha256": request["candidate_sha256"],
        "challenge_nonce": request["challenge_nonce"],
    }
    payload = json.dumps(attestation, sort_keys=True, separators=(",", ":")).encode()
    attestation["attestation_sig"] = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return request, attestation, secret


def test_fresh_attestation_consumes_nonce_once(tmp_path: Path) -> None:
    module = _load_module()
    request, attestation, secret = _case()
    first = module.verify_fresh_attestation(request, attestation, secret, tmp_path, now=NOW)
    second = module.verify_fresh_attestation(request, attestation, secret, tmp_path, now=NOW)
    assert first["decision"] == "candidate_verify"
    assert first["nonce_consumed"] is True
    assert first["promotion_allowed"] is False
    assert second["decision"] == "hold"
    assert second["nonce_consumed"] is False
    assert "challenge_nonce_already_consumed" in second["reasons"]


def test_stale_attestation_is_rejected_without_consuming_nonce(tmp_path: Path) -> None:
    module = _load_module()
    request, stale, secret = _case(NOW - timedelta(seconds=301))
    held = module.verify_fresh_attestation(request, stale, secret, tmp_path, now=NOW)
    request, fresh, secret = _case(NOW)
    accepted = module.verify_fresh_attestation(request, fresh, secret, tmp_path, now=NOW)
    assert held["decision"] == "hold"
    assert "attestation_stale" in held["reasons"]
    assert held["nonce_consumed"] is False
    assert accepted["decision"] == "candidate_verify"


def test_future_attestation_beyond_skew_is_rejected(tmp_path: Path) -> None:
    module = _load_module()
    request, attestation, secret = _case(NOW + timedelta(seconds=31))
    report = module.verify_fresh_attestation(request, attestation, secret, tmp_path, now=NOW)
    assert report["decision"] == "hold"
    assert "attestation_from_future" in report["reasons"]
    assert report["nonce_consumed"] is False


def test_malformed_timestamp_fails_closed(tmp_path: Path) -> None:
    module = _load_module()
    request, attestation, secret = _case()
    attestation["signed_at"] = "not-a-time"
    payload = json.dumps({k: v for k, v in attestation.items() if k != "attestation_sig"}, sort_keys=True, separators=(",", ":")).encode()
    attestation["attestation_sig"] = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    report = module.verify_fresh_attestation(request, attestation, secret, tmp_path, now=NOW)
    assert report["decision"] == "hold"
    assert "signed_at_invalid" in report["reasons"]


def test_bad_signature_does_not_burn_nonce(tmp_path: Path) -> None:
    module = _load_module()
    request, bad, secret = _case()
    bad["attestation_sig"] = "0" * 64
    held = module.verify_fresh_attestation(request, bad, secret, tmp_path, now=NOW)
    request, good, secret = _case()
    accepted = module.verify_fresh_attestation(request, good, secret, tmp_path, now=NOW)
    assert held["decision"] == "hold"
    assert held["nonce_consumed"] is False
    assert accepted["decision"] == "candidate_verify"


def test_atomic_consumption_allows_only_one_concurrent_accept(tmp_path: Path) -> None:
    module = _load_module()
    request, attestation, secret = _case()

    def run_once() -> dict:
        return module.verify_fresh_attestation(request, attestation, secret, tmp_path, now=NOW)

    with ThreadPoolExecutor(max_workers=8) as pool:
        reports = list(pool.map(lambda _: run_once(), range(8)))
    assert sum(report["decision"] == "candidate_verify" for report in reports) == 1
    assert sum("challenge_nonce_already_consumed" in report["reasons"] for report in reports) == 7
