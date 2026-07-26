"""Counterexample tests for the candidate daily-task acceptance gate."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "maintenance" / "daily_acceptance" / "cycle157" / "acceptance_gate.py"
SPEC = importlib.util.spec_from_file_location("daily_task_acceptance_gate", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def valid_record() -> dict:
    record = {
        "task_id": "daily.verify-json-output",
        "scope": "json-output-verification",
        "criteria": [
            {
                "id": "schema-valid",
                "requirement": "Output parses against the declared JSON schema.",
                "verifier": "python3 -m json.tool artifact.json",
                "exit_code": 0,
                "passed": True,
                "evidence_ref": "reports/artifact-json-tool.txt",
                "evidence_sha256": "a" * 64,
            },
            {
                "id": "negative-malformed-input",
                "requirement": "Malformed input is rejected without changing production state.",
                "verifier": "pytest -q tests/test_malformed_input.py",
                "exit_code": 0,
                "passed": True,
                "evidence_ref": "reports/malformed-input.txt",
                "evidence_sha256": "b" * 64,
                "negative_case": True,
            },
        ],
        "rollback": {
            "snapshot_ref": "backups/daily.verify-json-output.pre-change",
            "restore_command": "restore daily.verify-json-output.pre-change",
            "tested": True,
        },
        "side_effects_declared": True,
    }
    record["record_sha256"] = MODULE.record_sha256(record)
    return record


def test_complete_acceptance_record_is_candidate_pass_only() -> None:
    report = MODULE.evaluate(valid_record())
    assert report["decision"] == "candidate_pass"
    assert report["criteria_pass_rate"] == 1.0
    assert report["promotion_allowed"] is False
    assert report["writes_production"] is False


def test_prose_only_claim_without_verifier_is_held() -> None:
    record = valid_record()
    record["criteria"][0]["verifier"] = ""
    record["record_sha256"] = MODULE.record_sha256(record)
    report = MODULE.evaluate(record)
    assert report["decision"] == "hold"
    assert "criterion_missing_verifier" in report["reasons"]


def test_failed_criterion_blocks_acceptance() -> None:
    record = valid_record()
    record["criteria"][0]["passed"] = False
    record["criteria"][0]["exit_code"] = 1
    record["record_sha256"] = MODULE.record_sha256(record)
    report = MODULE.evaluate(record)
    assert report["decision"] == "hold"
    assert "criterion_failed" in report["reasons"]


def test_missing_negative_case_is_held() -> None:
    record = valid_record()
    record["criteria"][1].pop("negative_case")
    record["record_sha256"] = MODULE.record_sha256(record)
    report = MODULE.evaluate(record)
    assert report["decision"] == "hold"
    assert "negative_case_missing" in report["reasons"]


def test_untested_rollback_is_held() -> None:
    record = valid_record()
    record["rollback"]["tested"] = False
    record["record_sha256"] = MODULE.record_sha256(record)
    report = MODULE.evaluate(record)
    assert report["decision"] == "hold"
    assert "rollback_not_tested" in report["reasons"]


def test_post_attestation_mutation_is_held() -> None:
    attacked = copy.deepcopy(valid_record())
    attacked["scope"] = "global"
    report = MODULE.evaluate(attacked)
    assert report["decision"] == "hold"
    assert "scope_missing_or_global" in report["reasons"]
    assert "record_hash_mismatch" in report["reasons"]
