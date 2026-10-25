import datetime, difflib, hashlib, json, pathlib, sqlite3, sys, uuid
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from run_checks import run,ROOT,OUT
r=json.loads((ROOT/'evolution/registry.json').read_text())
b=json.loads((OUT/'backup/registry.json').read_text())
latest=max(r['cycles'],key=lambda k:int(k.split('_')[1]))
assert latest=='cycle_196'
assert all(r[k]==latest for k in ['head','head_cycle','last_cycle'])
assert all(r[k]==r['cycles'][latest]['timestamp'] for k in ['last_updated','last_verified','updated_at'])
assert all(r['cycles'][k]==v for k,v in b['cycles'].items())
assert all(r[k]==v for k,v in b.items() if k not in ['cycles','head','head_cycle','last_cycle','last_updated','last_verified','updated_at'])
record={'cycle':latest,'timestamp':r['cycles'][latest]['timestamp'],'mode':'watch_with_bounded_verifier_repair','status':'partial','report':'evolution/reports/cycle_196_verification_watch.md','report_sha256':hashlib.sha256((ROOT/'evolution/reports/cycle_196_verification_watch.md').read_bytes()).hexdigest(),'measured_capability_gain':'unknown'}
exp=ROOT/'evolution/experiments.jsonl'
prior=[json.loads(x) for x in exp.read_text().splitlines()] if exp.exists() else []
assert not any(x.get('cycle')==latest for x in prior)
with exp.open('a') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')
db=sqlite3.connect(ROOT/'evolution/watch_archive.sqlite')
db.execute('CREATE TABLE IF NOT EXISTS watch_cycles (cycle TEXT PRIMARY KEY, timestamp TEXT NOT NULL, payload_json TEXT NOT NULL)')
db.execute('INSERT INTO watch_cycles VALUES (?,?,?)',(latest,record['timestamp'],json.dumps(record,ensure_ascii=False)))
db.commit()
assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
assert json.loads(db.execute('SELECT payload_json FROM watch_cycles WHERE cycle=?',(latest,)).fetchone()[0])==record
db.close()
for rel in ['scripts/apex_harness_cycle.py','evolution/registry.json']:
    before=(OUT/'backup'/pathlib.Path(rel).name).read_text().splitlines(True)
    after=(ROOT/rel).read_text().splitlines(True)
    (OUT/(pathlib.Path(rel).name+'.diff')).write_text(''.join(difflib.unified_diff(before,after,fromfile='before/'+rel,tofile='after/'+rel)))
run('harness_final',['python3','scripts/apex_harness_cycle.py'])
run('indicator_final',['python3','scripts/indicator.py','--json'])
run('preflight_final',['python3','/home/ubuntu/.hermes/skills/apex-spiral-v10/scripts/apex_housekeeping_preflight.py','--cron-id','5f24f9cc168e'])
run('stash_final',['git','stash','list'])
existing=json.loads((OUT/'existing_hashes.json').read_text())
changed=[f for f,h in existing.items() if not (ROOT/f).exists() or hashlib.sha256((ROOT/f).read_bytes()).hexdigest()!=h]
assert set(changed)=={'evolution/registry.json','scripts/apex_harness_cycle.py'}, changed
checks={}
for name in ['cargo_root','cargo_devour','cargo_evomaster','pytest_regression','harness_final','indicator_final','runtime_gate','evm']:
    d=json.loads((OUT/(name+'.json')).read_text()); checks[name]=d['returncode']==0
assert all(checks.values())
h=json.loads(json.loads((OUT/'harness_final.json').read_text())['stdout']); assert h['verification_ok'] is True
assert h['raw']['omega']['registry']['head_cycle']==latest
assert json.loads((OUT/'stash_before.json').read_text())['stdout']==json.loads((OUT/'stash_final.json').read_text())['stdout']
result={'timestamp':datetime.datetime.now().astimezone().isoformat(),'status':'partial','head_aliases':{k:r[k] for k in ['head','head_cycle','last_cycle']},'cycle_count':len(r['cycles']),'checks':checks,'old_registry_content_preserved':True,'changed_preexisting_files':changed,'archive_roundtrip':True,'sqlite_integrity':'ok','stash_unchanged':True,'skill_baseline_matches':False,'report_sha256':record['report_sha256']}
(OUT/'final_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
(OUT/'session_anchor.json').write_text(json.dumps({'session_id':str(uuid.uuid4()),'last_updated':result['timestamp'],'active_task':{'what':'APEX weekly cycle_196','phase':'completed','status':'partial','done_steps':['bounded harness fix','158 Rust tests and 198 pytest tests','Variant A registration and archives verified'],'pending_steps':['review skill SHA drift','repair skill preflight with authorization','external SOUL continuity update'],'key_files':[str(ROOT/record['report']),str(OUT/'final_verification.json')]},'scope_note':'Local anchor only; shared /tmp and SOUL untouched'},ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
