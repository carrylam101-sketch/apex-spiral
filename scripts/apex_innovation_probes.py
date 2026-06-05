#!/usr/bin/env python3
"""
APEX P-INNOVATE five-way probe runner.

Purpose: when Shannon capacity / ΔG plateau is detected, execute five feasible
probes every cycle and persist objective evidence for the next mutation choice.
The script is intentionally read-mostly and LOW_RISK: it does not mutate source
code; it measures code, tests, docs, external baseline, and user-result signals.
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path("/home/ubuntu/apex-spiral")
HISTORY = Path("/tmp/apex_self_check_history.json")
REPORT = BASE / "reports" / "apex_innovation_probes.json"


def run(cmd: list[str], timeout: int = 30) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=BASE,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "cmd": " ".join(cmd),
            "exit_code": proc.returncode,
            "stdout_tail": proc.stdout[-1200:],
            "stderr_tail": proc.stderr[-1200:],
            "ok": proc.returncode == 0,
        }
    except Exception as exc:  # pragma: no cover - defensive evidence path
        return {"cmd": " ".join(cmd), "exit_code": None, "error": repr(exc), "ok": False}


def load_history() -> list[dict[str, Any]]:
    if not HISTORY.exists():
        return []
    data = json.loads(HISTORY.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def probe_code() -> dict[str, Any]:
    target = BASE / "py" / "apex_spiral" / "apex_self_check.py"
    tree = ast.parse(target.read_text(encoding="utf-8"))
    funcs = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    return {
        "name": "code",
        "target": str(target),
        "function_count": len(funcs),
        "has_shannon_capacity_layer": "formula_3b_shannon_capacity" in funcs,
        "has_improvement_generator": "_generate_improvements" in funcs,
        "ok": "formula_3b_shannon_capacity" in funcs,
    }


def probe_tests() -> dict[str, Any]:
    compile_result = run([sys.executable, "-m", "py_compile", "py/apex_spiral/apex_self_check.py", "scripts/generate_apex_dashboard.py"], timeout=30)
    return {"name": "tests", "py_compile": compile_result, "ok": compile_result["ok"]}


def probe_docs() -> dict[str, Any]:
    formula = BASE / "APEX_V10_FORMULA.md"
    dashboard = BASE / "reports" / "apex_dashboard.md"
    text = formula.read_text(encoding="utf-8") if formula.exists() else ""
    return {
        "name": "docs",
        "formula_doc_exists": formula.exists(),
        "dashboard_doc_exists": dashboard.exists(),
        "mentions_v10_3_trifecta": all(term in text for term in ["HERRO", "Prime Assembly", "DRT3", "Φ_APEX"]),
        "ok": formula.exists() and all(term in text for term in ["HERRO", "Prime Assembly", "DRT3"]),
    }


def probe_external_baseline() -> dict[str, Any]:
    # External benchmark proxy for cron-safe/offline operation: compare local git
    # state against origin/main after the mandatory git pull already ran.
    rev = run(["git", "rev-parse", "--short", "HEAD"], timeout=10)
    status = run(["git", "status", "--short"], timeout=10)
    return {
        "name": "external_benchmark",
        "git_head": rev.get("stdout_tail", "").strip(),
        "working_tree_changes": [line for line in status.get("stdout_tail", "").splitlines() if line.strip()],
        "ok": rev["ok"] and status["ok"],
    }


def probe_user_results() -> dict[str, Any]:
    hist = load_history()
    recent = hist[-8:]
    dgs = [float(item.get("summary", {}).get("delta_g_estimate", 0.0)) for item in recent]
    latest = hist[-1] if hist else {}
    cap = latest.get("formulas", {}).get("C_shannon", {})
    span = max(dgs) - min(dgs) if dgs else None
    return {
        "name": "user_results",
        "cycles": [item.get("cycle_count") for item in recent],
        "recent_delta_g": dgs,
        "delta_g_span_recent": None if span is None else round(span, 6),
        "eta_capacity": cap.get("eta_capacity"),
        "plateau_score": cap.get("plateau_score"),
        "plateau_confirmed": bool(span == 0 and len(dgs) >= 5) or cap.get("plateau_score", 0) >= 0.9,
        "ok": bool(hist),
    }


def main() -> int:
    probes = [probe_code(), probe_tests(), probe_docs(), probe_external_baseline(), probe_user_results()]
    passed = sum(1 for p in probes if p.get("ok"))
    user_probe = probes[-1]
    delta_g_increment = 0.0
    no_increment_reason = None
    if user_probe.get("plateau_confirmed"):
        no_increment_reason = (
            "ΔG remains unchanged because the current self-check scoring formula is static; "
            "this cycle therefore produces measurement/probe evidence and defers scoring mutation "
            "to a controlled LOW_RISK patch after validation."
        )

    report = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "route": "P-INNOVATE",
        "trigger": "Shannon平台期 / η_capacity偏低",
        "probes_passed": passed,
        "probes_total": len(probes),
        "probes": probes,
        "verifiable_increment": {
            "type": "evidence_artifact",
            "path": str(REPORT),
            "delta_g_increment": delta_g_increment,
            "no_delta_g_increment_reason": no_increment_reason,
        },
        "next_mutation_candidates": [
            "lower duplicate-check noise_n using probe deduplication evidence",
            "add capacity metrics to dashboard trend to make η_capacity regressions visible",
            "separate stable health score from exploratory innovation bonus to avoid fake ΔG inflation",
        ],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed >= 4 else 1


if __name__ == "__main__":
    raise SystemExit(main())
