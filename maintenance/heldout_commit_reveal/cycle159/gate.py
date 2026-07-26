"""Candidate commit-reveal integrity gate for held-out evaluation.

This gate proves only that a frozen candidate and fixture set did not change after
an external commitment digest was issued. It does not prove that the optimizer
never saw the fixtures or that the evaluator is semantically independent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_manifest(candidate: Path, fixtures: list[Path]) -> dict[str, Any]:
    return {
        "candidate": {"path": str(candidate), "sha256": sha256_file(candidate)},
        "fixtures": [
            {"path": str(path), "sha256": sha256_file(path)}
            for path in sorted(fixtures, key=lambda item: str(item))
        ],
    }


def manifest_digest(manifest: dict[str, Any]) -> str:
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify(manifest: dict[str, Any], expected_commitment: str) -> dict[str, Any]:
    reasons: list[str] = []
    actual_commitment = manifest_digest(manifest)
    if actual_commitment != expected_commitment:
        reasons.append("commitment_mismatch")

    candidate_entry = manifest.get("candidate", {})
    candidate = Path(str(candidate_entry.get("path", "")))
    if not candidate.is_file() or sha256_file(candidate) != candidate_entry.get("sha256"):
        reasons.append("candidate_changed_or_missing")

    fixtures = manifest.get("fixtures")
    if not isinstance(fixtures, list) or len(fixtures) < 3:
        reasons.append("fixture_set_too_small")
    else:
        seen: set[str] = set()
        for entry in fixtures:
            path = Path(str(entry.get("path", "")))
            digest = str(entry.get("sha256", ""))
            if digest in seen:
                reasons.append("duplicate_fixture_digest")
            seen.add(digest)
            if not path.is_file() or sha256_file(path) != digest:
                reasons.append("fixture_changed_or_missing")

    decision = "candidate_verify" if not reasons else "hold"
    return {
        "decision": decision,
        "reasons": sorted(set(reasons)),
        "commitment_match": actual_commitment == expected_commitment,
        "candidate_immutable": "candidate_changed_or_missing" not in reasons,
        "fixtures_immutable": "fixture_changed_or_missing" not in reasons,
        "hiddenness_verified": False,
        "semantic_independence_verified": False,
        "promotion_allowed": False,
        "status": "candidate_hold",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--commitment", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = verify(manifest, args.commitment)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["decision"] == "candidate_verify" else 2


if __name__ == "__main__":
    raise SystemExit(main())
