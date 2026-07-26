"""Candidate gate where the evaluator executes held-out probes itself.

The optimizer may provide a frozen candidate and committed fixture files, but it
may not provide pass/fail labels. This candidate gate computes outcomes from
subprocess observations. It proves neither pre-commit secrecy nor semantic or
organizational evaluator independence, so it never authorizes promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

ALLOWED_ENV = ("LANG", "LC_ALL", "PATH")
FORBIDDEN_RESULT_FIELDS = {"passed", "pass", "result", "actual", "score"}


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


def _load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(fixture, dict):
        raise ValueError("fixture_not_object")
    if FORBIDDEN_RESULT_FIELDS.intersection(fixture):
        raise ValueError("optimizer_supplied_result_field")
    if not isinstance(fixture.get("probe_id"), str) or not fixture["probe_id"]:
        raise ValueError("probe_id_missing")
    if fixture.get("probe_type") not in {"counterexample", "transfer", "factual"}:
        raise ValueError("probe_type_invalid")
    if not isinstance(fixture.get("stdin"), str):
        raise ValueError("stdin_invalid")
    expected = fixture.get("expected")
    if not isinstance(expected, dict):
        raise ValueError("expected_missing")
    if set(expected) != {"exit_code", "stdout"}:
        raise ValueError("expected_schema_invalid")
    if isinstance(expected["exit_code"], bool) or not isinstance(expected["exit_code"], int):
        raise ValueError("expected_exit_code_invalid")
    if not isinstance(expected["stdout"], str):
        raise ValueError("expected_stdout_invalid")
    return fixture


def verify_and_execute(
    manifest: dict[str, Any],
    expected_commitment: str,
    interpreter: Path,
    timeout_seconds: float = 2.0,
) -> dict[str, Any]:
    reasons: list[str] = []
    observations: list[dict[str, Any]] = []
    actual_commitment = manifest_digest(manifest)
    if actual_commitment != expected_commitment:
        reasons.append("commitment_mismatch")
    if timeout_seconds <= 0:
        reasons.append("timeout_invalid")

    candidate_entry = manifest.get("candidate", {})
    candidate = Path(str(candidate_entry.get("path", "")))
    candidate_ok = candidate.is_file() and sha256_file(candidate) == candidate_entry.get("sha256")
    if not candidate_ok:
        reasons.append("candidate_changed_or_missing")

    fixture_entries = manifest.get("fixtures")
    fixtures: list[tuple[Path, dict[str, Any]]] = []
    fixture_hashes: set[str] = set()
    probe_ids: set[str] = set()
    probe_types: set[str] = set()
    if not isinstance(fixture_entries, list) or len(fixture_entries) < 3:
        reasons.append("fixture_set_too_small")
    else:
        for entry in fixture_entries:
            path = Path(str(entry.get("path", "")))
            digest = str(entry.get("sha256", ""))
            if digest in fixture_hashes:
                reasons.append("duplicate_fixture_digest")
            fixture_hashes.add(digest)
            if not path.is_file() or sha256_file(path) != digest:
                reasons.append("fixture_changed_or_missing")
                continue
            try:
                fixture = _load_fixture(path)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                reasons.append(str(exc))
                continue
            if fixture["probe_id"] in probe_ids:
                reasons.append("duplicate_probe_id")
            probe_ids.add(fixture["probe_id"])
            probe_types.add(fixture["probe_type"])
            fixtures.append((path, fixture))
    if fixtures and not {"counterexample", "transfer"}.issubset(probe_types):
        reasons.append("required_probe_types_missing")

    interpreter_ok = interpreter.is_file()
    if not interpreter_ok:
        reasons.append("interpreter_missing")
    if reasons:
        return _report(reasons, observations, actual_commitment == expected_commitment)

    child_env = {key: os.environ[key] for key in ALLOWED_ENV if key in os.environ}
    for path, fixture in fixtures:
        expected = fixture["expected"]
        try:
            completed = subprocess.run(
                [str(interpreter), str(candidate)],
                input=fixture["stdin"],
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                env=child_env,
                check=False,
            )
            passed = completed.returncode == expected["exit_code"] and completed.stdout == expected["stdout"]
            observations.append(
                {
                    "probe_id": fixture["probe_id"],
                    "probe_type": fixture["probe_type"],
                    "fixture_sha256": sha256_file(path),
                    "observed_exit_code": completed.returncode,
                    "observed_stdout_sha256": hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest(),
                    "passed": passed,
                    "timed_out": False,
                }
            )
            if not passed:
                reasons.append(f"probe_failed:{fixture['probe_id']}")
        except subprocess.TimeoutExpired:
            observations.append(
                {
                    "probe_id": fixture["probe_id"],
                    "probe_type": fixture["probe_type"],
                    "fixture_sha256": sha256_file(path),
                    "passed": False,
                    "timed_out": True,
                }
            )
            reasons.append(f"probe_timeout:{fixture['probe_id']}")
    return _report(reasons, observations, True)


def _report(reasons: list[str], observations: list[dict[str, Any]], commitment_match: bool) -> dict[str, Any]:
    decision = "candidate_verify" if not reasons else "hold"
    return {
        "decision": decision,
        "reasons": sorted(set(reasons)),
        "commitment_match": commitment_match,
        "evaluator_owned_execution": True,
        "optimizer_supplied_pass_labels_accepted": False,
        "probe_count": len(observations),
        "probe_pass_count": sum(1 for item in observations if item.get("passed") is True),
        "observations": observations,
        "hiddenness_verified": False,
        "semantic_independence_verified": False,
        "organizational_independence_verified": False,
        "promotion_allowed": False,
        "status": "candidate_hold",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--commitment", required=True)
    parser.add_argument("--interpreter", required=True, type=Path)
    parser.add_argument("--timeout-seconds", type=float, default=2.0)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = verify_and_execute(manifest, args.commitment, args.interpreter, args.timeout_seconds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["decision"] == "candidate_verify" else 2


if __name__ == "__main__":
    raise SystemExit(main())
