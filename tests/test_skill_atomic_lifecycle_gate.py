"""Counterexample tests for the candidate atomic Skill lifecycle gate."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "maintenance" / "skill_lifecycle" / "cycle156" / "atomic_lifecycle_gate.py"
SPEC = importlib.util.spec_from_file_location("atomic_lifecycle_gate", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def valid_manifest() -> dict:
    manifest = {
        "skill_id": "candidate.atomic-json-validator",
        "version": "0.0.1-candidate",
        "capabilities": ["validate-one-json-contract"],
        "scope": "json-contract-validation",
        "artifact_hashes": {"candidate.py": "a" * 64, "test.py": "b" * 64},
        "rollback": {
            "snapshot_ref": "backup/candidate.atomic-json-validator-0.0.0",
            "restore_command": "restore candidate.atomic-json-validator 0.0.0",
            "tested": True,
        },
        "evidence_types": ["unit_tests", "held_out", "independent_eval"],
    }
    manifest["manifest_sha256"] = MODULE.manifest_sha256(manifest)
    return manifest


def test_atomic_bounded_candidate_is_advisory_only() -> None:
    report = MODULE.evaluate(valid_manifest())
    assert report["decision"] == "candidate_ready"
    assert report["atomic"] is True
    assert report["rollback_ready"] is True
    assert report["promotion_allowed"] is False
    assert report["writes_skill"] is False


def test_two_capabilities_are_held_as_non_atomic() -> None:
    manifest = valid_manifest()
    manifest["capabilities"].append("also-edit-yaml")
    manifest["manifest_sha256"] = MODULE.manifest_sha256(manifest)
    report = MODULE.evaluate(manifest)
    assert report["decision"] == "hold"
    assert "non_atomic_capability_set" in report["reasons"]


def test_untested_rollback_is_held() -> None:
    manifest = valid_manifest()
    manifest["rollback"]["tested"] = False
    manifest["manifest_sha256"] = MODULE.manifest_sha256(manifest)
    report = MODULE.evaluate(manifest)
    assert report["decision"] == "hold"
    assert "rollback_not_tested" in report["reasons"]


def test_non_hex_artifact_hash_is_held() -> None:
    manifest = valid_manifest()
    manifest["artifact_hashes"]["candidate.py"] = "z" * 64
    manifest["manifest_sha256"] = MODULE.manifest_sha256(manifest)
    report = MODULE.evaluate(manifest)
    assert report["decision"] == "hold"
    assert "artifact_hashes_invalid" in report["reasons"]


def test_missing_independent_or_heldout_evidence_is_held() -> None:
    manifest = valid_manifest()
    manifest["evidence_types"] = ["unit_tests"]
    report = MODULE.evaluate(manifest)
    assert report["decision"] == "hold"
    assert "evidence_incomplete" in report["reasons"]


def test_post_attestation_mutation_is_held() -> None:
    manifest = valid_manifest()
    attacked = copy.deepcopy(manifest)
    attacked["scope"] = "global"
    report = MODULE.evaluate(attacked)
    assert report["decision"] == "hold"
    assert "scope_missing_or_global" in report["reasons"]
    assert "manifest_hash_mismatch" in report["reasons"]
