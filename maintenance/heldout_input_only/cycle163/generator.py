"""Fresh held-out fixture generator executed as a separate process."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import time
from pathlib import Path

PROBE_TYPES = ("factual", "counterexample", "transfer")


def digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--canary", required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)

    public = []
    expected = {}
    for index, probe_type in enumerate(PROBE_TYPES):
        token = secrets.token_hex(6)
        value = f"mix-{index}-{token}-Az"
        probe_id = f"fresh-{index}-{secrets.token_hex(4)}"
        public.append(
            {
                "probe_id": probe_id,
                "probe_type": probe_type,
                "stdin": value + "\n",
                "custody_canary": args.canary,
            }
        )
        expected[probe_id] = {"exit_code": 0, "stdout": value.upper() + "\n"}

    public_path = args.output_dir / "public_inputs.json"
    sealed_path = args.output_dir / "sealed_expected.json"
    public_path.write_text(json.dumps(public, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sealed_path.write_text(
        json.dumps({"custody_canary": args.canary, "expected": expected}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    receipt = {
        "generator_pid": os.getpid(),
        "generated_ns": time.time_ns(),
        "public_sha256": hashlib.sha256(public_path.read_bytes()).hexdigest(),
        "sealed_sha256": hashlib.sha256(sealed_path.read_bytes()).hexdigest(),
        "public_schema_digest": digest(sorted(public[0].keys())),
    }
    (args.output_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
