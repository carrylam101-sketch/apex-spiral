"""Behavior tests for the deterministic APEX external-anchor evaluator."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "apex_anchor_eval.py"
REPORT_DIR = ROOT / "evolution" / "reports" / "anchor_eval"
FIXTURE_DIR = ROOT / "maintenance" / "heldout_fixtures"


def fixture_probe(probe_id: str, probe_type: str, payload: str) -> dict:
    path = FIXTURE_DIR / f"pytest-{probe_id}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return {
        "id": probe_id,
        "type": probe_type,
        "weight": 1.0,
        "passed": True,
        "hidden_from_optimizer": True,
        "fixture_ref": str(path.relative_to(ROOT)),
        "fixture_hash": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def load_module():
    spec = importlib.util.spec_from_file_location("apex_anchor_eval", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_record() -> dict:
    return {
        "schema_version": "apex_anchor_eval_v1",
        "task_id": "task-001",
        "source": {
            "type": "wechat_article",
            "title": "Harness evolution notes",
            "url": "https://example.invalid/article",
            "retrieved_at": "2026-07-14T15:00:00Z",
            "content_hash": "a" * 64,
        },
        "anchor": {
            "not_directly_trusted": True,
            "source_quality": 0.75,
            "mechanism_clarity": 0.9,
            "mapping_fit": 0.9,
            "risk": 0.1,
        },
        "acceptance_criteria": [
            {"id": "a1", "required": True, "passed": True, "evidence": "pytest"},
            {"id": "a2", "required": True, "passed": True, "evidence": "readback"},
        ],
        "held_out_probes": [
            fixture_probe("h1", "factual_fidelity", "factual fixture\n"),
            fixture_probe("h2", "counterexample", "counterexample fixture\n"),
            fixture_probe("h3", "transfer", "transfer fixture\n"),
            fixture_probe("h4", "regression", "regression fixture\n"),
        ],
        "task_quality_delta": 0.9,
        "regression_safety": 1.0,
        "critical_regression": False,
        "evidence": [
            {"kind": "test", "ref": "pytest", "verified": True},
            {"kind": "file", "ref": "report.json", "verified": True},
            {"kind": "gate", "ref": "indicator", "verified": True},
            {"kind": "hash", "ref": "sha256", "verified": True},
        ],
        "gates": {"harness_decision": "allow", "V_H": True},
        "promotion": {"current_state": "candidate", "rollback_ref": "v0"},
    }


def test_promote_requires_external_anchor_and_all_hard_gates():
    module = load_module()
    report = module.evaluate_record(valid_record())
    assert report["recommendation"] == "promote"
    assert report["evaluator_mode"] == "deterministic_script"
    assert report["scores"]["heldout_pass_rate"] == pytest.approx(1.0)
    assert report["scores"]["evidence_completeness"] == pytest.approx(1.0)
    assert report["mutation_applied"] is False


def test_evaluation_is_deterministic_for_same_record():
    module = load_module()
    assert module.evaluate_record(valid_record()) == module.evaluate_record(valid_record())


def test_missing_verified_evidence_cannot_promote():
    module = load_module()
    record = valid_record()
    record["evidence"] = [{"kind": "claim", "ref": "self-report", "verified": False}]
    report = module.evaluate_record(record)
    assert report["recommendation"] != "promote"
    assert "evidence_completeness_below_0.75" in report["failed_gates"]


def test_missing_evidence_field_is_rejected():
    module = load_module()
    record = valid_record()
    record.pop("evidence")
    with pytest.raises(module.ValidationError, match="evidence"):
        module.evaluate_record(record)


def test_malformed_evidence_item_is_rejected():
    module = load_module()
    record = valid_record()
    record["evidence"] = [{"kind": "test", "verified": True}]
    with pytest.raises(module.ValidationError, match="evidence.ref"):
        module.evaluate_record(record)


def test_harness_block_forces_hold_even_with_high_scores():
    module = load_module()
    record = valid_record()
    record["gates"]["harness_decision"] = "block"
    report = module.evaluate_record(record)
    assert report["recommendation"] == "hold"
    assert "harness_blocked" in report["failed_gates"]


def test_active_harness_block_recommends_rollback():
    module = load_module()
    record = valid_record()
    record["promotion"]["current_state"] = "active"
    record["gates"]["harness_decision"] = "block"
    assert module.evaluate_record(record)["recommendation"] == "rollback"


def test_active_artifact_with_critical_regression_recommends_rollback():
    module = load_module()
    record = valid_record()
    record["promotion"]["current_state"] = "active"
    record["critical_regression"] = True
    report = module.evaluate_record(record)
    assert report["recommendation"] == "rollback"
    assert report["rollback_ref"] == "v0"


def test_v_h_false_prevents_promotion():
    module = load_module()
    record = valid_record()
    record["gates"]["V_H"] = False
    assert module.evaluate_record(record)["recommendation"] == "hold"


def test_acceptance_failure_prevents_promotion():
    module = load_module()
    record = valid_record()
    record["acceptance_criteria"][0]["passed"] = False
    assert module.evaluate_record(record)["recommendation"] == "hold"


def test_untrusted_source_marker_is_mandatory():
    module = load_module()
    record = valid_record()
    record["anchor"]["not_directly_trusted"] = False
    with pytest.raises(module.ValidationError, match="not_directly_trusted"):
        module.evaluate_record(record)


def test_empty_heldout_set_is_rejected():
    module = load_module()
    record = valid_record()
    record["held_out_probes"] = []
    with pytest.raises(module.ValidationError, match="held_out_probes"):
        module.evaluate_record(record)


def test_probe_must_be_marked_hidden_and_hashed():
    module = load_module()
    record = valid_record()
    record["held_out_probes"][0]["hidden_from_optimizer"] = False
    with pytest.raises(module.ValidationError, match="hidden_from_optimizer"):
        module.evaluate_record(record)


def test_probe_requires_id_and_valid_fixture_hash():
    module = load_module()
    record = valid_record()
    record["held_out_probes"][0].pop("id")
    with pytest.raises(module.ValidationError, match="held_out_probes.id"):
        module.evaluate_record(record)

    record = valid_record()
    record["held_out_probes"][0]["fixture_hash"] = "not-a-sha256"
    with pytest.raises(module.ValidationError, match="fixture_hash"):
        module.evaluate_record(record)


def test_probe_hash_must_match_fixture_bytes():
    module = load_module()
    record = valid_record()
    record["held_out_probes"][0]["fixture_hash"] = "0" * 64
    with pytest.raises(module.ValidationError, match="does not match fixture bytes"):
        module.evaluate_record(record)


def test_probe_fixture_must_be_inside_sealed_directory(tmp_path):
    module = load_module()
    record = valid_record()
    outside = tmp_path / "visible-to-optimizer.txt"
    outside.write_text("not sealed", encoding="utf-8")
    record["held_out_probes"][0]["fixture_ref"] = str(outside)
    record["held_out_probes"][0]["fixture_hash"] = hashlib.sha256(outside.read_bytes()).hexdigest()
    with pytest.raises(module.ValidationError, match="maintenance/heldout_fixtures"):
        module.evaluate_record(record)


def test_probe_fixture_ref_is_required():
    module = load_module()
    record = valid_record()
    record["held_out_probes"][0].pop("fixture_ref")
    with pytest.raises(module.ValidationError, match="fixture_ref"):
        module.evaluate_record(record)


def test_heldout_set_requires_three_unique_fixtures():
    module = load_module()
    record = valid_record()
    record["held_out_probes"] = record["held_out_probes"][:2]
    with pytest.raises(module.ValidationError, match="at least 3 probes"):
        module.evaluate_record(record)

    record = valid_record()
    record["held_out_probes"][1]["fixture_ref"] = record["held_out_probes"][0]["fixture_ref"]
    record["held_out_probes"][1]["fixture_hash"] = record["held_out_probes"][0]["fixture_hash"]
    with pytest.raises(module.ValidationError, match="fixture_hash values must be unique"):
        module.evaluate_record(record)


def test_heldout_set_requires_counterexample_and_transfer_types():
    module = load_module()
    record = valid_record()
    for probe in record["held_out_probes"]:
        probe["type"] = "regression"
    with pytest.raises(module.ValidationError, match="counterexample and transfer"):
        module.evaluate_record(record)


def test_cli_writes_report_without_mutating_source(tmp_path):
    import subprocess

    source = tmp_path / "pytest-input.json"
    output = REPORT_DIR / "pytest-output.json"
    source.write_text(json.dumps(valid_record()), encoding="utf-8")
    before = source.read_bytes()
    try:
        completed = subprocess.run(
            ["python3", str(SCRIPT), "--input", str(source), "--output", str(output)],
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        assert source.read_bytes() == before
        report = json.loads(output.read_text(encoding="utf-8"))
        assert report["task_id"] == "task-001"
        assert report["mutation_applied"] is False
    finally:
        source.unlink(missing_ok=True)
        output.unlink(missing_ok=True)


def test_cli_rejects_output_outside_report_directory(tmp_path):
    import subprocess

    source = tmp_path / "pytest-input.json"
    source.write_text(json.dumps(valid_record()), encoding="utf-8")
    forbidden = tmp_path / "registry.json"
    try:
        completed = subprocess.run(
            ["python3", str(SCRIPT), "--input", str(source), "--output", str(forbidden)],
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 2
        assert not forbidden.exists()
        assert "output must be inside" in completed.stdout
    finally:
        source.unlink(missing_ok=True)


def test_cli_rejects_symlink_escape_from_report_directory(tmp_path):
    import os
    import subprocess

    source = tmp_path / "pytest-input.json"
    source.write_text(json.dumps(valid_record()), encoding="utf-8")
    link = REPORT_DIR / "pytest-escape-link"
    forbidden = tmp_path / "escaped.json"
    try:
        os.symlink(tmp_path, link)
        completed = subprocess.run(
            ["python3", str(SCRIPT), "--input", str(source), "--output", str(link / forbidden.name)],
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 2
        assert not forbidden.exists()
        assert "output must be inside" in completed.stdout
    finally:
        source.unlink(missing_ok=True)
        link.unlink(missing_ok=True)
