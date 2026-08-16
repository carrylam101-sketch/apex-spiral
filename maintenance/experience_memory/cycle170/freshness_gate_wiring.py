"""Cycle 170 wiring: cycle 168 freshness gate consumes cycle 169 WatermarkStore.

This module does NOT replace cycle168/freshness_gate.py. It provides an additive
entry point that calls the original verify_fresh_checkpoint with the same
freshness invariants, but resolves the watermark from a WatermarkStore view
when one is supplied. The internal logic is preserved byte-for-byte: only the
input adapter changes.

Strict boundary declarations:
1. verify_fresh_checkpoint is unchanged. Callers that pass inline dict
   watermarks keep working without any modification.
2. verify_fresh_checkpoint_v2 is a thin adapter: it pulls a view from the
   store, adapts it to the inline dict shape the original function already
   accepts, then delegates. It never mutates the store.
3. The promotion_allowed flag remains False. No code path here writes to the
   WatermarkStore; promotion remains a separate, human-reviewed step.
4. When watermark_source is None, v2 falls back to a strict "inline dict only"
   path identical to the legacy verify_fresh_checkpoint semantics.
5. Writes_active_memory / Writes_trusted_watermark / promotion_allowed fields
   in the returned dict keep the cycle 168 contract.
6. backend_append_only is exposed as a NEW optional observability field so
   callers can audit the source of the watermark they just verified against.
   Existing consumers that destructure specific keys are unaffected.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


FRESHNESS = _load(
    "experience_memory_freshness_gate_cycle168",
    ROOT / "maintenance" / "experience_memory" / "cycle168" / "freshness_gate.py",
)
WATERMARK_STORE = _load(
    "experience_memory_watermark_store_cycle169",
    ROOT / "maintenance" / "experience_memory" / "cycle169" / "watermark_store.py",
)


def _view_to_legacy_watermark(view: Any) -> dict[str, Any]:
    """Adapter from cycle 169 WatermarkView back to cycle 168 inline-dict shape.

    The cycle 168 verify_fresh_checkpoint reads these two keys:
        trusted_watermark.get("checkpoint_seq")
        trusted_watermark.get("checkpoint_sha256")

    The cycle 169 view_to_trusted_watermark emits them as "seq" instead of
    "checkpoint_seq". We rename here so the legacy logic keeps working.
    """
    return {
        "checkpoint_seq": view.seq,
        "checkpoint_sha256": view.checkpoint_sha256,
        "entry_count": view.entry_count,
        "backend_name": view.backend_name,
        "backend_append_only": view.backend_append_only,
    }


def verify_fresh_checkpoint_v2(
    *,
    chain_report: dict[str, Any],
    checkpoint: dict[str, Any],
    expected_chain_id: str,
    trusted_public_keys: dict[str, Any],
    trusted_watermark: dict[str, Any] | None = None,
    watermark_source: Any = None,
    source_chain_id: str | None = None,
) -> dict[str, Any]:
    """Additive wiring entry point.

    Resolution rule for the trusted watermark (mutually exclusive):
      1. If watermark_source is provided (and source_chain_id is set), pull a
         WatermarkView from the store and adapt it to the legacy shape.
      2. Otherwise, use the trusted_watermark inline dict exactly as the
         legacy verify_fresh_checkpoint expects.

    Passing both is a programmer error: watermark_source wins, trusted_watermark
    is ignored, but a 'watermark_source_overrides_inline_dict' reason is added
    to the result to make the override observable.
    """
    reasons_override: list[str] = []

    if watermark_source is not None:
        if source_chain_id is None:
            raise ValueError(
                "watermark_source requires source_chain_id; "
                "WatermarkStore.get_watermark is keyed by chain_id"
            )
        view = watermark_source.get_watermark(chain_id=source_chain_id)
        resolved_watermark = _view_to_legacy_watermark(view)
        if trusted_watermark is not None:
            reasons_override.append("watermark_source_overrides_inline_dict")
    elif trusted_watermark is None:
        raise ValueError(
            "verify_fresh_checkpoint_v2 requires either watermark_source "
            "or trusted_watermark (inline dict)"
        )
    else:
        resolved_watermark = trusted_watermark

    result = FRESHNESS.verify_fresh_checkpoint(
        chain_report=chain_report,
        checkpoint=checkpoint,
        expected_chain_id=expected_chain_id,
        trusted_public_keys=trusted_public_keys,
        trusted_watermark=resolved_watermark,
    )

    if reasons_override:
        result["reasons"] = list(result.get("reasons", [])) + reasons_override

    if watermark_source is not None:
        view_after = watermark_source.get_watermark(chain_id=source_chain_id)
        result["watermark_backend_name"] = view_after.backend_name
        result["watermark_backend_append_only"] = view_after.backend_append_only
        result["watermark_entry_count"] = view_after.entry_count
        result["watermark_source_provided"] = True
        result["writes_trusted_watermark"] = False
        result["promotion_allowed"] = False
        result["status"] = "candidate_hold"
    else:
        result["watermark_source_provided"] = False

    return result


__all__ = [
    "verify_fresh_checkpoint_v2",
    "FRESHNESS",
    "WATERMARK_STORE",
]