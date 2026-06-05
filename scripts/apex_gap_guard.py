#!/usr/bin/env python3
"""
APEX gap guard: detect hidden/latent weaknesses even when status=HEALTHY.
Checks:
1) ΔG plateau for too long
2) Ψ_cross low-ceiling risk
3) Memory crystal floor regression risk
"""
import json
from pathlib import Path

HIST = Path('/tmp/apex_self_check_history.json')
OUT = Path('/home/ubuntu/apex-spiral/reports/apex_gap_guard.json')

if not HIST.exists():
    raise SystemExit('history file not found')

data = json.loads(HIST.read_text(encoding='utf-8'))
if not isinstance(data, list) or not data:
    raise SystemExit('history empty')

last10 = data[-10:]
last5 = data[-5:]
latest = data[-1]

# Helpers

def dg(x):
    return float(x.get('summary', {}).get('delta_g_estimate', 0.0))

def psi(x):
    return float(x.get('formulas', {}).get('Ψ_cross', {}).get('psi_cross', 0.0))

def mem(x):
    return float(x.get('formulas', {}).get('M_mem', {}).get('m_crystal', 0.0))

warnings = []
actions = []

# 1) Plateau: if last 5 ΔG exactly same -> hidden optimization stall risk
dg5 = [round(dg(x), 4) for x in last5]
if len(set(dg5)) == 1:
    warnings.append('ΔG plateau: last 5 cycles unchanged')
    actions.append('Introduce one controlled micro-mutation per cycle for exploration (prompt/validation policy).')

# 2) Ψ_cross low ceiling risk (still pass but growth bottleneck)
psi_now = psi(latest)
if psi_now < 0.50:
    warnings.append(f'Ψ_cross ceiling risk: current {psi_now:.4f} < 0.50')
    actions.append('Increase cross-domain retrieval + adversarial verification pair before final answer.')

# 3) Memory floor risk
mem_now = mem(latest)
if mem_now < 0.88:
    warnings.append(f'M_mem headroom: current m_crystal {mem_now:.4f} < 0.88')
    actions.append('Shorten memory consolidation cycle and add post-task reflection writeback gate.')

policy = {
    'enable_micro_mutation': any('ΔG plateau' in w for w in warnings),
    'mutation_intensity': 0.003 if any('ΔG plateau' in w for w in warnings) else 0.0,
    'targets': ['DRT3.T_prot', 'DRT3.D_dup'] if any('ΔG plateau' in w for w in warnings) else []
}

report = {
    'cycle': latest.get('cycle_count'),
    'status': latest.get('summary', {}).get('status'),
    'delta_g': dg(latest),
    'warnings': warnings,
    'actions': actions,
    'policy': policy,
    'ok': len(warnings) == 0
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

policy_out = Path('/tmp/apex_mutation_policy.json')
policy_out.write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding='utf-8')

print(json.dumps(report, ensure_ascii=False, indent=2))
print(f'policy written: {policy_out}')
