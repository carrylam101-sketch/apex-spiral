import concurrent.futures, datetime, hashlib, json, os, pathlib, shutil, subprocess
ROOT=pathlib.Path('/home/ubuntu/apex-spiral'); OUT=ROOT/'maintenance/cycle_197'
def save(name,data):
    (OUT/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2))
def run(name,cmd,cwd=ROOT):
    try:
        p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=480,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        result={'command':cmd,'cwd':str(cwd),'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    except Exception as e: result={'command':cmd,'returncode':None,'error':repr(e)}
    save(name,result); print(name,result['returncode'],flush=True); return result
if __name__=='__main__':
    backup=OUT/'backup'; backup.mkdir(exist_ok=True)
    for rel in ['evolution/registry.json','evolution/experiments.jsonl','evolution/watch_archive.sqlite']:
        dst=backup/pathlib.Path(rel).name
        assert not dst.exists()
        shutil.copy2(ROOT/rel,dst)
    run('git_status_before',['git','status','--porcelain=v1','-z']);run('stash_before',['git','stash','list'])
    files=subprocess.check_output(['git','ls-files','-c','-o','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    save('existing_hashes',{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in set(files) if f and (ROOT/f).is_file() and not f.startswith('maintenance/cycle_197/')})
    save('session_anchor',{'active_task':{'what':'APEX weekly cycle_197','phase':'in_progress','done_steps':['Variant A confirmed','backup and existing-file hashes captured'],'pending_steps':['runtime verification','verifier audit','registration and archive'],'key_files':['maintenance/cycle_197']},'scope':'local only; external SOUL and shared anchor not modified'})
    tasks=[('preflight',['python3','-B','/home/ubuntu/.hermes/skills/apex-spiral-v10/scripts/apex_housekeeping_preflight.py','--cron-id','5f24f9cc168e'],ROOT),('cargo_root',['cargo','test','--offline'],ROOT),('cargo_devour',['cargo','test','--offline'],ROOT/'apex_devour'),('cargo_evomaster',['cargo','test','--offline'],ROOT/'evomaster_claw_core'),('harness',['python3','-B','scripts/apex_harness_cycle.py'],ROOT),('indicator',['python3','-B','scripts/indicator.py','--json'],ROOT),('pytest',['python3','-B','-m','pytest','tests','-q','-p','no:cacheprovider'],ROOT),('evm',['/home/ubuntu/.hermes/venv-evm/bin/python','-B','-c',"import sys,json; sys.path.insert(0,'/home/ubuntu/EVM-Entropy-Vibe-Mathing'); from CoreFormula.EVM_FORMULA import EVMCore; e=EVMCore(); print(json.dumps({'evm':e.calculate_evm(),'defects':e.defects,'defect_total':sum(e.defects.values()),'nonzero':sum(v>0 for v in e.defects.values())}))"],ROOT),('runtime_gate',['cargo','run','--offline','--quiet','--','gate'],ROOT/'apex_devour')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: list(ex.map(lambda t:run(*t),tasks))
