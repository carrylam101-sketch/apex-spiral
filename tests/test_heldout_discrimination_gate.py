"""Tests for held-out negative-control discrimination."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "maintenance" / "heldout_discrimination" / "cycle161" / "gate.py"
SPEC = importlib.util.spec_from_file_location("heldout_discrimination_gate", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_candidate(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def write_fixture(path: Path, probe_id: str, probe_type: str, stdin: str, stdout: str) -> Path:
    payload = {
        "probe_id": probe_id,
        "probe_type": probe_type,
        "stdin": stdin,
        "expected": {"exit_code": 0, "stdout": stdout},
    }
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def make_case(tmp_path: Path, control_body: str):
    target = write_candidate(
        tmp_path / "target.py",
        "import sys\nprint(sys.stdin.read().strip().upper())\n",
    )
    control = write_candidate(tmp_path / "control.py", control_body)
    fixtures = [
        write_fixture(tmp_path / "p1.json", "p1", "factual", "alpha\n", "ALPHA\n"),
        write_fixture(tmp_path / "p2.json", "p2", "counterexample", "MiXeD\n", "MIXED\n"),
        write_fixture(tmp_path / "p3.json", "p3", "transfer", "beta-2\n", "BETA-2\n"),
    ]
    target_manifest = MODULE.OWNED.canonical_manifest(target, fixtures)
    control_manifest = MODULE.OWNED.canonical_manifest(control, fixtures)
    return target_manifest, control_manifest


def evaluate(target_manifest, control_manifest):
    return MODULE.evaluate_discrimination(
        target_manifest,
        MODULE.OWNED.manifest_digest(target_manifest),
        control_manifest,
        MODULE.OWNED.manifest_digest(control_manifest),
        Path(sys.executable),
    )


def test_rejects_known_bad_negative_control_and_measures_separation(tmp_path: Path) -> None:
    target, control = make_case(
        tmp_path,
        "import sys\nprint(sys.stdin.read().strip().lower())\n",
    )
    report = evaluate(target, control)
    assert report["decision"] == "candidate_verify"
    assert report["target_pass_rate"] == 1.0
    assert report["negative_control_pass_rate"] == 0.0
    assert report["pass_rate_separation"] == 1.0
    assert report["discriminative_failure_count"] == 3
    assert report["promotion_allowed"] is False


def test_holds_when_control_also_passes_all_probes(tmp_path: Path) -> None:
    target, control = make_case(
        tmp_path,
        "import sys\nprint(sys.stdin.read().strip().upper())\n# distinct bytes, same behavior\n",
    )
    report = evaluate(target, control)
    assert report["decision"] == "hold"
    assert "heldout_suite_has_no_discriminative_failure" in report["reasons"]
    assert "non_positive_pass_rate_separation" in report["reasons"]


def test_holds_when_fixture_sets_differ(tmp_path: Path) -> None:
    target, control = make_case(
        tmp_path,
        "import sys\nprint(sys.stdin.read().strip().lower())\n",
    )
    control["fixtures"] = list(reversed(control["fixtures"]))
    report = evaluate(target, control)
    assert report["decision"] == "hold"
    assert "fixture_sets_differ" in report["reasons"]


def test_holds_when_negative_control_is_same_candidate(tmp_path: Path) -> None:
    target, _ = make_case(
        tmp_path,
        "import sys\nprint(sys.stdin.read().strip().lower())\n",
    )
    report = evaluate(target, target)
    assert report["decision"] == "hold"
    assert "negative_control_not_distinct" in report["reasons"]
