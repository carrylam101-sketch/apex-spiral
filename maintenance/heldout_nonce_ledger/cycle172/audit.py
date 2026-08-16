"""Candidate-only restart recovery audit for the local nonce ledger.

This scanner classifies every ledger entry after a cold process restart. Any
corrupt, conflicting, unexpected, missing, or unreadable state fails closed.
It does not prove real power-loss durability or off-host independence.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping

_REQUIRED = (
    "candidate_id",
    "candidate_sha256",
    "challenge_nonce",
    "evaluator_pubkey_sha256",
    "signed_at",
)
_MARKER_RE = re.compile(r"^[0-9a-f]{64}\.used$")


def _canonical(record: Mapping[str, Any]) -> bytes:
    selected = {key: record.get(key) for key in _REQUIRED}
    return json.dumps(selected, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _record_hash(record: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(record)).hexdigest()


def _marker_name(record: Mapping[str, Any]) -> str:
    evaluator_id = str(record.get("evaluator_pubkey_sha256", ""))
    nonce = str(record.get("challenge_nonce", ""))
    digest = hashlib.sha256(f"{evaluator_id}\0{nonce}".encode("utf-8")).hexdigest()
    return f"{digest}.used"


def _logical_key(record: Mapping[str, Any]) -> str:
    return f"{record.get('evaluator_pubkey_sha256', '')}\0{record.get('challenge_nonce', '')}"


def _inspect_marker(path: Path) -> dict[str, Any]:
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {"path": str(path), "classification": "corrupt", "reason": "marker_unreadable_or_invalid_json"}
    record = envelope.get("record")
    stored_hash = envelope.get("record_sha256")
    if envelope.get("schema") != "apex.nonce-ledger.v1" or envelope.get("state") != "consumed":
        return {"path": str(path), "classification": "corrupt", "reason": "marker_schema_or_state_invalid"}
    if not isinstance(record, dict) or not isinstance(stored_hash, str):
        return {"path": str(path), "classification": "corrupt", "reason": "marker_record_invalid"}
    if any(not record.get(field) for field in _REQUIRED):
        return {"path": str(path), "classification": "corrupt", "reason": "marker_record_incomplete"}
    if not hmac.compare_digest(stored_hash, _record_hash(record)):
        return {"path": str(path), "classification": "corrupt", "reason": "marker_integrity_mismatch"}
    logical_key_sha256 = hashlib.sha256(_logical_key(record).encode("utf-8")).hexdigest()
    if not hmac.compare_digest(path.name, _marker_name(record)):
        return {
            "path": str(path),
            "classification": "corrupt",
            "reason": "marker_name_binding_mismatch",
            "logical_key_sha256": logical_key_sha256,
        }
    return {
        "path": str(path),
        "classification": "complete",
        "reason": "verified_consumption_record",
        "logical_key_sha256": logical_key_sha256,
    }


def audit_ledger(ledger_dir: Path | str) -> dict[str, Any]:
    ledger = Path(ledger_dir)
    if not ledger.is_dir():
        return _report([], False, ["ledger_unavailable"])
    try:
        paths = sorted(ledger.iterdir(), key=lambda path: path.name)
    except OSError:
        return _report([], False, ["ledger_unavailable"])
    entries: list[dict[str, Any]] = []
    for path in paths:
        if not path.is_file() or not _MARKER_RE.fullmatch(path.name):
            entries.append({"path": str(path), "classification": "unexpected", "reason": "unexpected_ledger_entry"})
        else:
            entries.append(_inspect_marker(path))
    groups: dict[str, list[int]] = {}
    for index, entry in enumerate(entries):
        key = entry.get("logical_key_sha256")
        if isinstance(key, str):
            groups.setdefault(key, []).append(index)
    for indexes in groups.values():
        if len(indexes) > 1:
            for index in indexes:
                entries[index]["classification"] = "conflict"
                entries[index]["reason"] = "duplicate_logical_nonce"
    reasons: list[str] = []
    classifications = {entry["classification"] for entry in entries}
    if not entries:
        reasons.append("no_consumption_evidence")
    if "corrupt" in classifications:
        reasons.append("corrupt_marker_present")
    if "conflict" in classifications:
        reasons.append("logical_nonce_conflict")
    if "unexpected" in classifications:
        reasons.append("unexpected_ledger_entry_present")
    return _report(entries, True, reasons)


def _report(entries: list[dict[str, Any]], scan_complete: bool, reasons: list[str]) -> dict[str, Any]:
    labels = ("complete", "conflict", "corrupt", "unexpected")
    counts = {label: sum(entry.get("classification") == label for entry in entries) for label in labels}
    return {
        "decision": "candidate_verify" if scan_complete and not reasons and counts["complete"] > 0 else "hold",
        "promotion_allowed": False,
        "restart_scan_complete": scan_complete,
        "scanned_entries": len(entries),
        "counts": counts,
        "entries": entries,
        "reasons": reasons,
        "boundary": "local cold-process scan only; real reboot and power-loss recovery unverified",
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(json.dumps({"decision": "hold", "reasons": ["usage:audit.py LEDGER_DIR"]}))
        return 2
    report = audit_ledger(argv[1])
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
