"""Candidate external trusted-watermark store.

Cycle 169 extends the cycle 168 freshness gate by introducing a small,
append-only backend interface for the trusted watermark so that the
"latest checkpoint" anchor cannot be silently rolled back together
with the checkpoint itself. The module never writes active memory
or production state and never promotes itself: every backend exposes
is_append_only so callers can verify the self-attestation.
"""
from __future__ import annotations

import json
import os
import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping


GENESIS_WATERMARK_SEQ = 0
GENESIS_WATERMARK_HASH = "0" * 64


class WatermarkStoreError(Exception):
    pass


class ChainNotFound(WatermarkStoreError):
    pass


class SequenceNotMonotonic(WatermarkStoreError):
    pass


class PayloadMismatch(WatermarkStoreError):
    pass


@dataclass(frozen=True)
class WatermarkEntry:
    chain_id: str
    seq: int
    checkpoint_sha256: str
    prev_checkpoint_sha256: str
    written_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "seq": self.seq,
            "checkpoint_sha256": self.checkpoint_sha256,
            "prev_checkpoint_sha256": self.prev_checkpoint_sha256,
            "written_at": self.written_at,
        }


@dataclass(frozen=True)
class WatermarkView:
    chain_id: str
    seq: int
    checkpoint_sha256: str
    entry_count: int
    backend_name: str
    backend_append_only: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "checkpoint_sha256": self.checkpoint_sha256,
            "entry_count": self.entry_count,
            "backend_name": self.backend_name,
            "backend_append_only": self.backend_append_only,
        }


def canonical_entry(entry: Any) -> bytes:
    """Stable canonical bytes for a watermark entry.

    Accepts either a Mapping (dict) or a WatermarkEntry (frozen dataclass).
    The returned bytes are deterministic: sorted keys, no spaces, ASCII.
    """
    if hasattr(entry, "as_dict") and callable(getattr(entry, "as_dict")):
        payload = entry.as_dict()
    elif isinstance(entry, Mapping):
        payload = dict(entry)
    else:
        payload = {
            "chain_id": entry.chain_id,
            "seq": entry.seq,
            "checkpoint_sha256": entry.checkpoint_sha256,
            "prev_checkpoint_sha256": entry.prev_checkpoint_sha256,
            "written_at": entry.written_at,
        }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def entry_sha256(entry: WatermarkEntry) -> str:
    return hashlib.sha256(canonical_entry(entry)).hexdigest()


class WatermarkStore:
    """Abstract append-only watermark backend.

    All methods MUST be idempotent on reads and monotonic on writes.
    Implementations MUST expose is_append_only truthfully: an in-memory
    backend that allows overwrite must return False so callers can refuse
    to promote an artifact that depended on it.
    """

    name: str

    def is_append_only(self) -> bool:
        raise NotImplementedError

    def get_watermark(self, *, chain_id: str) -> WatermarkView:
        raise NotImplementedError

    def put_watermark(self, *, chain_id: str, seq: int, checkpoint_sha256: str, prev_checkpoint_sha256: str, written_at: str) -> WatermarkEntry:
        raise NotImplementedError

    def audit_trail(self, *, chain_id: str, limit: int = 100) -> tuple[WatermarkEntry, ...]:
        raise NotImplementedError

    def chain_count(self) -> int:
        raise NotImplementedError

    def close(self) -> None:
        # default no-op; FileAppendOnlyWatermarkStore overrides
        return None


@dataclass
class InMemoryWatermarkStore(WatermarkStore):
    """In-process dict-backed watermark store.

    NOT append-only: any holder of the same Python object can overwrite
    or delete entries. Suitable only for tests and offline replay; never
    for promotion. is_append_only returns False so that callers can
    refuse to promote an artifact that depended solely on this backend.
    """

    name: str = "in_memory_dict"
    _chains: dict[str, list[WatermarkEntry]] = field(default_factory=dict)

    def is_append_only(self) -> bool:
        return False

    def get_watermark(self, *, chain_id: str) -> WatermarkView:
        entries = self._chains.get(chain_id, [])
        if not entries:
            return WatermarkView(
                chain_id=chain_id,
                seq=GENESIS_WATERMARK_SEQ,
                checkpoint_sha256=GENESIS_WATERMARK_HASH,
                entry_count=0,
                backend_name=self.name,
                backend_append_only=False,
            )
        head = entries[-1]
        return WatermarkView(
                chain_id=chain_id,
                seq=head.seq,
                checkpoint_sha256=head.checkpoint_sha256,
                entry_count=len(entries),
                backend_name=self.name,
                backend_append_only=False,
            )

    def put_watermark(self, *, chain_id: str, seq: int, checkpoint_sha256: str, prev_checkpoint_sha256: str, written_at: str) -> WatermarkEntry:
        entries = self._chains.setdefault(chain_id, [])
        expected_next = (entries[-1].seq if entries else GENESIS_WATERMARK_SEQ) + 1
        if seq != expected_next:
            raise SequenceNotMonotonic(
                f"chain_id={chain_id} expected_seq={expected_next} got_seq={seq}"
            )
        if entries and prev_checkpoint_sha256 != entries[-1].checkpoint_sha256:
            raise PayloadMismatch(
                f"chain_id={chain_id} prev_mismatch got={prev_checkpoint_sha256[:12]} expected={entries[-1].checkpoint_sha256[:12]}"
            )
        entry = WatermarkEntry(
            chain_id=chain_id,
            seq=seq,
            checkpoint_sha256=checkpoint_sha256,
            prev_checkpoint_sha256=prev_checkpoint_sha256,
            written_at=written_at,
        )
        entries.append(entry)
        return entry

    def audit_trail(self, *, chain_id: str, limit: int = 100) -> tuple[WatermarkEntry, ...]:
        entries = self._chains.get(chain_id, [])
        return tuple(entries[-limit:])

    def chain_count(self) -> int:
        return len(self._chains)


