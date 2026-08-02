"""Off-host sealed-expected evaluator interface contract.

Defines the wire contract for an evaluator that lives on a different host
than the candidate, so the candidate never observes the expected output
in argv / env / cwd / local files. This module is contract-only; the
actual network transport and trust bootstrap are environment concerns.

Hard boundary: this interface MUST NOT include any code path that
materialises the expected output on the candidate host (filesystem,
environment, stdin, or stdout). The only allowed data flow for the
expected output is the signed attestation blob returned over the
transport, addressed by hash, not by path.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from typing import Any, Mapping

# Off-host transport channels we acknowledge. The candidate process is
# REQUIRED to use one of these; local-only channels (file path, env var,
# argv, stdin) are explicitly forbidden by the contract and rejected by
# the gate.
ALLOWED_TRANSPORTS = frozenset({"unix_socket", "https", "tor_onion"})

# Required request fields. Any missing field fails the contract.
REQUIRED_REQUEST_FIELDS = ("candidate_id", "candidate_sha256", "challenge_nonce")
REQUIRED_ATTESTATION_FIELDS = ("verdict", "expected_sha256", "signed_at", "attestation_sig")


@dataclass(frozen=True)
class OffHostRequest:
    """A signed challenge the candidate sends to the remote evaluator."""

    candidate_id: str
    candidate_sha256: str
    challenge_nonce: str
    transport: str
    transport_target: str
    extra: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.transport not in ALLOWED_TRANSPORTS:
            errors.append(f"transport_not_offhost:{self.transport}")
        if not self.candidate_id:
            errors.append("candidate_id_empty")
        if not self.challenge_nonce:
            errors.append("challenge_nonce_empty")
        if not self._is_hex64(self.candidate_sha256):
            errors.append("candidate_sha256_not_hex64")
        if not self.transport_target:
            errors.append("transport_target_empty")
        for required in REQUIRED_REQUEST_FIELDS:
            if not getattr(self, required, ""):
                errors.append(f"missing_field:{required}")
        return errors

    @staticmethod
    def _is_hex64(value: str) -> bool:
        return isinstance(value, str) and len(value) == 64 and all(
            ch in "0123456789abcdef" for ch in value.lower()
        )

    def envelope(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "candidate_sha256": self.candidate_sha256,
            "challenge_nonce": self.challenge_nonce,
            "transport": self.transport,
            "transport_target": self.transport_target,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class OffHostAttestation:
    """A signed verdict returned by the remote evaluator."""

    verdict: str
    expected_sha256: str
    signed_at: str
    attestation_sig: str
    evaluator_pubkey_sha256: str

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.verdict not in {"pass", "fail", "inconclusive"}:
            errors.append("verdict_not_in_alphabet")
        if not self._is_hex64(self.expected_sha256):
            errors.append("expected_sha256_not_hex64")
        if not self.signed_at:
            errors.append("signed_at_empty")
        if not self.attestation_sig:
            errors.append("attestation_sig_empty")
        elif not self._is_hex_like(self.attestation_sig):
            errors.append("attestation_sig_not_hex")
        if not self._is_hex64(self.evaluator_pubkey_sha256):
            errors.append("evaluator_pubkey_sha256_not_hex64")
        for required in REQUIRED_ATTESTATION_FIELDS:
            if not getattr(self, required, ""):
                errors.append(f"missing_field:{required}")
        return errors

    @staticmethod
    def _is_hex64(value: str) -> bool:
        return isinstance(value, str) and len(value) == 64 and all(
            ch in "0123456789abcdef" for ch in value.lower()
        )

    @staticmethod
    def _is_hex_like(value: str) -> bool:
        return isinstance(value, str) and len(value) > 0 and all(
            ch in "0123456789abcdef" for ch in value.lower()
        )


def expected_payload_hash(payload: Mapping[str, Any]) -> str:
    """Deterministic hash of an expected-output payload (used for offline replay)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sign_attestation(
    payload: Mapping[str, Any], secret_key: bytes
) -> OffHostAttestation:
    """Helper used by the offline replay harness only.

    The real production signature is performed on the remote host by a
    separate process with a hardware-backed key. This helper exists so the
    offline replay test can deterministically exercise the same wire format.
    """
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                ensure_ascii=False).encode("utf-8")
    sig = hmac.new(secret_key, payload_bytes, hashlib.sha256).hexdigest()
    return OffHostAttestation(
        verdict=str(payload.get("verdict", "inconclusive")),
        expected_sha256=str(payload.get("expected_sha256", "")),
        signed_at=str(payload.get("signed_at", "")),
        attestation_sig=sig,
        evaluator_pubkey_sha256=hashlib.sha256(secret_key).hexdigest(),
    )