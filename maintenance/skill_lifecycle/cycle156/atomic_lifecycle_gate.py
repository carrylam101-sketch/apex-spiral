"""Candidate-only gate for atomic Skill promotion and rollback readiness.

The gate emits deterministic advice. It never edits or activates a Skill.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_EVIDENCE = {"unit_tests", "held_out", "independent_eval"}


def canonical_manifest(manifest: dict[str, Any]) -> bytes:
    bounded = {
        "skill_id": manifest.get("skill_id"),
        "version": manifest.get("version"),
        "capabilities": manifest.get("capabilities"),
        "scope": manifest.get("scope"),
        "artifact_hashes": manifest.get("artifact_hashes"),
        "rollback": manifest.get("rollback"),
    }
    return json.dumps(bounded, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def manifest_sha256(manifest: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_manifest(manifest)).hexdigest()


def evaluate(manifest: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    capabilities = manifest.get("capabilities", [])
    scope = str(manifest.get("scope", ""))
    artifact_hashes = manifest.get("artifact_hashes", {})
    rollback = manifest.get("rollback", {})
    evidence = set(manifest.get("evidence_types", []))
    expected_hash = str(manifest.get("manifest_sha256", ""))
    actual_hash = manifest_sha256(manifest)

    atomic = isinstance(capabilities, list) and len(capabilities) == 1
    bounded_scope = bool(scope) and scope != "global"
    hashes_valid = (
        isinstance(artifact_hashes, dict)
        and bool(artifact_hashes)
        and all(
            isinstance(v, str)
            and len(v) == 64
            and all(ch in "0123456789abcdef" for ch in v.lower())
            for v in artifact_hashes.values()
        )
    )
    rollback_ready = (
        isinstance(rollback, dict)
        and bool(rollback.get("snapshot_ref"))
        and bool(rollback.get("restore_command"))
        and rollback.get("tested") is True
    )
    evidence_complete = REQUIRED_EVIDENCE.issubset(evidence)
    integrity_ok = expected_hash == actual_hash

    if not atomic:
        reasons.append("non_atomic_capability_set")
    if not bounded_scope:
        reasons.append("scope_missing_or_global")
    if not hashes_valid:
        reasons.append("artifact_hashes_invalid")
    if not rollback_ready:
        reasons.append("rollback_not_tested")
    if not evidence_complete:
        reasons.append("evidence_incomplete")
    if not integrity_ok:
        reasons.append("manifest_hash_mismatch")

    candidate_ready = not reasons
    return {
        "decision": "candidate_ready" if candidate_ready else "hold",
        "reasons": reasons,
        "atomic": atomic,
        "bounded_scope": bounded_scope,
        "rollback_ready": rollback_ready,
        "evidence_complete": evidence_complete,
        "manifest_sha256_actual": actual_hash,
        "manifest_sha256_expected": expected_hash,
        "writes_skill": False,
        "promotion_allowed": False,
        "status": "candidate_hold",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    manifest = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = evaluate(manifest)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["decision"] == "candidate_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
