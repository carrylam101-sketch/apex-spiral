"""Tests for the candidate held-out commit-reveal integrity gate."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "maintenance" / "heldout_commit_reveal" / "cycle159" / "gate.py"
SPEC = importlib.util.spec_from_file_location("heldout_commit_reveal_gate", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def make_artifacts(tmp_path: Path):
    candidate = tmp_path / "candidate.txt"
    candidate.write_text("candidate-v1\n", encoding="utf-8")
    fixtures = []
    for index in range(3):
        fixture = tmp_path / f"fixture-{index}.txt"
        fixture.write_text(f"fixture-{index}\n", encoding="utf-8")
        fixtures.append(fixture)
    manifest = MODULE.canonical_manifest(candidate, fixtures)
    commitment = MODULE.manifest_digest(manifest)
    return candidate, fixtures, manifest, commitment


def test_frozen_candidate_and_fixture_set_pass_integrity_only(tmp_path: Path) -> None:
    _, _, manifest, commitment = make_artifacts(tmp_path)
    report = MODULE.verify(manifest, commitment)
    assert report["decision"] == "candidate_verify"
    assert report["commitment_match"] is True
    assert report["candidate_immutable"] is True
    assert report["fixtures_immutable"] is True
    assert report["hiddenness_verified"] is False
    assert report["semantic_independence_verified"] is False
    assert report["promotion_allowed"] is False


def test_candidate_mutation_after_commitment_fails_closed(tmp_path: Path) -> None:
    candidate, _, manifest, commitment = make_artifacts(tmp_path)
    candidate.write_text("candidate-v2\n", encoding="utf-8")
    report = MODULE.verify(manifest, commitment)
    assert report["decision"] == "hold"
    assert "candidate_changed_or_missing" in report["reasons"]


def test_fixture_mutation_after_commitment_fails_closed(tmp_path: Path) -> None:
    _, fixtures, manifest, commitment = make_artifacts(tmp_path)
    fixtures[1].write_text("leaked-and-edited\n", encoding="utf-8")
    report = MODULE.verify(manifest, commitment)
    assert report["decision"] == "hold"
    assert "fixture_changed_or_missing" in report["reasons"]


def test_manifest_relabel_without_new_commitment_fails_closed(tmp_path: Path) -> None:
    _, _, manifest, commitment = make_artifacts(tmp_path)
    manifest["fixtures"][0]["path"] = manifest["fixtures"][1]["path"]
    report = MODULE.verify(manifest, commitment)
    assert report["decision"] == "hold"
    assert "commitment_mismatch" in report["reasons"]


def test_duplicate_fixture_digest_is_rejected(tmp_path: Path) -> None:
    _, _, manifest, _ = make_artifacts(tmp_path)
    manifest["fixtures"][1]["sha256"] = manifest["fixtures"][0]["sha256"]
    commitment = MODULE.manifest_digest(manifest)
    report = MODULE.verify(manifest, commitment)
    assert report["decision"] == "hold"
    assert "duplicate_fixture_digest" in report["reasons"]
