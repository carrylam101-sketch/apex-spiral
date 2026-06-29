# Cycle 142 - Alias and Script Sync Repair

## Conclusion
Status: completed_cron_alias_drift_repair

Cycle 142 detected alias drift at cron step 2. The drift included SKILL.md hash mismatch, reference content mismatch for cycle-141, and a root-only helper script `scripts/verify_apex_alias_sync.sh`. This run repaired root-to-mlops alias sync for SKILL.md, references/, and scripts/.

## Formula Substitution
Issue scoring formula:

```text
delta_G_issue = G_base * (Lambda * Theta * K * xi * Psi * Phi) / (H * T * epsilon)
```

Conservative factors:

```text
G_base=0.50
Lambda=0.90
Theta=0.80
K=0.92
xi=0.95
Psi=0.70
Phi=0.92
H=1.05
T=1.00
epsilon=1.05
```

Calculated issue delta_G: 0.183790.

No new Rust/Go/C measurable gate was introduced. Registry delta_g is carried forward from cycle_141: 1.404, gain_ratio=1.0.

## Problem Found
Pre-repair detector:

```text
root_skill_sha=25d059ac44e7a2a42bade4b251fa3c5baf3bdf665ead072ec37278bc9a68ba47
mlops_skill_sha=a5d55d74e2a1b96d604818474f42835ab4d5fa1e833c8e4f615493ff547bb2e8
reference diff: cycle-141-skill-alias-drift-repair.md differed
root-only script: scripts/verify_apex_alias_sync.sh
alias_drift=1
cron exact_marker=True
```

Root cause: cycle_141 final writes updated root SKILL.md/reference/script after an earlier sync, but did not re-run full alias sync for SKILL.md + references/ + scripts/ after those final writes.

## Optimization Executed

```bash
cp ~/.hermes/cron/jobs.json ~/.hermes/cron/jobs.json.bak.cycle142-alias-repair-20260620-120155
cp ~/.hermes/skills/apex-spiral-v10/SKILL.md ~/.hermes/skills/mlops/apex-spiral-v10/SKILL.md
rsync -a --delete ~/.hermes/skills/apex-spiral-v10/references/ ~/.hermes/skills/mlops/apex-spiral-v10/references/
rsync -a --delete ~/.hermes/skills/apex-spiral-v10/scripts/ ~/.hermes/skills/mlops/apex-spiral-v10/scripts/
```

## Verification Evidence

```text
skill hashes after sync:
25d059ac44e7a2a42bade4b251fa3c5baf3bdf665ead072ec37278bc9a68ba47  root/SKILL.md
25d059ac44e7a2a42bade4b251fa3c5baf3bdf665ead072ec37278bc9a68ba47  mlops/SKILL.md

script hashes after sync:
2b88937f111f3fe9f57fba882d3bca27caf6b0ea9ff0360c82a6129e98cb1490  root/scripts/verify_apex_alias_sync.sh
2b88937f111f3fe9f57fba882d3bca27caf6b0ea9ff0360c82a6129e98cb1490  mlops/scripts/verify_apex_alias_sync.sh

reference counts: 69 / 69
script counts: 2 / 2
references_sync_ok
scripts_sync_ok
```

System verification:

```text
registry_json_ok
safe genes_json_ok
cron jobs_json_ok
apex_version 0.3.0
EVM=0.7691 defect_rate=0.0000 G_evm=1.0600
APEX self-check: cycle_count=101, delta_G estimate=2.2713, health=HEALTHY; Shannon plateau persists
Gini selector: selected_gene_id=gene_594, gini_gain=0.0, ig_gain=0.0, source=gene_pool, n_candidates=21, n_outcome_history=44
apex_devour gate: delta_G_current=1.0581, G_neuro=1.1142, G_self=1.0908, G_evm=1.0600, G_devour=1.0000, delta_G_candidate=1.4040, gate_open=true
Harness/Ralph: risk_score=0.24 decision=allow; V_H=true I_continue=false
Registry scan: bad_cycles_missing_delta_or_gain=[]; orphaned_normalized=[]; registry_without_file=[]
Dashboard refreshed: reports/apex_dashboard.md and reports/apex_dashboard.html
```

## Lesson
The final alias gate must include scripts/ as well as SKILL.md and references/. It must run after all report/reference/script writes, not before them.
