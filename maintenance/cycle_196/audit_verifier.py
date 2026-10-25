"""Read-only skill verifier audit with fixtures isolated inside this run directory."""
import hashlib, importlib.util, json, pathlib, tempfile
from fractions import Fraction
ROOT=pathlib.Path('/home/ubuntu/apex-spiral')
OUT=ROOT/'maintenance/cycle_196'
SKILL=pathlib.Path('/home/ubuntu/.hermes/skills/apex-spiral-v10')
spec=importlib.util.spec_from_file_location('preflight',SKILL/'scripts/apex_housekeeping_preflight.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
registry=json.loads((OUT/'backup/registry.json').read_text())
previous=registry['cycles']['cycle_195']['sync_check']['root_skill_md_sha256']
live=hashlib.sha256((SKILL/'SKILL.md').read_bytes()).hexdigest()
checks={}
with tempfile.TemporaryDirectory(dir=OUT) as temp:
    t=pathlib.Path(temp); r=t/'root'; a=t/'alias'; r.mkdir(); a.mkdir()
    for name in ['SKILL.md','references','scripts']:
        (r/name).write_text('fixture')
        (a/name).symlink_to(r/name)
    checks['alias_positive']=m.alias_topology(r,a)['structural_ok'] is True
    (a/'SKILL.md').unlink(); (a/'SKILL.md').symlink_to(t/'missing')
    checks['alias_negative']=m.alias_topology(r,a)['structural_ok'] is False
    reg=t/'registry.json'; reg.write_text(json.dumps({'cycles':{'cycle_1':{}},'head':'cycle_1','head_cycle':'cycle_1','last_cycle':'cycle_1'}))
    checks['head_positive']=m.registry_state(reg)['variant']=='A'
    reg.write_text(json.dumps({'cycles':{'cycle_1':{}},'head':'cycle_0','head_cycle':'cycle_1','last_cycle':'cycle_1'}))
    checks['head_negative']=m.registry_state(reg)['variant']=='B'
    checks['sha_positive']=hashlib.sha256(b'fixture').hexdigest()==hashlib.sha256(b'fixture').hexdigest()
    checks['sha_negative']=hashlib.sha256(b'changed').hexdigest()!=hashlib.sha256(b'fixture').hexdigest()
manifest={}
for tree in ['references','scripts']:
    for p in sorted((SKILL/tree).rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            manifest[str(p.relative_to(SKILL))]=hashlib.sha256(p.read_bytes()).hexdigest()
product=Fraction('0.85')*Fraction('0.76')*Fraction('0.94')*Fraction('0.97')*Fraction('1.00')*Fraction('1.04')
report={'checks':checks,'all_fixture_checks_pass':all(checks.values()),'skill_previous_sha256':previous,'skill_live_sha256':live,'baseline_matches':previous==live,'baseline_disposition':'unexplained upstream change; observed SHA recorded separately, not auto-approved as known-good','skill_payload_manifest':manifest,'historical_cycle195_arithmetic':{'product_without_G_base':float(product),'product_with_G_base':float(product/2),'delta_g':float(product/2/(Fraction('1.02')*Fraction('1.03'))),'finding':'historical display multiplies G_base twice in intermediate line; final value corresponds to multiplying once. Historical report not rewritten.'},'unfixed_preflight_defects':['run_cargo catches exceptions into error with missing returncode; aggregation accepts None as success','preflight recommends independent SHA comparison but does not implement it','legacy default cron id is obsolete; current invocation explicitly supplies actual id'],'scope':'No skill files modified. Fixture unlink applies only to newly created local test symlink.'}
(OUT/'verifier_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='skill_payload_manifest'},ensure_ascii=False,indent=2))
assert all(checks.values())
