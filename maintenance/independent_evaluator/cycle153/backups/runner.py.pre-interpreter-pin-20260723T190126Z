#!/usr/bin/env python3
"""Candidate process-boundary runner for the deterministic APEX evaluator.

This runner only attests OS-process separation, evaluator identity, timeout use,
and source-input immutability. It does not claim semantic or organizational
independence and never authorizes promotion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EVALUATOR = ROOT / "scripts" / "apex_anchor_eval.py"
ALLOWED_ENV = ("HOME", "LANG", "LC_ALL", "PATH", "PYTHONPATH")
IDENTITY_FILE = Path(__file__).with_name("evaluator_identity.json")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_expected_identity(path: Path) -> dict[str, str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    expected_path = raw.get("evaluator_path")
    expected_sha256 = raw.get("evaluator_sha256")
    if not isinstance(expected_path, str) or not expected_path:
        raise ValueError("identity evaluator_path must be a non-empty string")
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise ValueError("identity evaluator_sha256 must be a 64-character digest")
    return {"evaluator_path": expected_path, "evaluator_sha256": expected_sha256}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--evaluator", type=Path, default=DEFAULT_EVALUATOR)
    parser.add_argument("--identity-file", type=Path, default=IDENTITY_FILE)
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    args = parser.parse_args()

    source = args.input.resolve(strict=True)
    evaluator = args.evaluator.resolve(strict=True)
    before = sha256(source)
    expected_identity = load_expected_identity(args.identity_file.resolve(strict=True))
    evaluator_digest = sha256(evaluator)
    identity_match = (
        str(evaluator) == expected_identity["evaluator_path"]
        and evaluator_digest == expected_identity["evaluator_sha256"]
    )
    if not identity_match:
        write_report(
            args.output,
            {
                "schema_version": "apex_independent_evaluator_candidate_v1",
                "independence_level": "process_isolated_candidate",
                "semantic_independence_verified": False,
                "organizational_independence_verified": False,
                "promotion_allowed": False,
                "identity_pinned": True,
                "identity_match": False,
                "expected_evaluator_path": expected_identity["evaluator_path"],
                "expected_evaluator_sha256": expected_identity["evaluator_sha256"],
                "evaluator_path": str(evaluator),
                "evaluator_sha256": evaluator_digest,
                "input_path": str(source),
                "input_sha256_before": before,
                "input_sha256_after": before,
                "input_unchanged": True,
                "mutation_applied": False,
                "failure_mode": "evaluator_identity_mismatch",
                "boundary": "identity pinning plus process separation is necessary but not sufficient for evaluator independence",
            },
        )
        return 2
    child_env = {key: os.environ[key] for key in ALLOWED_ENV if key in os.environ}
    command = [sys.executable, str(evaluator), "--input", str(source)]
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env=child_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    child_pid = process.pid
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=args.timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        stdout, stderr = process.communicate()

    after = sha256(source)
    report: dict[str, Any] = {
        "schema_version": "apex_independent_evaluator_candidate_v1",
        "independence_level": "process_isolated_candidate",
        "semantic_independence_verified": False,
        "organizational_independence_verified": False,
        "promotion_allowed": False,
        "process_boundary": child_pid != os.getpid(),
        "runner_pid": os.getpid(),
        "child_pid": child_pid,
        "timeout_enforced": args.timeout_seconds > 0,
        "timed_out": timed_out,
        "environment_allowlist": set(child_env).issubset(ALLOWED_ENV),
        "environment_keys": sorted(child_env),
        "identity_pinned": True,
        "identity_match": True,
        "expected_evaluator_path": expected_identity["evaluator_path"],
        "expected_evaluator_sha256": expected_identity["evaluator_sha256"],
        "evaluator_path": str(evaluator),
        "evaluator_sha256": evaluator_digest,
        "input_path": str(source),
        "input_sha256_before": before,
        "input_sha256_after": after,
        "input_unchanged": before == after,
        "child_exit_code": process.returncode,
        "mutation_applied": False,
        "boundary": "process separation is necessary but not sufficient for an independent evaluator",
    }

    exit_code = 0
    if timed_out:
        report["failure_mode"] = "child_evaluator_timeout"
        exit_code = 2
    elif process.returncode != 0:
        report["failure_mode"] = "child_evaluator_failed"
        report["child_stderr"] = stderr.strip()[:1000]
        exit_code = 2
    elif before != after:
        report["failure_mode"] = "source_input_mutated"
        exit_code = 2
    else:
        try:
            child_report = json.loads(stdout)
            report["recommendation"] = child_report["recommendation"]
            report["child_eval_version"] = child_report.get("eval_version")
            report["child_independence_claim"] = child_report.get("independence_claim")
        except (json.JSONDecodeError, KeyError) as exc:
            report["failure_mode"] = "invalid_child_report"
            report["child_stderr"] = f"{type(exc).__name__}: {exc}"
            exit_code = 2

    write_report(args.output, report)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