@dataclass
class FileAppendOnlyWatermarkStore(WatermarkStore):
    """POSIX append-only file backend.

    Each chain lives in its own log file under root_dir. Writes use
    O_APPEND + fsync so concurrent appenders serialize on the kernel
    and a torn write either completes or leaves the file unchanged.
    Reads scan the file from the tail. The store reports is_append_only
    truthfully but DOES NOT protect against an attacker who holds the
    host uid: they can unlink or replace the file. Cross-check with a
    second backend is the canonical defense.
    """

    root_dir: str
    name: str = "file_append_only"

    def __post_init__(self) -> None:
        os.makedirs(self.root_dir, exist_ok=True)

    def _path(self, chain_id: str) -> str:
        safe = chain_id.replace("/", "_")
        return os.path.join(self.root_dir, f"{safe}.log")

    def _read_entries(self, chain_id: str) -> list[WatermarkEntry]:
        path = self._path(chain_id)
        if not os.path.exists(path):
            return []
        entries: list[WatermarkEntry] = []
        try:
            with open(path, "r", encoding="ascii") as fp:
                for raw in fp:
                    line = raw.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    entries.append(WatermarkEntry(
                        chain_id=str(data["chain_id"]),
                        seq=int(data["seq"]),
                        checkpoint_sha256=str(data["checkpoint_sha256"]),
                        prev_checkpoint_sha256=str(data["prev_checkpoint_sha256"]),
                        written_at=str(data["written_at"]),
                    ))
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            raise PayloadMismatch(
                f"chain_id={chain_id} file_truncated_or_corrupted err={exc.__class__.__name__}"
            ) from exc
        return entries

    def is_append_only(self) -> bool:
        return True

    def get_watermark(self, *, chain_id: str) -> WatermarkView:
        entries = self._read_entries(chain_id)
        if not entries:
            return WatermarkView(
                chain_id=chain_id,
                seq=GENESIS_WATERMARK_SEQ,
                checkpoint_sha256=GENESIS_WATERMARK_HASH,
                entry_count=0,
                backend_name=self.name,
                backend_append_only=True,
            )
        head = entries[-1]
        return WatermarkView(
            chain_id=chain_id,
            seq=head.seq,
            checkpoint_sha256=head.checkpoint_sha256,
            entry_count=len(entries),
            backend_name=self.name,
            backend_append_only=True,
        )

    def put_watermark(self, *, chain_id: str, seq: int, checkpoint_sha256: str, prev_checkpoint_sha256: str, written_at: str) -> WatermarkEntry:
        path = self._path(chain_id)
        entries = self._read_entries(chain_id)
        expected_next = (entries[-1].seq if entries else GENESIS_WATERMARK_SEQ) + 1
        if seq != expected_next:
            raise SequenceNotMonotonic(
                f"chain_id={chain_id} expected_seq={expected_next} got_seq={seq}"
            )
        if entries and prev_checkpoint_sha256 != entries[-1].checkpoint_sha256:
            raise PayloadMismatch(
                f"chain_id={chain_id} prev_mismatch got={prev_checkpoint_sha256[:12]} expected={entries[-1].checkpoint_sha256[:12]}"
            )
        entry = WatermarkEntry(
            chain_id=chain_id,
            seq=seq,
            checkpoint_sha256=checkpoint_sha256,
            prev_checkpoint_sha256=prev_checkpoint_sha256,
            written_at=written_at,
        )
        payload_bytes = canonical_entry(entry)
        NL_CHAR = chr(10)
        line_bytes = payload_bytes + NL_CHAR.encode("ascii")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, line_bytes)
            os.fsync(fd)
        finally:
            os.close(fd)
        return entry

    def audit_trail(self, *, chain_id: str, limit: int = 100) -> tuple[WatermarkEntry, ...]:
        entries = self._read_entries(chain_id)
        return tuple(entries[-limit:])

    def chain_count(self) -> int:
        if not os.path.isdir(self.root_dir):
            return 0
        return sum(1 for n in os.listdir(self.root_dir) if n.endswith(".log"))

    def close(self) -> None:
        # No persistent handle; nothing to release for this backend.
        return None


def view_to_trusted_watermark(view: WatermarkView) -> dict[str, Any]:
    """Adapter to the cycle 168 freshness gate trusted_watermark arg."""
    return {
        "seq": view.seq,
        "checkpoint_sha256": view.checkpoint_sha256,
        "entry_count": view.entry_count,
        "backend_name": view.backend_name,
        "backend_append_only": view.backend_append_only,
    }


def verify_promotion_allowed(store: WatermarkStore, *, chain_id: str) -> dict[str, Any]:
    """Conservative gate; never promotes, only reports."""
    view = store.get_watermark(chain_id=chain_id)
    return {
        "decision": "candidate_hold",
        "watermark_seq": view.seq,
        "entry_count": view.entry_count,
        "backend_name": view.backend_name,
        "backend_append_only": view.backend_append_only,
        "writes_active_memory": False,
        "writes_production_state": False,
        "promotion_allowed": False,
        "status": "candidate_hold",
    }
