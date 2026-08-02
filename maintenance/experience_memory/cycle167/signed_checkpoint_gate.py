"""Candidate Ed25519 checkpoint gate for an experience-memory hash chain.

The checkpoint binds a chain identifier, event count, and head hash to a
separately held signing key. The verifier only receives trusted public keys.
This detects whole-chain rewrites by an actor who can edit memory records but
does not possess the external checkpoint signing key.
"""
from __future__ import annotations

import base64
import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def canonical_checkpoint(checkpoint: dict[str, Any]) -> bytes:
    payload = {
        "chain_id": checkpoint.get("chain_id"),
        "event_count": checkpoint.get("event_count"),
        "head_hash": checkpoint.get("head_hash"),
        "issued_at": checkpoint.get("issued_at"),
        "signer_id": checkpoint.get("signer_id"),
    }
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")


def create_checkpoint(
    *,
    chain_id: str,
    event_count: int,
    head_hash: str,
    issued_at: str,
    signer_id: str,
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    checkpoint: dict[str, Any] = {
        "chain_id": chain_id,
        "event_count": event_count,
        "head_hash": head_hash,
        "issued_at": issued_at,
        "signer_id": signer_id,
    }
    signature = private_key.sign(canonical_checkpoint(checkpoint))
    checkpoint["signature_b64"] = base64.b64encode(signature).decode("ascii")
    return checkpoint


def verify_signed_checkpoint(
    *,
    chain_report: dict[str, Any],
    checkpoint: dict[str, Any],
    expected_chain_id: str,
    trusted_public_keys: dict[str, Ed25519PublicKey],
) -> dict[str, Any]:
    reasons: list[str] = []
    signer_id = checkpoint.get("signer_id")
    public_key = trusted_public_keys.get(str(signer_id))

    if not chain_report.get("chain_valid"):
        reasons.append("underlying_chain_invalid")
    if checkpoint.get("chain_id") != expected_chain_id:
        reasons.append("chain_id_mismatch")
    if checkpoint.get("event_count") != chain_report.get("events_checked"):
        reasons.append("event_count_mismatch")
    if checkpoint.get("head_hash") != chain_report.get("head_hash"):
        reasons.append("head_hash_mismatch")
    if public_key is None:
        reasons.append("untrusted_signer")
    if not checkpoint.get("issued_at"):
        reasons.append("missing_issued_at")

    try:
        signature = base64.b64decode(
            str(checkpoint.get("signature_b64", "")),
            validate=True,
        )
    except (ValueError, TypeError):
        signature = b""
        reasons.append("invalid_signature_encoding")

    if public_key is not None and signature:
        try:
            public_key.verify(signature, canonical_checkpoint(checkpoint))
        except InvalidSignature:
            reasons.append("invalid_signature")

    valid = not reasons
    return {
        "decision": "candidate_checkpoint_valid" if valid else "quarantine",
        "checkpoint_valid": valid,
        "reasons": reasons,
        "signer_id": signer_id,
        "writes_active_memory": False,
        "promotion_allowed": False,
        "status": "candidate_hold",
    }
