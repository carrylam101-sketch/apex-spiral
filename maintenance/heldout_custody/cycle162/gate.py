"""Candidate gate for post-commit held-out fixture custody.

The evaluator freezes the candidate first, then generates a fresh canary and
commits a fixture set carrying that canary. Verification rejects changed
candidates, reordered custody events, reused/weak canaries, and any candidate
that already contained the post-commit canary. This is leakage evidence, not a
proof of secrecy, so promotion is always disabled.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import time
from pathlib import Path
from typing import Any


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(payload)


def begin_custody(candidate: Path, canary_bytes: int = 16) -> dict[str, Any]:
    if not candidate.is_file():
        raise ValueError("candidate_missing")
    if canary_bytes < 16:
        raise ValueError("canary_too_short")
    return {
        "candidate": {"path": str(candidate), "sha256": sha256_file(candidate)},
        "candidate_committed_ns": time.time_ns(),
        "canary": secrets.token_hex(canary_bytes),
        "canary_bytes": canary_bytes,
    }


def reveal_fixtures(custody: dict[str, Any], fixtures: list[Path]) -> dict[str, Any]:
    if len(fixtures) < 3:
        raise ValueError("fixture_set_too_small")
    entries = []
    canary = str(custody["canary"])
    for path in sorted(fixtures, key=lambda item: str(item)):
        if not path.is_file():
            raise ValueError("fixture_missing")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("custody_canary") != canary:
            raise ValueError("fixture_canary_mismatch")
        entries.append({"path": str(path), "sha256": sha256_file(path)})
    transcript = dict(custody)
    transcript["fixtures"] = entries
    transcript["fixtures_digest"] = canonical_digest(entries)
    transcript["fixtures_revealed_ns"] = time.time_ns()
    transcript["transcript_digest"] = canonical_digest(
        {key: value for key, value in transcript.items() if key != "transcript_digest"}
    )
    return transcript


def verify_custody(transcript: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    candidate_entry = transcript.get("candidate", {})
    candidate = Path(str(candidate_entry.get("path", "")))
    canary = str(transcript.get("canary", ""))
    canary_bytes = transcript.get("canary_bytes")

    if not isinstance(canary_bytes, int) or canary_bytes < 16 or len(canary) != canary_bytes * 2:
        reasons.append("canary_strength_invalid")
    try:
        bytes.fromhex(canary)
    except ValueError:
        reasons.append("canary_not_hex")

    candidate_ok = candidate.is_file() and sha256_file(candidate) == candidate_entry.get("sha256")
    if not candidate_ok:
        reasons.append("candidate_changed_or_missing")
    elif canary and canary.encode("utf-8") in candidate.read_bytes():
        reasons.append("post_commit_canary_present_in_candidate")

    committed_ns = transcript.get("candidate_committed_ns")
    revealed_ns = transcript.get("fixtures_revealed_ns")
    if not isinstance(committed_ns, int) or not isinstance(revealed_ns, int) or revealed_ns <= committed_ns:
        reasons.append("custody_order_invalid")

    fixtures = transcript.get("fixtures")
    if not isinstance(fixtures, list) or len(fixtures) < 3:
        reasons.append("fixture_set_too_small")
        fixtures = []
    current_entries = []
    for entry in fixtures:
        path = Path(str(entry.get("path", "")))
        digest = str(entry.get("sha256", ""))
        if not path.is_file() or sha256_file(path) != digest:
            reasons.append("fixture_changed_or_missing")
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            reasons.append("fixture_invalid")
            continue
        if payload.get("custody_canary") != canary:
            reasons.append("fixture_canary_mismatch")
        current_entries.append({"path": str(path), "sha256": digest})

    if canonical_digest(current_entries) != transcript.get("fixtures_digest"):
        reasons.append("fixtures_digest_mismatch")
    expected_transcript_digest = canonical_digest(
        {key: value for key, value in transcript.items() if key != "transcript_digest"}
    )
    if expected_transcript_digest != transcript.get("transcript_digest"):
        reasons.append("transcript_digest_mismatch")

    decision = "candidate_verify" if not reasons else "hold"
    return {
        "decision": decision,
        "reasons": sorted(set(reasons)),
        "mechanism": "post_commit_fixture_custody_canary",
        "candidate_frozen_before_fixture_reveal": not reasons,
        "precommit_canary_leak_detected": "post_commit_canary_present_in_candidate" in reasons,
        "hiddenness_verified": False,
        "organizational_independence_verified": False,
        "promotion_allowed": False,
        "status": "candidate_hold",
    }
