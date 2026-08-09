"""Candidate gate for attestation freshness and atomic one-time nonce use.

This is a local filesystem replay. It does not establish an off-host evaluator,
trusted wall clock, distributed atomicity, or hardware-backed identity.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

MAX_AGE_SECONDS = 300.0
MAX_FUTURE_SKEW_SECONDS = 30.0
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


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _nonce_marker(ledger_dir: Path, evaluator_id: str, nonce: str) -> Path:
    digest = hashlib.sha256(f"{evaluator_id}\0{nonce}".encode("utf-8")).hexdigest()
    return ledger_dir / f"{digest}.used"


def _consume_once(marker: Path, record: Mapping[str, Any]) -> bool:
    marker.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(marker, flags, 0o600)
    except FileExistsError:
        return False
    try:
        payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    return True


def verify_fresh_attestation(
    request: Mapping[str, Any],
    attestation: Mapping[str, Any],
    evaluator_secret: bytes,
    ledger_dir: Path | str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify binding/freshness, then atomically consume the nonce on success."""
    reasons: list[str] = []
    for field in _REQUIRED_REQUEST:
        if not request.get(field):
            reasons.append(f"missing_request_field:{field}")
    for field in _REQUIRED_ATTESTATION:
        if not attestation.get(field):
            reasons.append(f"missing_attestation_field:{field}")

    expected_key_id = hashlib.sha256(evaluator_secret).hexdigest()
    evaluator_id = str(attestation.get("evaluator_pubkey_sha256", ""))
    key_identity_valid = hmac.compare_digest(evaluator_id, expected_key_id)
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

    signed_at = _parse_time(attestation.get("signed_at"))
    if signed_at is None:
        reasons.append("signed_at_invalid")
        age_seconds = None
    else:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        age_seconds = (current - signed_at).total_seconds()
        if age_seconds > MAX_AGE_SECONDS:
            reasons.append("attestation_stale")
        if age_seconds < -MAX_FUTURE_SKEW_SECONDS:
            reasons.append("attestation_from_future")

    nonce_consumed = False
    if not reasons:
        marker = _nonce_marker(
            Path(ledger_dir), evaluator_id, str(request.get("challenge_nonce", ""))
        )
        nonce_consumed = _consume_once(
            marker,
            {
                "candidate_id": request.get("candidate_id"),
                "candidate_sha256": request.get("candidate_sha256"),
                "challenge_nonce": request.get("challenge_nonce"),
                "evaluator_pubkey_sha256": evaluator_id,
                "signed_at": attestation.get("signed_at"),
            },
        )
        if not nonce_consumed:
            reasons.append("challenge_nonce_already_consumed")

    return {
        "decision": "candidate_verify" if not reasons else "hold",
        "promotion_allowed": False,
        "signature_valid": signature_valid,
        "key_identity_valid": key_identity_valid,
        "request_binding_valid": not any(reason.endswith("_mismatch") for reason in reasons),
        "freshness_valid": signed_at is not None and not any(
            reason in {"attestation_stale", "attestation_from_future"} for reason in reasons
        ),
        "age_seconds": age_seconds,
        "nonce_consumed": nonce_consumed,
        "sealed_expected_received": False,
        "reasons": reasons,
        "boundary": "local ledger and clock only; off-host trust and distributed atomicity unverified",
    }
