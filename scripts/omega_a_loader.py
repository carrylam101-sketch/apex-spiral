#!/usr/bin/env python3
"""APEX Harness/Ralph Omega_A loader.

Loads the local APEX state bundle used by the Harness gate:
- evolution registry and genes
- local memory footprint
- session anchor metadata

The script is intentionally read-only and emits JSON for cron verification.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path('/home/ubuntu/apex-spiral')
REGISTRY = ROOT / 'evolution' / 'registry.json'
GENE_DIR = ROOT / 'evolution' / 'genes'
MEMORY_DIR = ROOT / 'memory'
ANCHOR = Path('/tmp/hermes_session_anchor.json')


def _cycle_num(key: str) -> int:
    match = re.search(r'cycle_(\d+)', key)
    return int(match.group(1)) if match else -1


def _safe_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        return json.loads(path.read_text()), None
    except Exception as exc:  # pragma: no cover - surfaced in CLI output
        return {}, f'{type(exc).__name__}: {exc}'


def _dir_size_kb(path: Path) -> float:
    if not path.exists():
        return 0.0
    total = 0
    for item in path.rglob('*'):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                pass
    return round(total / 1024.0, 3)


def load_omega_a() -> dict[str, Any]:
    registry, registry_error = _safe_json(REGISTRY)
    anchor, anchor_error = _safe_json(ANCHOR) if ANCHOR.exists() else ({}, 'missing')
    cycles = registry.get('cycles', {}) if isinstance(registry, dict) else {}
    head_key = max(cycles, key=_cycle_num) if cycles else None
    gene_files = sorted(GENE_DIR.glob('*.json')) if GENE_DIR.exists() else []
    unique_gene_ids: set[str] = set()
    bad_gene_json: list[str] = []
    for gene_file in gene_files:
        gene, err = _safe_json(gene_file)
        if err:
            bad_gene_json.append(gene_file.name)
            continue
        gid = str(gene.get('gene_id') or gene.get('id') or '').replace('gene_', '')
        if gid:
            unique_gene_ids.add(gid)
    sections = [
        'hermes_agent_defect_genes',
        'orchestrator_truth_gate_genes',
        'apex_devour_genes',
        'claw_native_evolution_genes',
        'vlm_agentic_genes',
    ]
    registry_ids: set[str] = set()
    for section in sections:
        for gid in registry.get(section, {}).keys() if isinstance(registry, dict) else []:
            registry_ids.add(str(gid).replace('gene_', ''))
    return {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'root': str(ROOT),
        'registry': {
            'path': str(REGISTRY),
            'ok': registry_error is None,
            'error': registry_error,
            'head_cycle': head_key,
            'head_delta_g': cycles.get(head_key, {}).get('delta_g') if head_key else None,
            'cycle_count': len(cycles),
        },
        'genes': {
            'file_count': len(gene_files),
            'unique_gene_ids': len(unique_gene_ids),
            'registry_ids': len(registry_ids),
            'bad_json': bad_gene_json,
            'orphaned_file_ids': sorted(unique_gene_ids - registry_ids),
            'registry_without_file': sorted(registry_ids - unique_gene_ids),
        },
        'memory': {
            'path': str(MEMORY_DIR),
            'exists': MEMORY_DIR.exists(),
            'size_kb': _dir_size_kb(MEMORY_DIR),
        },
        'anchor': {
            'path': str(ANCHOR),
            'ok': anchor_error is None,
            'error': anchor_error,
            'last_updated': anchor.get('last_updated'),
            'active_task': anchor.get('active_task', {}).get('what') if isinstance(anchor, dict) else None,
            'phase': anchor.get('active_task', {}).get('phase') if isinstance(anchor, dict) else None,
        },
    }


if __name__ == '__main__':
    print(json.dumps(load_omega_a(), ensure_ascii=False, indent=2, sort_keys=True))
