"""Candidate monotonic freshness gate for signed experience-memory checkpoints.

A v2 checkpoint signs both a monotonic checkpoint sequence and the digest of
its predecessor. Verification compares that signed data with an externally
held trusted watermark. The module never writes active memory or watermark
state; callers may persist a newly accepted watermark only after independent
review.
"""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

GENESIS_CHECKPOINT_HASH = "0" * 64


def canonical_checkpoint(checkpoint: dict[str, Any]) -> bytes:
    payload = {
        "chain_id": checkpoint.get("chain_id"),
        "checkpoint_seq": checkpoint.get("checkpoint_seq"),
        "event_count": checkpoint.get("event_count"),
        "head_hash": checkpoint.get("head_hash"),
        "issued_at": checkpoint.get("issued_at"),
        "prev_checkpoint_sha256": checkpoint.get("prev_checkpoint_sha256"),
        "signer_id": checkpoint.get("signer_id"),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def checkpoint_sha256(checkpoint: dict[str, Any]) -> str:
    envelope = {
        "payload": json.loads(canonical_checkpoint(checkpoint).decode("ascii")),
        "signature_b64": checkpoint.get("signature_b64"),
    }
    encoded = json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def create_checkpoint(
    *,
    chain_id: str,
    checkpoint_seq: int,
    event_count: int,
    head_hash: str,
    issued_at: str,
    prev_checkpoint_sha256: str,
    signer_id: str,
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    checkpoint: dict[str, Any] = {
        "chain_id": chain_id,
        "checkpoint_seq": checkpoint_seq,
        "event_count": event_count,
        "head_hash": head_hash,
        "issued_at": issued_at,
        "prev_checkpoint_sha256": prev_checkpoint_sha256,
        "signer_id": signer_id,
    }
    checkpoint["signature_b64"] = base64.b64encode(
        private_key.sign(canonical_checkpoint(checkpoint))
    ).decode("ascii")
    return checkpoint


def verify_fresh_checkpoint(
    *,
    chain_report: dict[str, Any],
    checkpoint: dict[str, Any],
    expected_chain_id: str,
    trusted_public_keys: dict[str, Ed25519PublicKey],
    trusted_watermark: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    signer_id = str(checkpoint.get("signer_id", ""))
    public_key = trusted_public_keys.get(signer_id)
    sequence = checkpoint.get("checkpoint_seq")
    trusted_sequence = trusted_watermark.get("checkpoint_seq")
    trusted_hash = trusted_watermark.get("checkpoint_sha256")

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
    if not isinstance(sequence, int) or sequence < 1:
        reasons.append("invalid_checkpoint_seq")
    if not isinstance(trusted_sequence, int) or trusted_sequence < 0:
        reasons.append("invalid_trusted_watermark_seq")
    if not isinstance(trusted_hash, str) or len(trusted_hash) != 64:
        reasons.append("invalid_trusted_watermark_hash")

    if isinstance(sequence, int) and isinstance(trusted_sequence, int):
        if sequence <= trusted_sequence:
            reasons.append("checkpoint_rollback_or_replay")
        elif sequence != trusted_sequence + 1:
            reasons.append("checkpoint_sequence_gap")

    if isinstance(trusted_hash, str) and checkpoint.get("prev_checkpoint_sha256") != trusted_hash:
        reasons.append("checkpoint_predecessor_mismatch")

    try:
        signature = base64.b64decode(str(checkpoint.get("signature_b64", "")), validate=True)
    except (ValueError, TypeError):
        signature = b""
        reasons.append("invalid_signature_encoding")

    if public_key is not None and signature:
        try:
            public_key.verify(signature, canonical_checkpoint(checkpoint))
        except InvalidSignature:
            reasons.append("invalid_signature")

    valid = not reasons
    next_watermark = None
    if valid:
        next_watermark = {
            "checkpoint_seq": sequence,
            "checkpoint_sha256": checkpoint_sha256(checkpoint),
        }
    return {
        "decision": "candidate_fresh_checkpoint" if valid else "quarantine",
        "checkpoint_valid": valid,
        "freshness_valid": valid,
        "reasons": reasons,
        "proposed_next_watermark": next_watermark,
        "writes_active_memory": False,
        "writes_trusted_watermark": False,
        "promotion_allowed": False,
        "status": "candidate_hold",
    }
