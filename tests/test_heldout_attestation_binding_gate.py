"""Tests for candidate-only held-out attestation binding verification."""
from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "maintenance" / "heldout_attestation_binding" / "cycle169" / "gate.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("heldout_attestation_binding_cycle169", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _case(secret: bytes = b"cycle169-test-key") -> tuple[dict, dict, bytes]:
    request = {
        "candidate_id": "candidate-169",
        "candidate_sha256": hashlib.sha256(b"candidate-body").hexdigest(),
        "challenge_nonce": "nonce-169",
    }
    attestation = {
        "verdict": "pass",
        "expected_sha256": hashlib.sha256(b"sealed-expected").hexdigest(),
        "signed_at": "2026-08-05T03:00:00+08:00",
        "evaluator_pubkey_sha256": hashlib.sha256(secret).hexdigest(),
        "candidate_id": request["candidate_id"],
        "candidate_sha256": request["candidate_sha256"],
        "challenge_nonce": request["challenge_nonce"],
    }
    payload = json.dumps(attestation, sort_keys=True, separators=(",", ":")).encode()
    attestation["attestation_sig"] = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return request, attestation, secret


def test_valid_attestation_is_candidate_verify_only() -> None:
    module = _load_module()
    request, attestation, secret = _case()
    report = module.verify_attestation_binding(request, attestation, secret)
    assert report["decision"] == "candidate_verify"
    assert report["promotion_allowed"] is False
    assert report["signature_valid"] is True
    assert report["request_binding_valid"] is True


def test_nonce_replay_is_rejected() -> None:
    module = _load_module()
    request, attestation, secret = _case()
    request["challenge_nonce"] = "fresh-nonce"
    report = module.verify_attestation_binding(request, attestation, secret)
    assert report["decision"] == "hold"
    assert "challenge_nonce_mismatch" in report["reasons"]


def test_candidate_hash_swap_is_rejected() -> None:
    module = _load_module()
    request, attestation, secret = _case()
    request["candidate_sha256"] = hashlib.sha256(b"different-candidate").hexdigest()
    report = module.verify_attestation_binding(request, attestation, secret)
    assert report["decision"] == "hold"
    assert "candidate_sha256_mismatch" in report["reasons"]


def test_verdict_tamper_breaks_signature() -> None:
    module = _load_module()
    request, attestation, secret = _case()
    attestation["verdict"] = "fail"
    report = module.verify_attestation_binding(request, attestation, secret)
    assert report["decision"] == "hold"
    assert report["signature_valid"] is False
    assert "attestation_signature_invalid" in report["reasons"]


def test_wrong_key_identity_is_rejected() -> None:
    module = _load_module()
    request, attestation, _ = _case()
    report = module.verify_attestation_binding(request, attestation, b"wrong-key")
    assert report["decision"] == "hold"
    assert "evaluator_key_identity_mismatch" in report["reasons"]


def test_missing_binding_field_fails_closed() -> None:
    module = _load_module()
    request, attestation, secret = _case()
    del attestation["candidate_id"]
    report = module.verify_attestation_binding(request, attestation, secret)
    assert report["decision"] == "hold"
    assert "missing_attestation_field:candidate_id" in report["reasons"]
