#!/usr/bin/env python3
import json, datetime
from pathlib import Path

base = Path('/home/ubuntu/apex-spiral')
reports = base / 'reports'
reports.mkdir(parents=True, exist_ok=True)

h = Path('/tmp/apex_self_check_history.json')
d = json.loads(h.read_text(encoding='utf-8'))
ln = d[-20:]
l5 = d[-5:]
cur = d[-1]

keys = ['Φ_anti', 'Ψ_cross', 'H(X)', 'C_shannon', '𝒯_full', 'M_mem']

def vv(i, k):
    x = i.get('formulas', {}).get(k, {})
    return {
        'Φ_anti': float(x.get('phi_anti', 0)),
        'Ψ_cross': float(x.get('psi_cross', 0)),
        'H(X)': float(x.get('h_x', 0)),
        'C_shannon': float(x.get('eta_capacity', 0)),
        '𝒯_full': float(x.get('q_traj', 0)),
        'M_mem': float(x.get('m_crystal', 0)),
    }[k]

def nm(k, x):
    if k == 'H(X)':
        return max(0, min(1, x / 3.0))
    if k == 'C_shannon':
        # η_capacity target is 0.35; normalize to expose plateau bottlenecks on radar.
        return max(0, min(1, x / 0.35))
    return max(0, min(1, x))

avg = {k: round(sum(nm(k, vv(i, k)) for i in ln) / len(ln), 4) for k in keys}
lat = {k: round(nm(k, vv(cur, k)), 4) for k in keys}

cy = [int(i.get('cycle_count', 0)) for i in l5]
dg = [round(float(i.get('summary', {}).get('delta_g_estimate', 0)), 4) for i in l5]
fd = [int(i.get('summary', {}).get('findings_count', 0)) for i in l5]
st = [i.get('summary', {}).get('status', '') for i in l5]
cap = [round(float(i.get('formulas', {}).get('C_shannon', {}).get('capacity_c', 0)), 4) for i in l5]
eta = [round(float(i.get('formulas', {}).get('C_shannon', {}).get('eta_capacity', 0)), 4) for i in l5]
ps = [round(float(i.get('formulas', {}).get('C_shannon', {}).get('plateau_score', 0)), 4) for i in l5]
cur_cap = cur.get('formulas', {}).get('C_shannon', {})
summary_path = reports / 'apex_cycle_summary_latest.json'
summary = json.loads(summary_path.read_text(encoding='utf-8')) if summary_path.exists() else {}
neuro_gate = summary.get('neuro_cell_gate', {})
github_v103 = summary.get('github_v10_3_self_loop', {})
up = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

md = [
    '# APEX 五环短板雷达看板',
    f'- 更新时间: {up}',
    f'- 当前循环: {cur.get("cycle_count")}',
    f'- 当前状态: {cur.get("summary", {}).get("status")}',
    f'- 当前 ΔG: {cur.get("summary", {}).get("delta_g_estimate")}',
    f'- Shannon容量 C: {cur_cap.get("capacity_c")} | η_capacity: {cur_cap.get("eta_capacity")} | plateau_score: {cur_cap.get("plateau_score")}',
    f'- Neuro-Cell: Π_neuro={neuro_gate.get("Π_neuro", "n/a")} | Ω_cell={neuro_gate.get("Ω_cell", "n/a")} | ΔG_candidate={neuro_gate.get("ΔG_candidate", "n/a")}',
    f'- GitHub V10.3 Self Loop: G_self_loop={github_v103.get("G_self_loop", "n/a")} | ΔG_v10_3_candidate={github_v103.get("ΔG_v10_3_candidate", "n/a")}',
    '',
    '## 五环雷达（归一化 0~1）'
]
for k in keys:
    md.append(f'- {k}: 最新 {lat[k]:.4f} / 20轮均值 {avg[k]:.4f}')
md += ['', '## 最近5轮趋势', '| cycle | ΔG | C_shannon | η_capacity | plateau | findings | status |', '|---:|---:|---:|---:|---:|---:|---|']
for c, dd, cc, ee, pp, f, s in zip(cy, dg, cap, eta, ps, fd, st):
    md.append(f'| {c} | {dd:.4f} | {cc:.4f} | {ee:.4f} | {pp:.4f} | {f} | {s} |')
(reports / 'apex_dashboard.md').write_text('\n'.join(md), encoding='utf-8')

