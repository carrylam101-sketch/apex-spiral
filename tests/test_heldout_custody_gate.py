"""Tests for post-commit held-out fixture custody."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "maintenance" / "heldout_custody" / "cycle162" / "gate.py"
SPEC = importlib.util.spec_from_file_location("heldout_custody_gate", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def make_transcript(tmp_path: Path):
    candidate = tmp_path / "candidate.py"
    candidate.write_text("print('candidate')\n", encoding="utf-8")
    custody = MODULE.begin_custody(candidate)
    fixtures = []
    for index in range(3):
        fixture = tmp_path / f"fixture-{index}.json"
        fixture.write_text(
            json.dumps(
                {
                    "probe_id": f"p{index}",
                    "custody_canary": custody["canary"],
                    "payload": f"held-out-{index}",
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        fixtures.append(fixture)
    return candidate, fixtures, MODULE.reveal_fixtures(custody, fixtures)


def refresh_transcript_digest(transcript):
    transcript["transcript_digest"] = MODULE.canonical_digest(
        {key: value for key, value in transcript.items() if key != "transcript_digest"}
    )


def test_accepts_candidate_commit_before_fresh_fixture_reveal(tmp_path: Path) -> None:
    _, _, transcript = make_transcript(tmp_path)
    report = MODULE.verify_custody(transcript)
    assert report["decision"] == "candidate_verify"
    assert report["candidate_frozen_before_fixture_reveal"] is True
    assert report["hiddenness_verified"] is False
    assert report["promotion_allowed"] is False


def test_detects_post_commit_canary_in_candidate(tmp_path: Path) -> None:
    candidate, _, transcript = make_transcript(tmp_path)
    candidate.write_text(
        candidate.read_text(encoding="utf-8") + f"# {transcript['canary']}\n",
        encoding="utf-8",
    )
    transcript["candidate"]["sha256"] = MODULE.sha256_file(candidate)
    refresh_transcript_digest(transcript)
    report = MODULE.verify_custody(transcript)
    assert report["decision"] == "hold"
    assert "post_commit_canary_present_in_candidate" in report["reasons"]
    assert report["precommit_canary_leak_detected"] is True


def test_holds_when_fixture_reveal_precedes_candidate_commit(tmp_path: Path) -> None:
    _, _, transcript = make_transcript(tmp_path)
    transcript["fixtures_revealed_ns"] = transcript["candidate_committed_ns"]
    refresh_transcript_digest(transcript)
    report = MODULE.verify_custody(transcript)
    assert report["decision"] == "hold"
    assert "custody_order_invalid" in report["reasons"]


def test_holds_on_fixture_mutation_after_reveal(tmp_path: Path) -> None:
    _, fixtures, transcript = make_transcript(tmp_path)
    fixtures[0].write_text("{}\n", encoding="utf-8")
    report = MODULE.verify_custody(transcript)
    assert report["decision"] == "hold"
    assert "fixture_changed_or_missing" in report["reasons"]


def test_rejects_weak_canary(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.py"
    candidate.write_text("print('candidate')\n", encoding="utf-8")
    try:
        MODULE.begin_custody(candidate, canary_bytes=8)
    except ValueError as exc:
        assert str(exc) == "canary_too_short"
    else:
        raise AssertionError("weak canary was accepted")
