"""Tests for separate-process, input-only held-out evaluation."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "maintenance" / "heldout_input_only" / "cycle163" / "gate.py"
SPEC = importlib.util.spec_from_file_location("heldout_input_only_gate", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_candidate(tmp_path: Path, body: str | None = None) -> Path:
    candidate = tmp_path / "candidate.py"
    candidate.write_text(
        body or "import sys\nvalue = sys.stdin.read().strip()\nprint(value.upper())\n",
        encoding="utf-8",
    )
    return candidate


def make_transcript(tmp_path: Path, candidate: Path | None = None):
    candidate = candidate or write_candidate(tmp_path)
    frozen = MODULE.freeze_candidate(candidate)
    transcript = MODULE.generate_fresh_bundle(frozen, tmp_path)
    return candidate, transcript


def test_fresh_generator_is_distinct_and_candidate_passes_input_only(tmp_path: Path) -> None:
    _, transcript = make_transcript(tmp_path)
    report = MODULE.evaluate_input_only(transcript)
    assert transcript["generator_pid"] != transcript["evaluator_pid"]
    assert transcript["generated_ns"] > transcript["candidate_frozen_ns"]
    assert report["decision"] == "candidate_verify"
    assert report["probe_count"] == 3
    assert report["probe_pass_count"] == 3
    assert report["sealed_loaded_after_execution"] is True
    assert report["promotion_allowed"] is False


def test_public_inputs_contain_no_expected_outputs(tmp_path: Path) -> None:
    _, transcript = make_transcript(tmp_path)
    public = json.loads(Path(transcript["public_path"]).read_text(encoding="utf-8"))
    assert all(set(item) == {"probe_id", "probe_type", "stdin", "custody_canary"} for item in public)
    assert all(not MODULE.FORBIDDEN_PUBLIC_FIELDS.intersection(item) for item in public)


def test_rejects_expected_field_in_public_input(tmp_path: Path) -> None:
    _, transcript = make_transcript(tmp_path)
    public_path = Path(transcript["public_path"])
    public = json.loads(public_path.read_text(encoding="utf-8"))
    public[0]["expected"] = {"stdout": "LEAK"}
    public_path.write_text(json.dumps(public, sort_keys=True) + "\n", encoding="utf-8")
    transcript["public_sha256"] = MODULE.sha256_file(public_path)
    report = MODULE.evaluate_input_only(transcript)
    assert report["decision"] == "hold"
    assert "expected_data_exposed_in_public_input" in report["reasons"]


def test_candidate_cannot_find_expected_in_argv_env_or_empty_cwd(tmp_path: Path) -> None:
    body = (
        "import os, pathlib, sys\n"
        "value = sys.stdin.read().strip()\n"
        "surface = ' '.join(sys.argv) + ' ' + ' '.join(os.environ.values())\n"
        "surface += ' ' + ' '.join(p.name for p in pathlib.Path.cwd().iterdir())\n"
        "print('LEAK' if 'sealed_expected' in surface else value.upper())\n"
    )
    _, transcript = make_transcript(tmp_path, write_candidate(tmp_path, body))
    report = MODULE.evaluate_input_only(transcript)
    assert report["decision"] == "candidate_verify"
    assert report["expected_present_in_candidate_argv_env_cwd"] is False


def test_candidate_mutation_after_freeze_fails_closed(tmp_path: Path) -> None:
    candidate, transcript = make_transcript(tmp_path)
    candidate.write_text("print('constant')\n", encoding="utf-8")
    report = MODULE.evaluate_input_only(transcript)
    assert report["decision"] == "hold"
    assert "candidate_changed_or_missing" in report["reasons"]
    assert report["probe_count"] == 0


def test_wrong_candidate_is_rejected_by_fresh_outputs(tmp_path: Path) -> None:
    candidate = write_candidate(tmp_path, "import sys\nprint(sys.stdin.read().strip().lower())\n")
    _, transcript = make_transcript(tmp_path, candidate)
    report = MODULE.evaluate_input_only(transcript)
    assert report["decision"] == "hold"
    assert report["probe_pass_count"] == 0
    assert sum(reason.startswith("probe_failed:") for reason in report["reasons"]) == 3
