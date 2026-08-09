"""Candidate crash-consistent, fail-closed nonce ledger.

This local gate strengthens one-time nonce consumption against interrupted writes
and corrupt markers. It does not prove power-loss durability on all filesystems,
distributed atomicity, trusted time, or off-host evaluator independence.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any, Mapping

_REQUIRED = (
    "candidate_id",
    "candidate_sha256",
    "challenge_nonce",
    "evaluator_pubkey_sha256",
    "signed_at",
)


def _canonical(record: Mapping[str, Any]) -> bytes:
    selected = {key: record.get(key) for key in _REQUIRED}
    return json.dumps(selected, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _record_hash(record: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(record)).hexdigest()


def marker_path(ledger_dir: Path | str, record: Mapping[str, Any]) -> Path:
    evaluator_id = str(record.get("evaluator_pubkey_sha256", ""))
    nonce = str(record.get("challenge_nonce", ""))
    digest = hashlib.sha256(f"{evaluator_id}\0{nonce}".encode("utf-8")).hexdigest()
    return Path(ledger_dir) / f"{digest}.used"


def _validate_existing(marker: Path, record: Mapping[str, Any]) -> tuple[bool, str]:
    try:
        envelope = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False, "ledger_marker_corrupt"
    stored = envelope.get("record")
    stored_hash = envelope.get("record_sha256")
    if not isinstance(stored, dict) or not isinstance(stored_hash, str):
        return False, "ledger_marker_corrupt"
    if not hmac.compare_digest(stored_hash, _record_hash(stored)):
        return False, "ledger_marker_corrupt"
    if not hmac.compare_digest(stored_hash, _record_hash(record)):
        return False, "ledger_nonce_collision_or_record_mismatch"
    return True, "challenge_nonce_already_consumed"


def _write_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    offset = 0
    while offset < len(view):
        written = os.write(fd, view[offset:])
        if written <= 0:
            raise OSError("short ledger write")
        offset += written


def consume_nonce_durably(ledger_dir: Path | str, record: Mapping[str, Any]) -> dict[str, Any]:
    """Create, verify, fsync, and directory-fsync a nonce marker before accept."""
    reasons: list[str] = []
    missing = [field for field in _REQUIRED if not record.get(field)]
    reasons.extend(f"missing_record_field:{field}" for field in missing)
    marker = marker_path(ledger_dir, record)
    if reasons:
        return _report(marker, reasons, False)

    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return _report(marker, ["ledger_unavailable"], False)

    envelope = {
        "schema": "apex.nonce-ledger.v1",
        "record": {key: record.get(key) for key in _REQUIRED},
        "record_sha256": _record_hash(record),
        "state": "consumed",
    }
    payload = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(marker, flags, 0o600)
    except FileExistsError:
        valid, reason = _validate_existing(marker, record)
        return _report(marker, [reason], False, existing_marker_valid=valid)
    except OSError:
        return _report(marker, ["ledger_unavailable"], False)

    durable_commit = False
    try:
        _write_all(fd, payload)
        os.fsync(fd)
        os.close(fd)
        fd = -1
        valid, reason = _validate_existing(marker, record)
        if not valid:
            return _report(marker, [reason], False, existing_marker_valid=False)
        directory_fd = os.open(marker.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        durable_commit = True
    except OSError:
        return _report(marker, ["ledger_commit_failed"], False)
    finally:
        if fd >= 0:
            os.close(fd)

    return _report(marker, [], durable_commit, existing_marker_valid=True)


def _report(
    marker: Path,
    reasons: list[str],
    durable_commit: bool,
    *,
    existing_marker_valid: bool | None = None,
) -> dict[str, Any]:
    return {
        "decision": "candidate_verify" if durable_commit and not reasons else "hold",
        "promotion_allowed": False,
        "durable_commit": durable_commit,
        "marker_path": str(marker),
        "marker_exists": marker.exists(),
        "existing_marker_valid": existing_marker_valid,
        "reasons": reasons,
        "boundary": "local fsync replay only; real power-loss and distributed durability unverified",
    }
