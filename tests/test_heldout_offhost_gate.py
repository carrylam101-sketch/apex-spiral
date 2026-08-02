"""Tests for the off-host sealed-expected evaluator gate.

These tests are interface + offline replay only. They do NOT spin up a
real cross-host transport; the purpose is to lock down the wire contract
and prove that the gate fails closed when the contract is violated.
"""
from __future__ import annotations

import importlib.util
import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG_PATH = ROOT / "maintenance" / "heldout_offhost" / "cycle165"
INTERFACE_PATH = PKG_PATH / "interface.py"
GATE_PATH = PKG_PATH / "gate.py"


def _load(module_name: str, path: Path, parent_pkg: str = "heldout_offhost_cycle165"):
    """Load `path` as `parent_pkg.module_name` so relative imports inside work.

    importlib.util.spec_from_file_location without a parent package can't
    resolve `from .interface import ...`. We synthesise a tiny parent
    package and register both modules under it.
    """
    import sys
    import types
    if parent_pkg not in sys.modules:
        parent = types.ModuleType(parent_pkg)
        parent.__path__ = [str(PKG_PATH.parent)]
        sys.modules[parent_pkg] = parent
    full_name = f"{parent_pkg}.{module_name}"
    spec = importlib.util.spec_from_file_location(full_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # dataclass needs sys.modules[name] to resolve type annotations.
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


INTERFACE = _load("interface", INTERFACE_PATH)
GATE = _load("gate", GATE_PATH)


SECRET_KEY = b"test-secret-key-cycle165-not-production-use"


def _candidate_artifact(tmp_path: Path, body: bytes = b"candidate-output-v1") -> Path:
    path = tmp_path / "candidate.bin"
    path.write_bytes(body)
    return path


def _good_expected_payload() -> dict:
    return {
        "candidate_id": "candidate-cycle165",
        "verdict": "pass",
        "expected_sha256": "",  # filled by _wrap
        "signed_at": "2026-07-31T03:00:00+08:00",
        "transport": "unix_socket",
        "transport_target": "/var/run/apex/offhost.sock",
    }


def _wrap(payload: dict) -> dict:
    out = dict(payload)
    if not out.get("expected_sha256"):
        inner = {k: v for k, v in out.items() if k != "expected_sha256"}
        inner["expected_sha256"] = "placeholder"
        out["expected_sha256"] = INTERFACE.expected_payload_hash(inner)
    return out


def test_request_rejects_local_only_transports() -> None:
    req = INTERFACE.OffHostRequest(
        candidate_id="cand-1",
        candidate_sha256="a" * 64,
        challenge_nonce="n-1",
        transport="local_file",
        transport_target="/tmp/expected.json",
    )
    errors = req.validate()
    assert any("transport_not_offhost" in e for e in errors), errors


def test_request_requires_hex_candidate_sha() -> None:
    req = INTERFACE.OffHostRequest(
        candidate_id="cand-2",
        candidate_sha256="not-hex",
        challenge_nonce="n-2",
        transport="https",
        transport_target="https://evaluator.example.com/attest",
    )
    errors = req.validate()
    assert "candidate_sha256_not_hex64" in errors


def test_attestation_requires_hex_signature() -> None:
    att = INTERFACE.OffHostAttestation(
        verdict="pass",
        expected_sha256="b" * 64,
        signed_at="2026-07-31T03:00:00+08:00",
        attestation_sig="not-hex",
        evaluator_pubkey_sha256="c" * 64,
    )
    errors = att.validate()
    assert "attestation_sig_not_hex" in errors  # validator rejects non-hex sigs


def test_attestation_rejects_unknown_verdict() -> None:
    att = INTERFACE.OffHostAttestation(
        verdict="maybe",
        expected_sha256="d" * 64,
        signed_at="2026-07-31T03:00:00+08:00",
        attestation_sig="e" * 64,
        evaluator_pubkey_sha256="f" * 64,
    )
    errors = att.validate()
    assert "verdict_not_in_alphabet" in errors


def test_expected_payload_hash_is_deterministic() -> None:
    a = INTERFACE.expected_payload_hash({"a": 1, "b": [1, 2]})
    b = INTERFACE.expected_payload_hash({"b": [1, 2], "a": 1})
    assert a == b
    assert len(a) == 64


def test_gate_holds_when_payload_references_local_filesystem(tmp_path: Path) -> None:
    artifact = _candidate_artifact(tmp_path)
    payload = _wrap({
        "candidate_id": "cand-3",
        "verdict": "pass",
        "expected_sha256": "",
        "signed_at": "2026-07-31T03:00:00+08:00",
        "transport": "unix_socket",
        "transport_target": "/home/ubuntu/apex-spiral/secrets.json",
    })
    report = GATE.offhost_gate(
        candidate_artifact_path=artifact,
        expected_payload=payload,
        secret_key=SECRET_KEY,
    )
    assert report["decision"] == "hold"
    assert report["promotion_allowed"] is False
    assert report["offhost_transport_actually_reachable"] is False
    assert any(
        "expected_payload_references_local_filesystem" in r
        for r in report["reasons"]
    )
    assert report["offline_replay_evidence"]["reasons"]  # replay still attempted and recorded


def test_gate_holds_when_declared_transport_is_local(tmp_path: Path) -> None:
    artifact = _candidate_artifact(tmp_path)
    payload = _wrap({
        "candidate_id": "cand-4",
        "verdict": "pass",
        "expected_sha256": "",
        "signed_at": "2026-07-31T03:00:00+08:00",
        "transport": "local_file",
        "transport_target": "/tmp/expected.json",
    })
    report = GATE.offhost_gate(
        candidate_artifact_path=artifact,
        expected_payload=payload,
        secret_key=SECRET_KEY,
    )
    assert report["decision"] == "hold"
    assert any("declared_transport_not_offhost" in r for r in report["reasons"])


def test_gate_holds_when_no_offhost_transport_reachable(tmp_path: Path) -> None:
    artifact = _candidate_artifact(tmp_path)
    payload = _wrap(_good_expected_payload())
    # Ensure no env hints fool the probe.
    env = {k: v for k, v in os.environ.items() if not k.startswith("APEX_OFFHOST_")}
    saved = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update(env)
        report = GATE.offhost_gate(
            candidate_artifact_path=artifact,
            expected_payload=payload,
            secret_key=SECRET_KEY,
        )
    finally:
        os.environ.clear()
        os.environ.update(saved)
    assert report["decision"] == "hold"
    assert report["offhost_transport_actually_reachable"] is False
    assert any(
        "no_offhost_transport_reachable_in_runtime" in r
        for r in report["reasons"]
    )


def test_gate_holds_when_replay_attestation_is_malformed(tmp_path: Path) -> None:
    artifact = _candidate_artifact(tmp_path)
    payload = _wrap(_good_expected_payload())
    # Empty secret -> attestation_sig becomes a sha256 of empty bytes, which is
    # valid hex; instead break expected_sha256 so the mismatch path triggers.
    payload["expected_sha256"] = "0" * 64
    report = GATE.offhost_gate(
        candidate_artifact_path=artifact,
        expected_payload=payload,
        secret_key=SECRET_KEY,
    )
    assert report["decision"] == "hold"
    assert any(
        "replay_failed:expected_sha256_mismatch" in r
        for r in report["reasons"]
    )


def test_gate_holds_when_candidate_artifact_missing(tmp_path: Path) -> None:
    artifact = tmp_path / "does-not-exist.bin"
    payload = _wrap(_good_expected_payload())
    report = GATE.offhost_gate(
        candidate_artifact_path=artifact,
        expected_payload=payload,
        secret_key=SECRET_KEY,
    )
    assert report["decision"] == "hold"
    replay = report["offline_replay_evidence"]
    assert "candidate_artifact_missing" in replay["reasons"]


def test_gate_reports_candidate_host_fingerprint(tmp_path: Path) -> None:
    artifact = _candidate_artifact(tmp_path)
    payload = _wrap(_good_expected_payload())
    report = GATE.offhost_gate(
        candidate_artifact_path=artifact,
        expected_payload=payload,
        secret_key=SECRET_KEY,
    )
    fp = report["candidate_host_fingerprint"]
    assert fp["hostname"]
    assert len(fp["cwd_hash"]) == 64
    # sealed expected output was never written to disk by the gate
    assert report["sealed_expected_disclosed_on_candidate_host"] is False
    # /tmp/cycle165-leak.json must not exist (a regression test against
    # any future code path that accidentally materialises the expected
    # output onto the candidate host's filesystem).
    assert not (tmp_path / "cycle165-leak.json").exists()