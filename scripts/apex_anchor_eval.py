#!/usr/bin/env python3
"""Deterministic external-anchor and held-out evaluator for APEX daily tasks.

This script is a read-only governance layer: it evaluates an evidence record and
writes a recommendation. It never edits skills, cron jobs, the registry, model
weights, or the source record.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "apex_anchor_eval_v1"
EVAL_VERSION = "apex_anchor_eval_v1.0.0"
ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = (ROOT / "evolution" / "reports" / "anchor_eval").resolve()
HELDOUT_FIXTURE_DIR = (ROOT / "maintenance" / "heldout_fixtures").resolve()


class ValidationError(ValueError):
    """Raised when an evidence record cannot be evaluated safely."""


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{field} must be a number")
    result = float(value)
    if not 0.0 <= result <= 1.0:
        raise ValidationError(f"{field} must be between 0 and 1")
    return result


def _require_mapping(record: dict[str, Any], field: str) -> dict[str, Any]:
    value = record.get(field)
    if not isinstance(value, dict):
        raise ValidationError(f"{field} must be an object")
    return value


def _require_nonempty_list(record: dict[str, Any], field: str) -> list[dict[str, Any]]:
    value = record.get(field)
    if not isinstance(value, list) or not value:
        raise ValidationError(f"{field} must be a non-empty list")
    if not all(isinstance(item, dict) for item in value):
        raise ValidationError(f"{field} items must be objects")
    return value


def _weighted_pass_rate(probes: list[dict[str, Any]]) -> float:
    if len(probes) < 3:
        raise ValidationError("held_out_probes must contain at least 3 probes")
    total = 0.0
    passed = 0.0
    fixture_hashes: set[str] = set()
    probe_types: set[str] = set()
    for probe in probes:
        if not probe.get("id"):
            raise ValidationError("held_out_probes.id is required")
        probe_type = probe.get("type")
        if not isinstance(probe_type, str) or not probe_type.strip():
            raise ValidationError("held_out_probes.type is required")
        probe_types.add(probe_type.strip())
        if "weight" not in probe:
            raise ValidationError("held_out_probes.weight is required")
        weight = _number(probe["weight"], "held_out_probes.weight")
        if weight <= 0.0:
            raise ValidationError("held_out_probes.weight must be greater than 0")
        if not isinstance(probe.get("passed"), bool):
            raise ValidationError("held_out_probes.passed must be boolean")
        if probe.get("hidden_from_optimizer") is not True:
            raise ValidationError("held_out_probes.hidden_from_optimizer must be true")
        fixture_ref = probe.get("fixture_ref")
        if not isinstance(fixture_ref, str) or not fixture_ref.strip():
            raise ValidationError("held_out_probes.fixture_ref is required")
        fixture_path = Path(fixture_ref)
        if not fixture_path.is_absolute():
            fixture_path = ROOT / fixture_path
        try:
            resolved_fixture = fixture_path.resolve(strict=True)
        except OSError as exc:
            raise ValidationError(f"held_out_probes.fixture_ref is unreadable: {exc}") from exc
        if HELDOUT_FIXTURE_DIR not in resolved_fixture.parents:
            raise ValidationError("held_out_probes.fixture_ref must be inside maintenance/heldout_fixtures")
        if not resolved_fixture.is_file():
            raise ValidationError("held_out_probes.fixture_ref must reference a file")
        fixture_hash = str(probe.get("fixture_hash", ""))
        if len(fixture_hash) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in fixture_hash):
            raise ValidationError("held_out_probes.fixture_hash must be a sha256 hex digest")
        normalized_hash = fixture_hash.lower()
        actual_hash = hashlib.sha256(resolved_fixture.read_bytes()).hexdigest()
        if normalized_hash != actual_hash:
            raise ValidationError("held_out_probes.fixture_hash does not match fixture bytes")
        if normalized_hash in fixture_hashes:
            raise ValidationError("held_out_probes.fixture_hash values must be unique")
        fixture_hashes.add(normalized_hash)
        total += weight
        if probe["passed"]:
            passed += weight
    if not {"counterexample", "transfer"}.issubset(probe_types):
        raise ValidationError("held_out_probes must include counterexample and transfer probe types")
    return passed / total


def _acceptance_pass(criteria: list[dict[str, Any]]) -> bool:
    required = [item for item in criteria if item.get("required", True)]
    if not required:
        raise ValidationError("acceptance_criteria must contain a required criterion")
    for item in criteria:
        if not item.get("id"):
            raise ValidationError("acceptance_criteria.id is required")
        if not isinstance(item.get("passed"), bool):
            raise ValidationError("acceptance_criteria.passed must be boolean")
        if not item.get("evidence"):
            raise ValidationError("acceptance criterion must contain evidence")
    return all(item["passed"] for item in required)


def _evidence_completeness(evidence: list[dict[str, Any]]) -> float:
    if not evidence:
        return 0.0
    verified = sum(1 for item in evidence if item.get("verified") is True and item.get("ref"))
    return verified / len(evidence)


def evaluate_record(record: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a record and return a non-mutating promotion recommendation."""
    if not isinstance(record, dict):
        raise ValidationError("record must be an object")
    if record.get("schema_version") != SCHEMA_VERSION:
        raise ValidationError(f"schema_version must be {SCHEMA_VERSION}")
    task_id = record.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValidationError("task_id must be a non-empty string")

    source = _require_mapping(record, "source")
    for field in ("type", "title", "retrieved_at", "content_hash"):
        if not source.get(field):
            raise ValidationError(f"source.{field} is required")
    content_hash = str(source["content_hash"])
    if len(content_hash) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in content_hash):
        raise ValidationError("source.content_hash must be a sha256 hex digest")

    anchor = _require_mapping(record, "anchor")
    if anchor.get("not_directly_trusted") is not True:
        raise ValidationError("anchor.not_directly_trusted must be true")
    for field in ("source_quality", "mechanism_clarity", "mapping_fit", "risk"):
        if field not in anchor:
            raise ValidationError(f"anchor.{field} is required")
    source_quality = _number(anchor["source_quality"], "anchor.source_quality")
    mechanism_clarity = _number(anchor["mechanism_clarity"], "anchor.mechanism_clarity")
    mapping_fit = _number(anchor["mapping_fit"], "anchor.mapping_fit")
    risk = _number(anchor["risk"], "anchor.risk")
    anchor_score = source_quality * mechanism_clarity * mapping_fit * (1.0 - risk)

    criteria = _require_nonempty_list(record, "acceptance_criteria")
    acceptance_pass = _acceptance_pass(criteria)
    heldout = _require_nonempty_list(record, "held_out_probes")
    heldout_pass_rate = _weighted_pass_rate(heldout)
    for field in ("task_quality_delta", "regression_safety", "critical_regression"):
        if field not in record:
            raise ValidationError(f"{field} is required")
    task_quality_delta = _number(record["task_quality_delta"], "task_quality_delta")
    regression_safety = _number(record["regression_safety"], "regression_safety")
    critical_regression = record["critical_regression"]
    if not isinstance(critical_regression, bool):
        raise ValidationError("critical_regression must be boolean")

    evidence = _require_nonempty_list(record, "evidence")
    for item in evidence:
        if not item.get("kind"):
            raise ValidationError("evidence.kind is required")
        if not item.get("ref"):
            raise ValidationError("evidence.ref is required")
        if not isinstance(item.get("verified"), bool):
            raise ValidationError("evidence.verified must be boolean")
    evidence_completeness = _evidence_completeness(evidence)

    gates = _require_mapping(record, "gates")
    harness_decision = gates.get("harness_decision")
    if harness_decision not in {"allow", "warn", "block"}:
        raise ValidationError("gates.harness_decision must be allow, warn, or block")
    if not isinstance(gates.get("V_H"), bool):
        raise ValidationError("gates.V_H must be boolean")

    promotion = _require_mapping(record, "promotion")
    current_state = promotion.get("current_state")
    if current_state not in {"draft", "candidate", "active", "held", "rolled_back"}:
        raise ValidationError("promotion.current_state is invalid")
    if "rollback_ref" not in promotion:
        raise ValidationError("promotion.rollback_ref is required")
    rollback_ref = promotion.get("rollback_ref")

    final_score = (
        0.25 * anchor_score
        + 0.30 * heldout_pass_rate
        + 0.20 * task_quality_delta
        + 0.15 * evidence_completeness
        + 0.10 * regression_safety
        - 0.20 * risk
    )
    final_score = max(0.0, min(1.0, final_score))

    checks = {
        "acceptance_pass": acceptance_pass,
        "heldout_pass_rate_at_least_0.80": heldout_pass_rate >= 0.80,
        "evidence_completeness_at_least_0.75": evidence_completeness >= 0.75,
        "risk_at_most_0.20": risk <= 0.20,
        "final_score_at_least_0.78": final_score >= 0.78,
        "harness_not_blocked": harness_decision != "block",
        "V_H_true": gates["V_H"] is True,
        "no_critical_regression": not critical_regression,
    }
    failed_gates: list[str] = []
    if not checks["acceptance_pass"]:
        failed_gates.append("acceptance_failed")
    if not checks["heldout_pass_rate_at_least_0.80"]:
        failed_gates.append("heldout_pass_rate_below_0.80")
    if not checks["evidence_completeness_at_least_0.75"]:
        failed_gates.append("evidence_completeness_below_0.75")
    if not checks["risk_at_most_0.20"]:
        failed_gates.append("risk_above_0.20")
    if not checks["final_score_at_least_0.78"]:
        failed_gates.append("final_score_below_0.78")
    if not checks["harness_not_blocked"]:
        failed_gates.append("harness_blocked")
    if not checks["V_H_true"]:
        failed_gates.append("V_H_false")
    if not checks["no_critical_regression"]:
        failed_gates.append("critical_regression")

    if current_state == "active" and (
        critical_regression
        or heldout_pass_rate < 0.60
        or not gates["V_H"]
        or harness_decision == "block"
    ):
        recommendation = "rollback"
    elif harness_decision == "block" or not gates["V_H"] or critical_regression or not acceptance_pass:
        recommendation = "hold"
    elif all(checks.values()):
        recommendation = "promote"
    elif final_score >= 0.65 and heldout_pass_rate >= 0.65 and risk <= 0.30:
        recommendation = "candidate"
    else:
        recommendation = "hold"

    return {
        "schema_version": SCHEMA_VERSION,
        "eval_version": EVAL_VERSION,
        "task_id": task_id,
        "evaluator_mode": "deterministic_script",
        "independence_claim": "not self-proving; separation must be supported by evidence outside this report",
        "scores": {
            "anchor_score": round(anchor_score, 6),
            "heldout_pass_rate": round(heldout_pass_rate, 6),
            "task_quality_delta": round(task_quality_delta, 6),
            "evidence_completeness": round(evidence_completeness, 6),
            "regression_safety": round(regression_safety, 6),
            "risk": round(risk, 6),
            "final_score": round(final_score, 6),
        },
        "checks": checks,
        "failed_gates": failed_gates,
        "recommendation": recommendation,
        "current_state": current_state,
        "rollback_ref": rollback_ref,
        "mutation_applied": False,
        "boundary": "governance recommendation only; no model-weight training or automatic skill/cron/registry mutation",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        record = json.loads(args.input.read_text(encoding="utf-8"))
        report = evaluate_record(record)
        if args.output:
            output = args.output.resolve()
            if output == REPORT_DIR or REPORT_DIR not in output.parents:
                raise ValidationError(f"output must be inside {REPORT_DIR}")
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
