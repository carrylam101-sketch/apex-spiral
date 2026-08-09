"""Candidate gate for binding an evaluator attestation to one held-out request.

This verifies a signed attestation without receiving the sealed expected output.
It is a local replay candidate, not proof of an off-host evaluator or asymmetric
hardware-backed identity.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Mapping

_REQUIRED_REQUEST = ("candidate_id", "candidate_sha256", "challenge_nonce")
_REQUIRED_ATTESTATION = (
    "verdict",
    "expected_sha256",
    "signed_at",
    "evaluator_pubkey_sha256",
    "candidate_id",
    "candidate_sha256",
    "challenge_nonce",
    "attestation_sig",
)


def _canonical_unsigned(attestation: Mapping[str, Any]) -> bytes:
    unsigned = {key: value for key, value in attestation.items() if key != "attestation_sig"}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _hex64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        char in "0123456789abcdef" for char in value.lower()
    )


def verify_attestation_binding(
    request: Mapping[str, Any],
    attestation: Mapping[str, Any],
    evaluator_secret: bytes,
) -> dict[str, Any]:
    """Fail closed unless identity, signature, and request binding all verify."""
    reasons: list[str] = []
    for field in _REQUIRED_REQUEST:
        if not request.get(field):
            reasons.append(f"missing_request_field:{field}")
    for field in _REQUIRED_ATTESTATION:
        if not attestation.get(field):
            reasons.append(f"missing_attestation_field:{field}")

    expected_key_id = hashlib.sha256(evaluator_secret).hexdigest()
    key_identity_valid = hmac.compare_digest(
        str(attestation.get("evaluator_pubkey_sha256", "")), expected_key_id
    )
    if not key_identity_valid:
        reasons.append("evaluator_key_identity_mismatch")

    provided_sig = str(attestation.get("attestation_sig", ""))
    computed_sig = hmac.new(
        evaluator_secret, _canonical_unsigned(attestation), hashlib.sha256
    ).hexdigest()
    signature_valid = bool(provided_sig) and hmac.compare_digest(provided_sig, computed_sig)
    if not signature_valid:
        reasons.append("attestation_signature_invalid")

    bindings = (
        ("candidate_id", "candidate_id_mismatch"),
        ("candidate_sha256", "candidate_sha256_mismatch"),
        ("challenge_nonce", "challenge_nonce_mismatch"),
    )
    for field, reason in bindings:
        if request.get(field) != attestation.get(field):
            reasons.append(reason)

    if request.get("candidate_sha256") and not _hex64(request.get("candidate_sha256")):
        reasons.append("request_candidate_sha256_not_hex64")
    if attestation.get("expected_sha256") and not _hex64(attestation.get("expected_sha256")):
        reasons.append("attestation_expected_sha256_not_hex64")
    if attestation.get("verdict") not in {"pass", "fail", "inconclusive"}:
        reasons.append("verdict_not_in_alphabet")

    request_binding_valid = not any(reason.endswith("_mismatch") for reason in reasons)
    decision = "candidate_verify" if not reasons else "hold"
    return {
        "decision": decision,
        "promotion_allowed": False,
        "signature_valid": signature_valid,
        "key_identity_valid": key_identity_valid,
        "request_binding_valid": request_binding_valid,
        "sealed_expected_received": False,
        "reasons": reasons,
        "boundary": "local HMAC replay only; off-host and asymmetric trust remain unverified",
    }
