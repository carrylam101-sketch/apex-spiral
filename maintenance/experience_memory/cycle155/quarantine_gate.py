"""Candidate provenance-bound quarantine gate for experience memory.

This module is isolated under maintenance/. It never writes active memory and never
promotes a record. It only emits deterministic admit/quarantine/reject advice.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_EVIDENCE = {"task_result", "independent_eval", "held_out"}


def canonical_payload(record: dict[str, Any]) -> bytes:
    payload = {
        "memory_key": record.get("memory_key"),
        "content": record.get("content"),
        "task_scope": record.get("task_scope"),
        "source_ref": record.get("source_ref"),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def payload_sha256(record: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_payload(record)).hexdigest()


def evaluate(record: dict[str, Any], active_memory: dict[str, str]) -> dict[str, Any]:
    reasons: list[str] = []
    expected_hash = record.get("payload_sha256", "")
    actual_hash = payload_sha256(record)
    evidence = set(record.get("evidence_types", []))
    verified = record.get("verification_status") == "verified"
    scoped = bool(record.get("task_scope")) and record.get("task_scope") != "global"
    independent = "independent_eval" in evidence
    held_out = "held_out" in evidence
    complete_evidence = REQUIRED_EVIDENCE.issubset(evidence)
    key = str(record.get("memory_key", ""))
    content = str(record.get("content", ""))
    conflict = key in active_memory and active_memory[key] != content

    if not key or not content:
        reasons.append("missing_key_or_content")
    if expected_hash != actual_hash:
        reasons.append("payload_hash_mismatch")
    if not verified:
        reasons.append("not_verified")
    if not scoped:
        reasons.append("scope_missing_or_global")
    if not complete_evidence:
        reasons.append("incomplete_evidence")
    if conflict:
        reasons.append("active_memory_conflict")

    integrity_ok = expected_hash == actual_hash and bool(key) and bool(content)
    clean_score = float(verified and integrity_ok) * float(independent) * float(held_out) * float(scoped) * float(not conflict)

    if not integrity_ok:
        decision = "reject"
    elif reasons:
        decision = "quarantine"
    else:
        decision = "candidate_admit"

    return {
        "decision": decision,
        "reasons": reasons,
        "clean_score": clean_score,
        "payload_sha256_actual": actual_hash,
        "payload_sha256_expected": expected_hash,
        "writes_active_memory": False,
        "promotion_allowed": False,
        "status": "candidate_hold",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--active-memory", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    record = json.loads(Path(args.input).read_text(encoding="utf-8"))
    active = json.loads(Path(args.active_memory).read_text(encoding="utf-8"))
    report = evaluate(record, active)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["decision"] == "candidate_admit" else 2


if __name__ == "__main__":
    raise SystemExit(main())
