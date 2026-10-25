import concurrent.futures, datetime, hashlib, json, os, pathlib, shutil, subprocess
ROOT=pathlib.Path('/home/ubuntu/apex-spiral')
OUT=ROOT/'maintenance/cycle_196'
OUT.mkdir(parents=True,exist_ok=True)
def run(name,cmd,cwd=ROOT):
    try:
        p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=300)
        result={'command':cmd,'cwd':str(cwd),'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    except Exception as e: result={'command':cmd,'returncode':None,'error':str(e)}
    (OUT/(name+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(name,result['returncode'],flush=True)
    return result
if __name__=='__main__':
    backup=OUT/'backup'; backup.mkdir(exist_ok=True)
    for rel in ['evolution/registry.json','scripts/apex_harness_cycle.py']:
        dst=backup/pathlib.Path(rel).name
        if not dst.exists(): shutil.copy2(ROOT/rel,dst)
    run('git_status_before',['git','status','--porcelain=v1','-z'])
    run('stash_before',['git','stash','list'])
    files=subprocess.check_output(['git','ls-files','-m','-o','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files if f and (ROOT/f).is_file() and not f.startswith('maintenance/cycle_196/')}
    (OUT/'existing_hashes.json').write_text(json.dumps(hashes,indent=2))
    tasks=[('preflight',['python3','/home/ubuntu/.hermes/skills/apex-spiral-v10/scripts/apex_housekeeping_preflight.py','--cron-id','5f24f9cc168e'],ROOT),('cargo_root',['cargo','test','--offline'],ROOT),('cargo_devour',['cargo','test','--offline'],ROOT/'apex_devour'),('cargo_evomaster',['cargo','test','--offline'],ROOT/'evomaster_claw_core'),('harness_before',['python3','scripts/apex_harness_cycle.py'],ROOT),('evm',['/home/ubuntu/.hermes/venv-evm/bin/python','-c',"import sys,json; sys.path.insert(0,'/home/ubuntu/EVM-Entropy-Vibe-Mathing'); from CoreFormula.EVM_FORMULA import EVMCore; e=EVMCore(); print(json.dumps({'evm':e.calculate_evm(),'defects':e.defects,'defect_total':sum(e.defects.values()),'nonzero':sum(v>0 for v in e.defects.values())}))"],ROOT),('runtime_gate',['cargo','run','--offline','--quiet','--','gate'],ROOT/'apex_devour')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(lambda t:run(*t),tasks))
