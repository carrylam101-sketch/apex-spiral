"""Candidate-only daily-task acceptance gate.

The gate evaluates explicit verifier evidence and never changes production state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_record(record: dict[str, Any]) -> bytes:
    bounded = {
        "task_id": record.get("task_id"),
        "scope": record.get("scope"),
        "criteria": record.get("criteria"),
        "rollback": record.get("rollback"),
        "side_effects_declared": record.get("side_effects_declared"),
    }
    return json.dumps(bounded, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def record_sha256(record: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_record(record)).hexdigest()


def valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value.lower())
    )


def evaluate(record: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    scope = str(record.get("scope", ""))
    criteria = record.get("criteria", [])
    rollback = record.get("rollback", {})
    expected_hash = str(record.get("record_sha256", ""))
    actual_hash = record_sha256(record)

    bounded_scope = bool(scope) and scope != "global"
    criteria_list = isinstance(criteria, list) and bool(criteria)
    total = len(criteria) if criteria_list else 0
    passed = 0
    has_negative = False

    if not bounded_scope:
        reasons.append("scope_missing_or_global")
    if not criteria_list:
        reasons.append("criteria_missing")
    else:
        for criterion in criteria:
            if not isinstance(criterion, dict):
                reasons.append("criterion_invalid")
                continue
            if not criterion.get("id") or not criterion.get("requirement"):
                reasons.append("criterion_missing_definition")
            if not criterion.get("verifier"):
                reasons.append("criterion_missing_verifier")
            if not criterion.get("evidence_ref") or not valid_sha256(criterion.get("evidence_sha256")):
                reasons.append("criterion_evidence_invalid")
            criterion_passed = criterion.get("passed") is True and criterion.get("exit_code") == 0
            if criterion_passed:
                passed += 1
            else:
                reasons.append("criterion_failed")
            has_negative = has_negative or criterion.get("negative_case") is True

    if not has_negative:
        reasons.append("negative_case_missing")

    rollback_ready = (
        isinstance(rollback, dict)
        and bool(rollback.get("snapshot_ref"))
        and bool(rollback.get("restore_command"))
        and rollback.get("tested") is True
    )
    if not rollback_ready:
        reasons.append("rollback_not_tested")
    if record.get("side_effects_declared") is not True:
        reasons.append("side_effects_not_declared")
    if expected_hash != actual_hash:
        reasons.append("record_hash_mismatch")

    unique_reasons = list(dict.fromkeys(reasons))
    pass_rate = passed / total if total else 0.0
    candidate_pass = not unique_reasons and pass_rate == 1.0
    return {
        "decision": "candidate_pass" if candidate_pass else "hold",
        "reasons": unique_reasons,
        "criteria_total": total,
        "criteria_passed": passed,
        "criteria_pass_rate": pass_rate,
        "negative_case_present": has_negative,
        "rollback_ready": rollback_ready,
        "record_sha256_actual": actual_hash,
        "record_sha256_expected": expected_hash,
        "writes_production": False,
        "promotion_allowed": False,
        "status": "candidate_hold",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    record = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = evaluate(record)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["decision"] == "candidate_pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
