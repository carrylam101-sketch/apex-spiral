"""Candidate-only binding of restart audit output to ledger bytes and challenge."""
from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping

_PREVIOUS_AUDIT = Path(__file__).resolve().parents[1] / "cycle172" / "audit.py"


def _load_audit():
    spec = importlib.util.spec_from_file_location("cycle172_restart_audit", _PREVIOUS_AUDIT)
    if spec is None or spec.loader is None:
        raise RuntimeError("restart_audit_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _ledger_manifest(ledger_dir: Path | str) -> dict[str, Any]:
    ledger = Path(ledger_dir)
    if not ledger.is_dir():
        return {"available": False, "entries": []}
    entries: list[dict[str, Any]] = []
    try:
        paths = sorted(ledger.iterdir(), key=lambda path: path.name)
    except OSError:
        return {"available": False, "entries": []}
    for path in paths:
        entry: dict[str, Any] = {"name": path.name, "kind": "file" if path.is_file() else "other"}
        if path.is_file():
            try:
                raw = path.read_bytes()
            except OSError:
                entry["readable"] = False
            else:
                entry["readable"] = True
                entry["size"] = len(raw)
                entry["sha256"] = hashlib.sha256(raw).hexdigest()
        entries.append(entry)
    return {"available": True, "entries": entries}


def _snapshot_payload(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": snapshot.get("schema"),
        "challenge": snapshot.get("challenge"),
        "ledger_manifest_sha256": snapshot.get("ledger_manifest_sha256"),
        "audit_report_sha256": snapshot.get("audit_report_sha256"),
        "audit_report": snapshot.get("audit_report"),
    }


def create_bound_snapshot(ledger_dir: Path | str, evaluator_challenge: str) -> dict[str, Any]:
    audit = _load_audit().audit_ledger(ledger_dir)
    manifest = _ledger_manifest(ledger_dir)
    snapshot: dict[str, Any] = {
        "schema": "apex.restart-audit-snapshot.v1",
        "challenge": evaluator_challenge,
        "ledger_manifest_sha256": _sha256(manifest),
        "audit_report_sha256": _sha256(audit),
        "audit_report": audit,
        "promotion_allowed": False,
    }
    snapshot["snapshot_sha256"] = _sha256(_snapshot_payload(snapshot))
    return snapshot


def verify_bound_snapshot(
    ledger_dir: Path | str,
    evaluator_challenge: str,
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    current_audit = _load_audit().audit_ledger(ledger_dir)
    current_manifest = _ledger_manifest(ledger_dir)
    challenge_match = bool(evaluator_challenge) and hmac.compare_digest(
        str(snapshot.get("challenge", "")), evaluator_challenge
    )
    ledger_digest_match = hmac.compare_digest(
        str(snapshot.get("ledger_manifest_sha256", "")), _sha256(current_manifest)
    )
    audit_report_match = hmac.compare_digest(
        str(snapshot.get("audit_report_sha256", "")), _sha256(snapshot.get("audit_report"))
    ) and hmac.compare_digest(
        str(snapshot.get("audit_report_sha256", "")), _sha256(current_audit)
    )
    snapshot_integrity_match = hmac.compare_digest(
        str(snapshot.get("snapshot_sha256", "")), _sha256(_snapshot_payload(snapshot))
    )
    if not evaluator_challenge:
        reasons.append("evaluator_challenge_empty")
    elif not challenge_match:
        reasons.append("evaluator_challenge_mismatch")
    if not ledger_digest_match:
        reasons.append("ledger_changed_after_audit")
    if not audit_report_match:
        reasons.append("audit_report_binding_mismatch")
    if not snapshot_integrity_match:
        reasons.append("snapshot_integrity_mismatch")
    if current_audit.get("decision") != "candidate_verify":
        reasons.append("embedded_audit_not_verified")
    verified = not reasons
    return {
        "decision": "candidate_verify" if verified else "hold",
        "promotion_allowed": False,
        "challenge_match": challenge_match,
        "ledger_digest_match": ledger_digest_match,
        "audit_report_match": audit_report_match,
        "snapshot_integrity_match": snapshot_integrity_match,
        "reasons": reasons,
        "boundary": "local hash binding only; no digital signature, trusted clock, or off-host verifier",
    }
