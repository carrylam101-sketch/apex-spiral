"""Tests for evaluator-owned held-out probe execution."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "maintenance" / "heldout_owned_execution" / "cycle160" / "gate.py"
SPEC = importlib.util.spec_from_file_location("heldout_owned_execution_gate", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def make_candidate(tmp_path: Path) -> Path:
    candidate = tmp_path / "candidate.py"
    candidate.write_text(
        "import sys\nvalue = sys.stdin.read().strip()\nprint(value.upper())\n",
        encoding="utf-8",
    )
    return candidate


def write_fixture(tmp_path: Path, probe_id: str, probe_type: str, stdin: str, stdout: str, **extra) -> Path:
    fixture = tmp_path / f"{probe_id}.json"
    payload = {
        "probe_id": probe_id,
        "probe_type": probe_type,
        "stdin": stdin,
        "expected": {"exit_code": 0, "stdout": stdout},
    }
    payload.update(extra)
    fixture.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return fixture


def make_artifacts(tmp_path: Path):
    candidate = make_candidate(tmp_path)
    fixtures = [
        write_fixture(tmp_path, "p1", "factual", "alpha\n", "ALPHA\n"),
        write_fixture(tmp_path, "p2", "counterexample", "MiXeD\n", "MIXED\n"),
        write_fixture(tmp_path, "p3", "transfer", "beta-2\n", "BETA-2\n"),
    ]
    manifest = MODULE.canonical_manifest(candidate, fixtures)
    commitment = MODULE.manifest_digest(manifest)
    return candidate, fixtures, manifest, commitment


def evaluate(manifest, commitment):
    return MODULE.verify_and_execute(manifest, commitment, Path(sys.executable), 2.0)


def test_evaluator_executes_all_probes_and_computes_outcomes(tmp_path: Path) -> None:
    _, _, manifest, commitment = make_artifacts(tmp_path)
    report = evaluate(manifest, commitment)
    assert report["decision"] == "candidate_verify"
    assert report["evaluator_owned_execution"] is True
    assert report["optimizer_supplied_pass_labels_accepted"] is False
    assert report["probe_count"] == 3
    assert report["probe_pass_count"] == 3
    assert report["promotion_allowed"] is False


def test_optimizer_supplied_pass_label_is_rejected(tmp_path: Path) -> None:
    candidate = make_candidate(tmp_path)
    fixtures = [
        write_fixture(tmp_path, "p1", "factual", "a\n", "A\n", passed=True),
        write_fixture(tmp_path, "p2", "counterexample", "b\n", "B\n"),
        write_fixture(tmp_path, "p3", "transfer", "c\n", "C\n"),
    ]
    manifest = MODULE.canonical_manifest(candidate, fixtures)
    report = evaluate(manifest, MODULE.manifest_digest(manifest))
    assert report["decision"] == "hold"
    assert "optimizer_supplied_result_field" in report["reasons"]
    assert report["probe_count"] == 0


def test_wrong_expected_output_is_observed_as_failure(tmp_path: Path) -> None:
    _, fixtures, _, _ = make_artifacts(tmp_path)
    payload = json.loads(fixtures[2].read_text(encoding="utf-8"))
    payload["expected"]["stdout"] = "WRONG\n"
    fixtures[2].write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    candidate = tmp_path / "candidate.py"
    manifest = MODULE.canonical_manifest(candidate, fixtures)
    report = evaluate(manifest, MODULE.manifest_digest(manifest))
    assert report["decision"] == "hold"
    assert "probe_failed:p3" in report["reasons"]
    assert report["probe_pass_count"] == 2


def test_candidate_mutation_after_commitment_fails_before_execution(tmp_path: Path) -> None:
    candidate, _, manifest, commitment = make_artifacts(tmp_path)
    candidate.write_text("print('constant')\n", encoding="utf-8")
    report = evaluate(manifest, commitment)
    assert report["decision"] == "hold"
    assert "candidate_changed_or_missing" in report["reasons"]
    assert report["probe_count"] == 0


def test_fixture_mutation_after_commitment_fails_before_execution(tmp_path: Path) -> None:
    _, fixtures, manifest, commitment = make_artifacts(tmp_path)
    fixtures[0].write_text("{}\n", encoding="utf-8")
    report = evaluate(manifest, commitment)
    assert report["decision"] == "hold"
    assert "fixture_changed_or_missing" in report["reasons"]
    assert report["probe_count"] == 0
