#!/usr/bin/env python3
"""ApexAGI seven-stage Hermes repair orchestrator.

This script is a governance driver, not a hot-switch mechanism. It records the
ApexAGI runtime contract, checks tool availability, computes a conservative
activation score, and emits a P7 task batch skeleton. Code execution must be
performed by external T workers and independently verified by O.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/home/ubuntu/apex-spiral')
STAGES = ['locate', 'plan', 'review', 'implement', 'code_review', 'verify', 'judge']


@dataclass
class ApexFactors:
    g_base: float = 0.50
    lambda_goal: float = 0.90
    theta_decomp: float = 0.80
    k_knowledge: float = 0.75
    xi_truth: float = 0.80
    psi_transfer: float = 0.70
    phi_harness: float = 0.85
    h_health_cost: float = 1.10
    t_cost: float = 1.20
    epsilon_noise: float = 1.10

    def delta_g(self) -> float:
        numerator = self.g_base * self.lambda_goal * self.theta_decomp * self.k_knowledge * self.xi_truth * self.psi_transfer * self.phi_harness
        denominator = self.h_health_cost * self.t_cost * self.epsilon_noise
        return round(numerator / denominator, 6)


def run(cmd: list[str], timeout: int = 60) -> dict:
    cp = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True, timeout=timeout)
    return {
        'cmd': cmd,
        'returncode': cp.returncode,
        'stdout': cp.stdout.strip(),
        'stderr': cp.stderr.strip(),
    }


def command_path(name: str) -> str | None:
    return shutil.which(name)


def docker_status() -> dict:
    docker = command_path('docker')
    if not docker:
        return {'installed': False, 'usable': False, 'error': 'docker not found'}
    probe = run([docker, 'version', '--format', '{{.Server.Version}}'], timeout=20)
    return {
        'installed': True,
        'path': docker,
        'usable': probe['returncode'] == 0,
        'probe': probe,
    }


def tool_inventory() -> dict:
    names = ['pi', 'dbexplain', 'cubesandbox', 'cube', 'docker', 'git', 'hermes', 'codex', 'gh']
    return {name: command_path(name) for name in names}


def p7_batch(defect: str, repo: str) -> list[dict]:
    return [
        {'stage': stage, 'owner': 'O' if stage in {'locate', 'plan', 'review', 'code_review', 'judge'} else 'T/Vt', 'status': 'pending', 'defect': defect, 'repo': repo}
        for stage in STAGES
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--defect', default='ApexAGI runtime activation preflight')
    parser.add_argument('--repo', default=str(ROOT))
    parser.add_argument('--authorize-hot-switch', action='store_true', help='Only records authorization flag; caller must still perform separate switch workflow.')
    args = parser.parse_args()

    factors = ApexFactors()
    docker = docker_status()
    tools = tool_inventory()
    harness = run(['python3', 'scripts/apex_harness_cycle.py'], timeout=90)
    gate = run(['./apex_devour/target/release/apex_devour', 'gate'], timeout=60)
    vt_replay = run(['python3', 'scripts/apex_agi_vt_replay_check.py'], timeout=60)

    report = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'runtime': 'ApexAGI',
        'formula': 'ApexAGI = O o P7 o T o Vt o Au, O_intersection_T = empty',
        'apex_factors': asdict(factors),
        'delta_g_activation': factors.delta_g(),
        'layers': {
            'O': 'orchestration/judgement only',
            'T': 'external coding agents only',
            'separation_invariant': True,
        },
        'p7_batch': p7_batch(args.defect, args.repo),
        'tool_inventory': tools,
        'docker_status': docker,
        'harness_cycle': harness,
        'apex_gate': gate,
        'vt_replay_check': vt_replay,
        'hot_switch': {
            'authorized_flag': bool(args.authorize_hot_switch),
            'effective': False,
            'reason': 'Separate explicit user authorization and successful Vt replay are required before any hot switch.',
        },
    }
    out_dir = ROOT / 'evolution' / 'reports'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / 'apex_agi_runtime_preflight.json'
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'ok': True, 'report_path': str(out_path), 'delta_g_activation': factors.delta_g(), 'docker_usable': docker.get('usable'), 'p7_stages': STAGES}, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
