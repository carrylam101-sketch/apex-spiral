#!/usr/bin/env python3
"""APEX Ralph termination indicator I(neg V_H).

Current minimal V_H: EVM must be healthy, registry JSON must parse, and no gene
orphan scan failures. I_continue is True when V_H is not satisfied.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/home/ubuntu/apex-spiral')
EVM_PY = Path('/home/ubuntu/.hermes/venv-evm/bin/python')
EVM_ROOT = Path('/home/ubuntu/EVM-Entropy-Vibe-Mathing')


def evm_status() -> dict:
 code = (
  "import sys,json; sys.path.insert(0, '/home/ubuntu/EVM-Entropy-Vibe-Mathing'); "
  "from CoreFormula.EVM_FORMULA import EVMCore; evm=EVMCore(); s=evm.get_status(); "
  "print(json.dumps({'evm': round(evm.calculate_evm(),4), 'defect_rate': s.get('defect_rate')}))"
 )
 env = {'PYTHONPATH': str(EVM_ROOT)}
 cp = subprocess.run([str(EVM_PY), '-c', code], text=True, capture_output=True, env=env, timeout=20)
 if cp.returncode !=0:
  return {'ok': False, 'error': cp.stderr.strip() or cp.stdout.strip()}
 data = json.loads(cp.stdout)
 data['ok'] = data.get('evm') ==0.7691 and data.get('defect_rate') ==0.0
 return data


def registry_status() -> dict:
 try:
  reg = json.loads((ROOT / 'evolution' / 'registry.json').read_text())
 except Exception as exc:
  return {'ok': False, 'error': f'{type(exc).__name__}: {exc}'}
 sections = ['hermes_agent_defect_genes', 'orchestrator_truth_gate_genes', 'apex_devour_genes', 'claw_native_evolution_genes', 'vlm_agentic_genes', 'self_reflexion_genes']
 reg_ids = set()
 for section in sections:
  for gid in reg.get(section, {}).keys():
   reg_ids.add(str(gid).replace('gene_', ''))
 file_ids = set()
 bad_json = []
 for file in (ROOT / 'evolution' / 'genes').glob('*.json'):
  try:
   gene = json.loads(file.read_text())
   file_ids.add(str(gene.get('gene_id') or gene.get('id')).replace('gene_', ''))
  except Exception:
   bad_json.append(file.name)
 orphaned = sorted(file_ids - reg_ids)
 missing = sorted(reg_ids - file_ids)
 return {'ok': not bad_json and not orphaned and not missing, 'bad_json': bad_json, 'orphaned': orphaned, 'registry_without_file': missing}


def main() -> None:
 parser = argparse.ArgumentParser()
 parser.add_argument('--json', action='store_true')
 parser.parse_args()
 evm = evm_status()
 registry = registry_status()
 v_h = bool(evm.get('ok') and registry.get('ok'))
 report = {
  'timestamp': datetime.now(timezone.utc).isoformat(),
  'V_H': v_h,
  'I_continue': not v_h,
  'evm': evm,
  'registry': registry,
 }
 print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == '__main__':
 main()
