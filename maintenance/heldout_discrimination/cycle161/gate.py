"""Candidate held-out discrimination gate.

A held-out suite is useful only if it separates a known-good target from a
committed negative control. This wrapper reuses the cycle160 evaluator-owned
execution gate, executes both candidates against the same frozen fixtures, and
keeps every result at candidate/hold status.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
OWNED_GATE = ROOT / "maintenance" / "heldout_owned_execution" / "cycle160" / "gate.py"
SPEC = importlib.util.spec_from_file_location("cycle160_owned_gate", OWNED_GATE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cycle160_gate_unavailable")
OWNED = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OWNED)


def evaluate_discrimination(
    target_manifest: dict[str, Any],
    target_commitment: str,
    control_manifest: dict[str, Any],
    control_commitment: str,
    interpreter: Path,
    timeout_seconds: float = 2.0,
) -> dict[str, Any]:
    reasons: list[str] = []
    target_hash = target_manifest.get("candidate", {}).get("sha256")
    control_hash = control_manifest.get("candidate", {}).get("sha256")
    if not target_hash or target_hash == control_hash:
        reasons.append("negative_control_not_distinct")

    target_fixtures = target_manifest.get("fixtures")
    control_fixtures = control_manifest.get("fixtures")
    if target_fixtures != control_fixtures:
        reasons.append("fixture_sets_differ")

    target_report = OWNED.verify_and_execute(
        target_manifest, target_commitment, interpreter, timeout_seconds
    )
    control_report = OWNED.verify_and_execute(
        control_manifest, control_commitment, interpreter, timeout_seconds
    )

    if target_report["decision"] != "candidate_verify":
        reasons.append("target_failed_heldout")
    control_count = control_report["probe_count"]
    control_pass_count = control_report["probe_pass_count"]
    control_fail_count = control_count - control_pass_count
    if control_count == 0:
        reasons.append("negative_control_not_executed")
    elif control_fail_count == 0:
        reasons.append("heldout_suite_has_no_discriminative_failure")

    target_count = target_report["probe_count"]
    target_pass_count = target_report["probe_pass_count"]
    target_rate = target_pass_count / target_count if target_count else 0.0
    control_rate = control_pass_count / control_count if control_count else 0.0
    separation = target_rate - control_rate
    if separation <= 0.0:
        reasons.append("non_positive_pass_rate_separation")

    decision = "candidate_verify" if not reasons else "hold"
    return {
        "decision": decision,
        "reasons": sorted(set(reasons)),
        "mechanism": "heldout_negative_control_discrimination",
        "target_report": target_report,
        "negative_control_report": control_report,
        "target_pass_rate": target_rate,
        "negative_control_pass_rate": control_rate,
        "pass_rate_separation": separation,
        "discriminative_failure_count": control_fail_count,
        "same_fixture_set": target_fixtures == control_fixtures,
        "promotion_allowed": False,
        "status": "candidate_hold",
    }
