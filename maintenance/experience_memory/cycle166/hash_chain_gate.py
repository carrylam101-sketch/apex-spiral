"""Candidate append-only hash-chain gate for experience-memory provenance.

The gate detects mutation, deletion, reordering, and duplicate replay across
session records. It never writes active memory and never permits promotion.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

GENESIS_HASH = "0" * 64
REQUIRED_EVIDENCE = {"task_result", "independent_eval", "held_out"}


def canonical_event(event: dict[str, Any]) -> bytes:
    payload = {
        "sequence": event.get("sequence"),
        "event_id": event.get("event_id"),
        "session_id": event.get("session_id"),
        "memory_key": event.get("memory_key"),
        "content": event.get("content"),
        "task_scope": event.get("task_scope"),
        "source_ref": event.get("source_ref"),
        "verification_status": event.get("verification_status"),
        "evidence_types": sorted(event.get("evidence_types", [])),
        "prev_hash": event.get("prev_hash"),
    }
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def event_hash(event: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_event(event)).hexdigest()


def seal_event(event: dict[str, Any], prev_hash: str) -> dict[str, Any]:
    sealed = dict(event)
    sealed["prev_hash"] = prev_hash
    sealed["event_hash"] = event_hash(sealed)
    return sealed


def verify_chain(events: list[dict[str, Any]]) -> dict[str, Any]:
    reasons: list[str] = []
    expected_prev = GENESIS_HASH
    seen_event_ids: set[str] = set()
    seen_sequences: set[int] = set()

    if not events:
        reasons.append("empty_chain")

    for index, event in enumerate(events, start=1):
        sequence = event.get("sequence")
        event_id = str(event.get("event_id", ""))
        evidence = set(event.get("evidence_types", []))

        if sequence != index:
            reasons.append(f"sequence_gap_or_reorder:{index}")
        if not isinstance(sequence, int) or sequence in seen_sequences:
            reasons.append(f"duplicate_or_invalid_sequence:{index}")
        elif isinstance(sequence, int):
            seen_sequences.add(sequence)

        if not event_id or event_id in seen_event_ids:
            reasons.append(f"duplicate_or_missing_event_id:{index}")
        else:
            seen_event_ids.add(event_id)

        if event.get("prev_hash") != expected_prev:
            reasons.append(f"prev_hash_mismatch:{index}")
        actual_hash = event_hash(event)
        if event.get("event_hash") != actual_hash:
            reasons.append(f"event_hash_mismatch:{index}")

        if event.get("verification_status") != "verified":
            reasons.append(f"not_verified:{index}")
        if not REQUIRED_EVIDENCE.issubset(evidence):
            reasons.append(f"incomplete_evidence:{index}")
        if event.get("task_scope") in (None, "", "global"):
            reasons.append(f"scope_missing_or_global:{index}")

        expected_prev = actual_hash

    chain_valid = not reasons
    return {
        "decision": "candidate_chain_valid" if chain_valid else "quarantine",
        "reasons": reasons,
        "chain_valid": chain_valid,
        "events_checked": len(events),
        "head_hash": expected_prev if events else GENESIS_HASH,
        "writes_active_memory": False,
        "promotion_allowed": False,
        "status": "candidate_hold",
    }