# HTML dashboard (Chart.js radar + line trend)
labels_json = json.dumps(keys, ensure_ascii=False)
latest_json = json.dumps([lat[k] for k in keys], ensure_ascii=False)
avg_json = json.dumps([avg[k] for k in keys], ensure_ascii=False)
cy_json = json.dumps(cy, ensure_ascii=False)
dg_json = json.dumps(dg, ensure_ascii=False)
cap_json = json.dumps(cap, ensure_ascii=False)
eta_json = json.dumps(eta, ensure_ascii=False)
ps_json = json.dumps(ps, ensure_ascii=False)

html = f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>APEX Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #222; }}
    .meta {{ margin-bottom: 16px; }}
    .cards {{ display: grid; grid-template-columns: repeat(3, minmax(180px, 1fr)); gap: 12px; margin: 16px 0 24px; }}
    .card {{ border: 1px solid #e6e8ef; border-radius: 10px; padding: 12px 14px; background: #fafbff; }}
    .card b {{ display:block; margin-bottom: 6px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
    canvas {{ background: #fff; border: 1px solid #eee; border-radius: 8px; padding: 8px; }}
    table {{ border-collapse: collapse; margin-top: 16px; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: right; }}
    th:first-child, td:first-child, th:last-child, td:last-child {{ text-align: left; }}
  </style>
</head>
<body>
  <h1>APEX 五环短板雷达看板</h1>
  <div class="meta">
    <div>更新时间: {up}</div>
    <div>当前循环: {cur.get('cycle_count')} | 状态: {cur.get('summary', {}).get('status')} | ΔG: {cur.get('summary', {}).get('delta_g_estimate')}</div>
    <div>Shannon C: {cur_cap.get('capacity_c')} | η_capacity: {cur_cap.get('eta_capacity')} | plateau_score: {cur_cap.get('plateau_score')}</div>
  </div>
  <div class="cards">
    <div class="card"><b>Neuro-Cell Gate</b>Π_neuro: {neuro_gate.get('Π_neuro', 'n/a')}<br>Ω_cell: {neuro_gate.get('Ω_cell', 'n/a')}<br>ΔG_candidate: {neuro_gate.get('ΔG_candidate', 'n/a')}</div>
    <div class="card"><b>GitHub V10.3 Self Loop</b>G_self_loop: {github_v103.get('G_self_loop', 'n/a')}<br>ΔG_v10_3_candidate: {github_v103.get('ΔG_v10_3_candidate', 'n/a')}<br>gain: {github_v103.get('relative_gain_vs_current_pct', 'n/a')}%</div>
    <div class="card"><b>Repo Sync</b>origin/main: {github_v103.get('origin_main', 'n/a')}<br>module: {github_v103.get('module', 'n/a')}</div>
  </div>
  <div class="grid">
    <canvas id="radar"></canvas>
    <canvas id="trend"></canvas>
  </div>
  <table>
    <thead><tr><th>cycle</th><th>ΔG</th><th>C_shannon</th><th>η_capacity</th><th>plateau</th><th>findings</th><th>status</th></tr></thead>
    <tbody>
      {''.join(f'<tr><td>{c}</td><td>{dd:.4f}</td><td>{cc:.4f}</td><td>{ee:.4f}</td><td>{pp:.4f}</td><td>{f}</td><td>{s}</td></tr>' for c,dd,cc,ee,pp,f,s in zip(cy,dg,cap,eta,ps,fd,st))}
    </tbody>
  </table>
  <script>
    const labels = {labels_json};
    const latest = {latest_json};
    const avg20 = {avg_json};
    const cycles = {cy_json};
    const deltaG = {dg_json};
    const capacityC = {cap_json};
    const etaCapacity = {eta_json};
    const plateauScore = {ps_json};

    new Chart(document.getElementById('radar'), {{
      type: 'radar',
      data: {{ labels, datasets: [
        {{ label: '最新', data: latest, borderWidth: 2 }},
        {{ label: '20轮均值', data: avg20, borderWidth: 2 }}
      ] }},
      options: {{ scales: {{ r: {{ min: 0, max: 1 }} }} }}
    }});

    new Chart(document.getElementById('trend'), {{
      type: 'line',
      data: {{ labels: cycles, datasets: [
        {{ label: 'ΔG', data: deltaG, tension: 0.2, borderWidth: 2 }},
        {{ label: 'C_shannon', data: capacityC, tension: 0.2, borderWidth: 2 }},
        {{ label: 'η_capacity', data: etaCapacity, tension: 0.2, borderWidth: 2 }},
        {{ label: 'plateau_score', data: plateauScore, tension: 0.2, borderWidth: 2 }}
      ] }},
      options: {{ plugins: {{ legend: {{ display: true }} }} }}
    }});
  </script>
</body>
</html>
'''
(reports / 'apex_dashboard.html').write_text(html, encoding='utf-8')

print('dashboard updated')
