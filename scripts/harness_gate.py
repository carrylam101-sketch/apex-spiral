#!/usr/bin/env python3
"""APEX Harness feed-forward risk gate.

Risk(a)=w1*C+w2*R+w3*P, where:
- C: code/change risk
- R: runtime/resource risk
- P: policy/path/provenance risk

This gate is conservative and deterministic. It does not execute the action;
it only decides whether an APEX cron action should proceed, warn, or block.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class HarnessRisk:
    action: str
    c_code_change: float
    r_runtime: float
    p_provenance: float
    risk_score: float
    decision: str
    threshold_warn: float = 0.35
    threshold_block: float = 0.65


def clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def score_action(action: str, *, writes_files: bool, runs_network: bool, touches_system: bool,
                 has_tests: bool, path_exists: bool) -> HarnessRisk:
    text = action.lower()
    c = 0.15
    r = 0.10
    p = 0.10
    if writes_files:
        c += 0.25
    if any(token in text for token in ['registry', 'soul', 'skill', 'cron', 'config']):
        c += 0.15
    if runs_network:
        r += 0.25
    if touches_system:
        r += 0.30
        p += 0.15
    if not has_tests:
        c += 0.15
    else:
        c -= 0.10
    if not path_exists:
        p += 0.25
    if any(token in text for token in ['delete', 'remove', 'rm ', 'sudo', 'secret', 'token']):
        p += 0.25
    c, r, p = clamp(c), clamp(r), clamp(p)
    risk = round(0.40 * c + 0.35 * r + 0.25 * p, 6)
    decision = 'allow'
    if risk >= 0.65:
        decision = 'block'
    elif risk >= 0.35:
        decision = 'warn'
    return HarnessRisk(action, c, r, p, risk, decision)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--action', required=True)
    parser.add_argument('--path', default='/home/ubuntu/apex-spiral')
    parser.add_argument('--writes-files', action='store_true')
    parser.add_argument('--runs-network', action='store_true')
    parser.add_argument('--touches-system', action='store_true')
    parser.add_argument('--has-tests', action='store_true')
    args = parser.parse_args()
    report = score_action(
        args.action,
        writes_files=args.writes_files,
        runs_network=args.runs_network,
        touches_system=args.touches_system,
        has_tests=args.has_tests,
        path_exists=Path(args.path).exists(),
    )
    out = asdict(report)
    out['timestamp'] = datetime.now(timezone.utc).isoformat()
    out['path'] = args.path
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
