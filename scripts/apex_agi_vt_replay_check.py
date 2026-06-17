#!/usr/bin/env python3
"""ApexAGI Vt replay readiness checker.

This is a verification adapter, not a production replay engine. It records
whether Docker or CubeSandbox-style replay can actually run on this host.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/home/ubuntu/apex-spiral')
OUT = ROOT / 'evolution' / 'reports' / 'apex_agi_vt_replay_check.json'


def run(cmd: list[str], timeout: int = 30) -> dict:
    try:
        cp = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True, timeout=timeout)
        return {
            'cmd': cmd,
            'returncode': cp.returncode,
            'stdout': cp.stdout.strip(),
            'stderr': cp.stderr.strip(),
        }
    except Exception as exc:  # noqa: BLE001 - diagnostic script
        return {'cmd': cmd, 'returncode': 999, 'stdout': '', 'stderr': repr(exc)}


def sock_info(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {'exists': False}
    st = p.stat()
    return {
        'exists': True,
        'mode': stat.filemode(st.st_mode),
        'uid': st.st_uid,
        'gid': st.st_gid,
        'is_socket': socket.S_ISSOCK(st.st_mode) if hasattr(socket, 'S_ISSOCK') else stat.S_ISSOCK(st.st_mode),
    }


def main() -> None:
    docker = shutil.which('docker')
    sudo = shutil.which('sudo')
    sg = shutil.which('sg')
    cubesandbox = shutil.which('cubesandbox')
    cube = shutil.which('cube')
    report = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'runtime': 'ApexAGI',
        'layer': 'Vt replay verification',
        'docker': {
            'path': docker,
            'sock': sock_info('/var/run/docker.sock'),
            'version_probe': run([docker, 'version', '--format', '{{.Server.Version}}'], timeout=20) if docker else None,
            'sudo_path': sudo,
            'sudo_version_probe': run([sudo, '-n', docker, 'version', '--format', '{{.Server.Version}}'], timeout=20) if docker and sudo else None,
            'sg_path': sg,
            'sg_docker_probe': run([sg, 'docker', '-c', "docker version --format '{{.Server.Version}}'"], timeout=20) if docker and sg else None,
        },
        'kvm': {
            'path': '/dev/kvm',
            'exists': Path('/dev/kvm').exists(),
            'stat': sock_info('/dev/kvm') if Path('/dev/kvm').exists() else None,
        },
        'cubesandbox': {
            'cubesandbox_path': cubesandbox,
            'cube_path': cube,
            'repo_compatibility_note': 'TencentCloud/CubeSandbox requires x86_64 Linux with KVM support; this host currently lacks /dev/kvm.',
        },
        'decision': None,
        'blockers': [],
        'next_actions': [],
    }
    docker_ok = bool(docker and report['docker']['version_probe']['returncode'] == 0)
    docker_sudo_ok = bool(docker and report['docker'].get('sudo_version_probe') and report['docker']['sudo_version_probe']['returncode'] == 0)
    docker_sg_ok = bool(docker and report['docker'].get('sg_docker_probe') and report['docker']['sg_docker_probe']['returncode'] == 0)
    kvm_ok = bool(report['kvm']['exists'])
    cube_ok = bool(cubesandbox or cube)
    if docker_ok or docker_sg_ok or docker_sudo_ok or (kvm_ok and cube_ok):
        if docker_ok:
            report['decision'] = 'replay_possible'
        elif docker_sg_ok:
            report['decision'] = 'replay_possible_with_docker_group_new_session'
        elif docker_sudo_ok:
            report['decision'] = 'replay_possible_with_sudo'
        else:
            report['decision'] = 'replay_possible'
    else:
        report['decision'] = 'replay_blocked'
        if not docker_ok and not docker_sg_ok and not docker_sudo_ok:
            report['blockers'].append('Docker replay unavailable: docker daemon/socket probe failed.')
            report['next_actions'].append('Add current user to docker group or run replay through a permitted service account, then restart session.')
        elif docker_sg_ok and not docker_ok:
            report['blockers'].append('Current process lacks refreshed docker group, but new docker group context works via sg; fresh login/session should make direct docker work.')
            report['next_actions'].append('Restart Hermes/gateway/login session so ubuntu group membership includes docker without sg.')
        elif docker_sudo_ok and not docker_ok:
            report['blockers'].append('Docker replay requires sudo in current session; direct user socket access still unavailable.')
            report['next_actions'].append('For non-sudo replay, add ubuntu to docker group and start a fresh login/session.')
        if not kvm_ok:
            report['blockers'].append('CubeSandbox replay unavailable: /dev/kvm missing.')
            report['next_actions'].append('Provision x86_64 Linux host with KVM support before deploying CubeSandbox.')
        if not cube_ok:
            report['blockers'].append('CubeSandbox CLI/service not installed on PATH.')
            report['next_actions'].append('Install and verify CubeSandbox only after KVM prerequisite is satisfied.')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'ok': True, 'decision': report['decision'], 'blockers': report['blockers'], 'report_path': str(OUT)}, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
