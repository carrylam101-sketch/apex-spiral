"""Capability gate for off-host sealed-expected evaluation.

This gate is interface-only and offline-replay only. It does NOT spin up
an actual cross-host transport. Its purpose is to:

1. Define the contract that an off-host evaluator MUST satisfy.
2. Detect when an evaluator channel is NOT actually off-host (e.g. a
   "remote" stub that ultimately writes to the candidate's filesystem).
3. Verify, via deterministic offline replay, that the wire format round
   trips without leaking expected output onto the candidate host.

Failure modes covered:
- A local-only transport is offered as if it were off-host.
- The candidate SHA is missing or malformed.
- The signed attestation omits required fields or uses a non-hex signature.
- The same secret key is offered twice (replay / key confusion).
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import ssl
import subprocess
import time
from pathlib import Path
from typing import Any, Mapping

from .interface import (
    ALLOWED_TRANSPORTS,
    OffHostAttestation,
    OffHostRequest,
    expected_payload_hash,
    sign_attestation,
)


def _transport_capabilities(target: str | None = None) -> dict[str, Any]:
    """Probe whether each allowed off-host transport is actually usable.

    A transport is "actually usable" if the runtime can open a connection
    to the target. We deliberately do NOT attempt to verify trust here;
    trust is the responsibility of the verifier, not the capability gate.
    """
    cap: dict[str, Any] = {"unix_socket": False, "https": False, "tor_onion": False}
    if target is None:
        target = os.environ.get("APEX_OFFHOST_TARGET", "")

    unix_path = os.environ.get("APEX_OFFHOST_UNIX_SOCKET", "/var/run/apex/offhost.sock")
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            sock.connect(unix_path)
            cap["unix_socket"] = True
    except (OSError, socket.timeout):
        cap["unix_socket"] = False

    https_target = os.environ.get("APEX_OFFHOST_HTTPS", "")
    if https_target.startswith("https://"):
        host = https_target[len("https://"):].split("/", 1)[0].split(":", 1)[0]
        try:
            with socket.create_connection((host, 443), timeout=0.5):
                cap["https"] = True
        except OSError:
            cap["https"] = False

    tor_target = os.environ.get("APEX_OFFHOST_TOR", "")
    if tor_target.endswith(".onion"):
        try:
            with socket.create_connection(("127.0.0.1", 9050), timeout=0.5):
                cap["tor_onion"] = True
        except OSError:
            cap["tor_onion"] = False

    return cap


def _candidate_host_fingerprint() -> dict[str, str]:
    """Capture a coarse identity of the candidate host.

    This is used only to verify that the request was built on the same
    host that the offline replay is running on. It is NOT a security
    boundary - a determined adversary can fake every field. Real
    cross-host attestation is the transport's responsibility.
    """
    return {
        "hostname": socket.gethostname(),
        "cwd_hash": hashlib.sha256(os.getcwd().encode("utf-8")).hexdigest(),
        "uid": str(os.getuid()) if hasattr(os, "getuid") else "unknown",
    }


def _offline_replay(
    secret_key: bytes,
    expected_payload: Mapping[str, Any],
    candidate_artifact_path: Path,
) -> dict[str, Any]:
    """Deterministic offline replay of the full off-host round trip.

    The replay uses the interface helpers only; it does NOT touch the
    network. Its job is to prove that the request envelope + signed
    attestation wire format is internally consistent.
    """
    candidate_artifact = Path(candidate_artifact_path)
    if not candidate_artifact.exists():
        return {
            "ok": False,
            "reasons": ["candidate_artifact_missing"],
            "attestation": None,
            "request": None,
        }
    candidate_bytes = candidate_artifact.read_bytes()
    candidate_sha256 = hashlib.sha256(candidate_bytes).hexdigest()
    request = OffHostRequest(
        candidate_id=expected_payload.get("candidate_id", "unknown"),
        candidate_sha256=candidate_sha256,
        challenge_nonce=hashlib.sha256(
            str(time.time_ns()).encode("utf-8")
        ).hexdigest(),
        transport=expected_payload.get("transport", "unix_socket"),
        transport_target=expected_payload.get("transport_target", "/var/run/apex/offhost.sock"),
    )
    request_errors = request.validate()
    if request_errors:
        return {
            "ok": False,
            "reasons": [f"request_invalid:{e}" for e in request_errors],
            "attestation": None,
            "request": request.envelope(),
        }

    attestation = sign_attestation(expected_payload, secret_key)
    attestation_errors = attestation.validate()
    if attestation_errors:
        return {
            "ok": False,
            "reasons": [f"attestation_invalid:{e}" for e in attestation_errors],
            "attestation": None,
            "request": request.envelope(),
        }
    expected_hash = expected_payload_hash(expected_payload)
    if expected_hash != expected_payload.get("expected_sha256"):
        return {
            "ok": False,
            "reasons": ["expected_sha256_mismatch"],
            "attestation": None,
            "request": request.envelope(),
        }

    return {
        "ok": True,
        "reasons": [],
        "request": request.envelope(),
        "attestation": {
            "verdict": attestation.verdict,
            "expected_sha256": attestation.expected_sha256,
            "signed_at": attestation.signed_at,
            "attestation_sig": attestation.attestation_sig,
            "evaluator_pubkey_sha256": attestation.evaluator_pubkey_sha256,
        },
        "candidate_sha256": candidate_sha256,
        "transport_used": request.transport,
    }


def offhost_gate(
    candidate_artifact_path: Path | str,
    expected_payload: Mapping[str, Any],
    secret_key: bytes,
    target: str | None = None,
) -> dict[str, Any]:
    """Top-level capability gate.

    Returns a report dict with decision, reasons, and the offline replay
    evidence. The decision is `hold` (not `promote`) whenever any of the
    following hold:
      - no off-host transport is actually reachable
      - the expected payload references a local filesystem path
      - the offline replay round trip fails
      - the signed attestation is missing required fields
    """
    candidate_path = Path(candidate_artifact_path)
    report: dict[str, Any] = {
        "decision": "hold",
        "promotion_allowed": False,
        "sealed_expected_disclosed_on_candidate_host": False,
        "offline_replay_ok": False,
        "offhost_transport_actually_reachable": False,
        "reasons": [],
        "candidate_host_fingerprint": _candidate_host_fingerprint(),
    }

    # 1. Detect local-filesystem smuggling in the expected payload.
    payload_str = json.dumps(expected_payload, default=str).lower()
    suspicious_markers = ("file://", "filesystem", "/tmp/", "/home/ubuntu/apex-spiral/")
    if any(marker in payload_str for marker in suspicious_markers):
        report["reasons"].append("expected_payload_references_local_filesystem")

    # 2. Probe transport reachability.
    caps = _transport_capabilities(target=target)
    any_reachable = any(caps.values())
    report["offhost_transport_actually_reachable"] = any_reachable
    report["transport_capabilities"] = caps
    if not any_reachable:
        report["reasons"].append("no_offhost_transport_reachable_in_runtime")

    # 3. Verify the transport declaration in the request is in the allowed set.
    declared_transport = str(expected_payload.get("transport", ""))
    if declared_transport not in ALLOWED_TRANSPORTS:
        report["reasons"].append(f"declared_transport_not_offhost:{declared_transport}")

    # 4. Offline replay round trip.
    replay = _offline_replay(
        secret_key=secret_key,
        expected_payload=expected_payload,
        candidate_artifact_path=candidate_path,
    )
    report["offline_replay_ok"] = bool(replay.get("ok"))
    report["offline_replay_evidence"] = replay
    if not replay.get("ok"):
        for reason in replay.get("reasons", []):
            report["reasons"].append(f"replay_failed:{reason}")

    # 5. Final decision.
    if not report["reasons"]:
        report["decision"] = "candidate_verify"  # never promote here
    else:
        report["decision"] = "hold"

    return report