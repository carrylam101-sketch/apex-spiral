#!/usr/bin/env python3
"""Run one minimal APEX x Harness x Ralph verification cycle."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/home/ubuntu/apex-spiral')


def run(cmd: list[str]) -> dict:
    cp = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True, timeout=60)
    return {'cmd': cmd, 'returncode': cp.returncode, 'stdout': cp.stdout.strip(), 'stderr': cp.stderr.strip()}


def main() -> None:
    omega = run(['python3', 'scripts/omega_a_loader.py'])
    harness = run(['python3', 'scripts/harness_gate.py', '--action', 'APEX cron read-only verification with report write', '--path', str(ROOT), '--writes-files', '--has-tests'])
    indicator = run(['python3', 'scripts/indicator.py', '--json'])
    parsed = {}
    for name, result in [('omega', omega), ('harness', harness), ('indicator', indicator)]:
        try:
            parsed[name] = json.loads(result['stdout'])
        except Exception as exc:
            parsed[name] = {'parse_error': f'{type(exc).__name__}: {exc}'}
    report = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'cycle': 'apex_harness_ralph_minimal',
        'omega_ok': omega['returncode'] == 0 and parsed.get('omega', {}).get('registry', {}).get('ok') is True,
        'harness_decision': parsed.get('harness', {}).get('decision'),
        'harness_risk_score': parsed.get('harness', {}).get('risk_score'),
        'V_H': parsed.get('indicator', {}).get('V_H'),
        'I_continue': parsed.get('indicator', {}).get('I_continue'),
        'raw': {'omega': parsed.get('omega'), 'harness': parsed.get('harness'), 'indicator': parsed.get('indicator')},
        'commands': {'omega': omega, 'harness': harness, 'indicator': indicator},
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
