"""Tests for capability-gated OS isolation of held-out expected outputs."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "maintenance" / "heldout_os_isolation" / "cycle164" / "gate.py"
SPEC = importlib.util.spec_from_file_location("heldout_os_isolation_gate", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_live_environment_fails_closed_when_isolation_is_unavailable() -> None:
    report = MODULE.isolation_gate()
    assert report["decision"] == "hold"
    assert report["candidate_execution_started"] is False
    assert report["sealed_expected_path_disclosed"] is False
    assert report["promotion_allowed"] is False
    assert report["os_level_secrecy_verified"] is False
    assert "os_identity_or_user_namespace_isolation_unavailable" in report["reasons"]


def test_gate_accepts_verified_distinct_uid_capability_but_never_promotes() -> None:
    capabilities = {
        "evaluator_uid": 1000,
        "setpriv": {"returncode": 0, "stdout": "65534"},
        "unshare_user_namespace": {"returncode": 1, "stdout": ""},
        "distinct_uid_verified": True,
        "user_namespace_verified": False,
        "isolation_mechanism_available": True,
    }
    report = MODULE.isolation_gate(capabilities)
    assert report["decision"] == "candidate_verify"
    assert report["promotion_allowed"] is False
    assert report["candidate_execution_started"] is False
    assert report["os_level_secrecy_verified"] is False


def test_claim_without_verified_mechanism_fails_closed() -> None:
    capabilities = {
        "evaluator_uid": 1000,
        "setpriv": {"returncode": 0, "stdout": "1000"},
        "unshare_user_namespace": {"returncode": 0, "stdout": "1000"},
        "distinct_uid_verified": False,
        "user_namespace_verified": False,
        "isolation_mechanism_available": False,
    }
    report = MODULE.isolation_gate(capabilities)
    assert report["decision"] == "hold"
    assert report["reasons"] == ["os_identity_or_user_namespace_isolation_unavailable"]
