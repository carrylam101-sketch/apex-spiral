"""Candidate gate for OS-level held-out expected-output isolation.

The gate probes whether a candidate subprocess can be placed under a distinct
OS identity or user namespace before any sealed expected-output path is used.
If neither mechanism is available, evaluation fails closed and promotion stays
disabled. This gate detects missing isolation; it does not emulate isolation.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any

NOBODY_UID = 65534
NOBODY_GID = 65534


def _run_probe(argv: list[str], timeout_seconds: float = 2.0) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            argv,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
        return {
            "argv0": argv[0],
            "available": True,
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "argv0": argv[0],
            "available": False,
            "returncode": None,
            "stdout": "",
            "stderr": type(exc).__name__,
        }


def probe_isolation_capabilities() -> dict[str, Any]:
    setpriv = shutil.which("setpriv")
    unshare = shutil.which("unshare")
    setpriv_probe = (
        _run_probe(
            [
                setpriv,
                f"--reuid={NOBODY_UID}",
                f"--regid={NOBODY_GID}",
                "--clear-groups",
                "id",
                "-u",
            ]
        )
        if setpriv
        else {"argv0": "setpriv", "available": False, "returncode": None, "stdout": "", "stderr": "not_found"}
    )
    unshare_probe = (
        _run_probe([unshare, "--user", "--map-root-user", "id", "-u"])
        if unshare
        else {"argv0": "unshare", "available": False, "returncode": None, "stdout": "", "stderr": "not_found"}
    )
    setpriv_works = setpriv_probe["returncode"] == 0 and setpriv_probe["stdout"] == str(NOBODY_UID)
    unshare_works = unshare_probe["returncode"] == 0 and unshare_probe["stdout"] == "0"
    return {
        "evaluator_uid": os.getuid(),
        "setpriv": setpriv_probe,
        "unshare_user_namespace": unshare_probe,
        "distinct_uid_verified": setpriv_works,
        "user_namespace_verified": unshare_works,
        "isolation_mechanism_available": setpriv_works or unshare_works,
    }


def isolation_gate(capabilities: dict[str, Any] | None = None) -> dict[str, Any]:
    capabilities = capabilities or probe_isolation_capabilities()
    isolated = capabilities.get("isolation_mechanism_available") is True
    reasons = [] if isolated else ["os_identity_or_user_namespace_isolation_unavailable"]
    return {
        "decision": "candidate_verify" if isolated else "hold",
        "reasons": reasons,
        "mechanism": "capability_gated_os_expected_isolation",
        "capabilities": capabilities,
        "candidate_execution_started": False,
        "sealed_expected_path_disclosed": False,
        "os_level_secrecy_verified": False,
        "organizational_independence_verified": False,
        "promotion_allowed": False,
        "status": "candidate_hold",
    }


def main() -> int:
    print(json.dumps(isolation_gate(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
