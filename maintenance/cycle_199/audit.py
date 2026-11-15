import contextlib, hashlib, importlib.util, io, json, pathlib, subprocess, tempfile
from unittest.mock import patch
from run_checks import ROOT,OUT,save
SKILL=pathlib.Path('/home/ubuntu/.hermes/skills/apex-spiral-v10'); ALIAS=SKILL.parent/'mlops/apex-spiral-v10'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('preflight',SKILL/'scripts/apex_housekeeping_preflight.py');h=load('harness',ROOT/'scripts/apex_harness_cycle.py')
r=json.loads((OUT/'backup/registry.json').read_text());last=max(r['cycles'],key=lambda k:int(k.split('_')[1])); prev=r['cycles'][last]['sync_check']; approved=prev.get('last_known_good_sha256',prev['root_skill_md_sha256'])
checks={}
with tempfile.TemporaryDirectory(dir=OUT) as temp:
 t=pathlib.Path(temp);rt=t/'root';a=t/'alias';rt.mkdir();a.mkdir()
 for n in ['SKILL.md','references','scripts']:(rt/n).write_text('fixture');(a/n).symlink_to(rt/n)
 checks['alias_pass']=m.alias_topology(rt,a)['structural_ok'] is True
 (a/'SKILL.md').unlink();(a/'SKILL.md').symlink_to(t/'missing')
 checks['alias_fail']=m.alias_topology(rt,a)['structural_ok'] is False
 p=t/'registry.json'
 for name,head,expected in [('head_pass','cycle_1','A'),('head_fail','cycle_0','B')]:
  p.write_text(json.dumps({'cycles':{'cycle_1':{}},'head':head,'head_cycle':'cycle_1','last_cycle':'cycle_1'}));checks[name]=m.registry_state(p)['variant']==expected
 def matches(path,baseline):return hashlib.sha256(path.read_bytes()).hexdigest()==baseline
 fixture=t/'content';fixture.write_bytes(b'approved');digest=hashlib.sha256(fixture.read_bytes()).hexdigest();checks['baseline_pass']=matches(fixture,digest);fixture.write_bytes(b'changed');checks['baseline_fail']=not matches(fixture,digest)
 # Verify both outcomes of the real harness aggregator, not just process exit.
 for name,payloads,code in [('harness_pass',[{'registry':{'ok':True}},{'decision':'allow'},{'V_H':True,'I_continue':False}],0),('harness_fail',[{'registry':{'ok':True}},{'decision':'deny'},{'V_H':True,'I_continue':False}],1)]:
  results=[{'returncode':0,'stdout':json.dumps(p),'stderr':''} for p in payloads]
  with patch.object(h,'run',side_effect=results),contextlib.redirect_stdout(io.StringIO()) as buf: rc=h.main()
  checks[name]=rc==code and json.loads(buf.getvalue())['verification_ok']==(code==0)
with patch.object(m.subprocess,'run',side_effect=FileNotFoundError('injected cargo missing')): bad=m.run_cargo(ROOT)
legacy_flags=any(v.get('returncode') not in (0,None) for v in bad.values())
manifest={}
for tree in ['references','scripts']:
 for p in sorted((SKILL/tree).rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts:manifest[str(p.relative_to(SKILL))]=hashlib.sha256(p.read_bytes()).hexdigest()
alias_manifest={}
for rel in manifest:alias_manifest[rel]=hashlib.sha256((ALIAS/rel).read_bytes()).hexdigest()
observed=hashlib.sha256((SKILL/'SKILL.md').read_bytes()).hexdigest()
oldmanifest=json.loads((ROOT/'maintenance/cycle_198/verifier_audit.json').read_text())['payload_manifest']
report={'fixture_checks':checks,'all_fixtures_pass':all(checks.values()),'topology':m.alias_topology(SKILL,ALIAS),'sync_check':{'root_skill_md_sha256':observed,'mlops_skill_md_sha256':hashlib.sha256((ALIAS/'SKILL.md').read_bytes()).hexdigest(),'last_known_good_sha256':approved,'baseline_matches':observed==approved,'baseline_review_status':'pending; observed SHA does not replace approved baseline','alias_mode':m.alias_topology(SKILL,ALIAS)['alias_mode'],'alias_farm_structural_check':'ALIAS_FARM_OK' if m.alias_topology(SKILL,ALIAS)['structural_ok'] else 'FAIL','references_count_root':m.count_reference_files(SKILL/'references')['detector_count'],'references_count_mlops':m.count_reference_files(ALIAS/'references')['detector_count'],'scripts_count':m.count_script_files(SKILL/'scripts')['detector_count']},'reference_counts':m.count_reference_files(SKILL/'references'),'script_counts':m.count_script_files(SKILL/'scripts'),'payload_manifest':manifest,'recursive_mirror_equal':manifest==alias_manifest,'mirror_independent':False,'observed_payload_changes_since_previous':[k for k in set(manifest)|set(oldmanifest) if manifest.get(k)!=oldmanifest.get(k)],'cargo_exception_reproduction':{'results':bad,'legacy_aggregation_flags_failure':legacy_flags,'correct_fail_closed_flags_failure':any(v.get('returncode')!=0 for v in bad.values())},'registry':m.registry_state(ROOT/'evolution/registry.json'),'formula':{'G_base':'0.50 policy default','Lambda':'unknown','Theta':'unknown','K':'unknown','xi':'unknown','Psi':'unknown','Phi':'unknown','H':'unknown','T':'unknown','epsilon':'unknown','measured_delta_g':'unknown'},'decision':'Watch only; unresolved skill preflight and baseline review retained. No new demonstrated runtime defect justifies code change.'}
save('verifier_audit',report)
print(json.dumps({k:v for k,v in report.items() if k not in ('payload_manifest','registry')},ensure_ascii=False,indent=2));assert all(checks.values())
