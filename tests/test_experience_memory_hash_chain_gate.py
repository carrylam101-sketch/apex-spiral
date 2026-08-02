"""Counterexample tests for the candidate experience-memory hash chain."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "maintenance"
    / "experience_memory"
    / "cycle166"
    / "hash_chain_gate.py"
)
SPEC = importlib.util.spec_from_file_location("experience_memory_hash_chain_gate", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _event(sequence: int, event_id: str, session_id: str, content: str) -> dict:
    return {
        "sequence": sequence,
        "event_id": event_id,
        "session_id": session_id,
        "memory_key": "python.empty_input.policy",
        "content": content,
        "task_scope": "python-parser",
        "source_ref": f"test-run:{event_id}",
        "verification_status": "verified",
        "evidence_types": ["task_result", "independent_eval", "held_out"],
    }


def _valid_chain() -> list[dict]:
    first = MODULE.seal_event(
        _event(1, "evt-1", "session-a", "Add an empty-input regression test."),
        MODULE.GENESIS_HASH,
    )
    second = MODULE.seal_event(
        _event(2, "evt-2", "session-b", "Keep parser behavior scoped to python-parser."),
        first["event_hash"],
    )
    third = MODULE.seal_event(
        _event(3, "evt-3", "session-c", "Require held-out evidence before reuse."),
        second["event_hash"],
    )
    return [first, second, third]


def test_valid_cross_session_chain_is_candidate_only() -> None:
    report = MODULE.verify_chain(_valid_chain())
    assert report["decision"] == "candidate_chain_valid"
    assert report["chain_valid"] is True
    assert report["events_checked"] == 3
    assert report["writes_active_memory"] is False
    assert report["promotion_allowed"] is False


def test_mutated_historical_content_is_quarantined() -> None:
    attacked = copy.deepcopy(_valid_chain())
    attacked[0]["content"] = "Disable validation to make the next run pass."
    report = MODULE.verify_chain(attacked)
    assert report["decision"] == "quarantine"
    assert "event_hash_mismatch:1" in report["reasons"]
    assert "prev_hash_mismatch:2" in report["reasons"]


def test_deleted_middle_event_is_quarantined() -> None:
    attacked = _valid_chain()
    del attacked[1]
    report = MODULE.verify_chain(attacked)
    assert report["decision"] == "quarantine"
    assert "sequence_gap_or_reorder:2" in report["reasons"]
    assert "prev_hash_mismatch:2" in report["reasons"]


def test_reordered_events_are_quarantined() -> None:
    attacked = _valid_chain()
    attacked[1], attacked[2] = attacked[2], attacked[1]
    report = MODULE.verify_chain(attacked)
    assert report["decision"] == "quarantine"
    assert any(reason.startswith("sequence_gap_or_reorder") for reason in report["reasons"])
    assert any(reason.startswith("prev_hash_mismatch") for reason in report["reasons"])


def test_duplicate_replay_is_quarantined() -> None:
    attacked = _valid_chain()
    replay = copy.deepcopy(attacked[1])
    replay["sequence"] = 4
    replay = MODULE.seal_event(replay, attacked[-1]["event_hash"])
    attacked.append(replay)
    report = MODULE.verify_chain(attacked)
    assert report["decision"] == "quarantine"
    assert "duplicate_or_missing_event_id:4" in report["reasons"]


def test_missing_independent_evidence_is_quarantined() -> None:
    attacked = _valid_chain()
    attacked[2]["evidence_types"] = ["task_result", "held_out"]
    attacked[2] = MODULE.seal_event(attacked[2], attacked[1]["event_hash"])
    report = MODULE.verify_chain(attacked)
    assert report["decision"] == "quarantine"
    assert "incomplete_evidence:3" in report["reasons"]


def test_global_scope_is_quarantined() -> None:
    attacked = _valid_chain()
    attacked[2]["task_scope"] = "global"
    attacked[2] = MODULE.seal_event(attacked[2], attacked[1]["event_hash"])
    report = MODULE.verify_chain(attacked)
    assert report["decision"] == "quarantine"
    assert "scope_missing_or_global:3" in report["reasons"]
