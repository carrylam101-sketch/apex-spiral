import datetime, difflib, hashlib, json, pathlib, re, sqlite3, uuid
from run_checks import ROOT,OUT,run,save

def read(name):return json.loads((OUT/(name+'.json')).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rpath=ROOT/'evolution/registry.json'; original=(OUT/'backup/registry.json').read_bytes()
assert rpath.read_bytes()==original,'Registry changed concurrently; stop'
r=json.loads(original);latest=max(r['cycles'],key=lambda k:int(k.split('_')[1]));assert latest=='cycle_198'
assert all(r[k]==latest for k in ['head','head_cycle','last_cycle'])
a=read('verifier_audit'); assert a['all_fixtures_pass']
checks={n:read(n)['returncode']==0 for n in ['cargo_root','cargo_devour','cargo_evomaster','pytest','harness','indicator','evm','runtime_gate','preflight']}
assert all(checks.values()),checks
h=json.loads(read('harness')['stdout']); assert h['verification_ok'] is True
ind=json.loads(read('indicator')['stdout']); assert ind['V_H'] is True and ind['I_continue'] is False
counts={}
for n in ['cargo_root','cargo_devour','cargo_evomaster']:
 text=read(n)['stdout']; matches=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed',text);assert matches and all(int(f)==0 for _,f in matches);counts[n]=sum(int(p) for p,_ in matches)
pytest_count=int(re.search(r'(\d+) passed',read('pytest')['stdout']).group(1))
gate=read('runtime_gate')['stdout']; assert re.search(r'gate_open\s*= true',gate)
values={k:float(re.search(re.escape(k)+r'\s*=\s*([0-9.]+)',gate).group(1)) for k in ['ΔG_current','G_neuro','G_self','G_evm','G_devour','ΔG_candidate']}
gate_count=gate.count('✓');evm=json.loads(read('evm')['stdout'])
now=datetime.datetime.now().astimezone().isoformat();cycle='cycle_199';report_rel='evolution/reports/cycle_199_verification_watch.md'
report=f'''# cycle_199 — APEX V10.3 每周 verification/watch

## 结论
状态：部分达成。运行验证、Variant A 注册及本地归档完成；skill 独立基线待审批、技能 preflight 的 cargo 异常漏报仍未修复。不声称实测能力提升。
时间：{now}。

## 任务前真实性声明
可真实执行：声明工作目录 /home/ubuntu/apex-spiral 内的检查、备份、证据登记。只读访问 skill、EVM 和 scheduler 作为依赖；不改目录外 SOUL、共享 /tmp anchor 或 pinned skill。无 session_search/delegate_task 工具，未声称调用。用户未提交改动保留，stash 不 pop；不改 cron、生产站、provider、安全策略，不 push。幻觉风险通过原始 stdout/stderr/returncode 与注册后独立复读控制。

## 代入公式
ΔG = G_base × (Λ·Θ·K·ξ·Ψ·Φ)/(H·T·ε)。G_base=0.50 为政策默认，Λ、Θ、K、ξ、Ψ、Φ、H、T、ε 均 unknown；本轮实测 ΔG=unknown。
本轮实际运行 CLI 重算配置门控：ΔG_current={values['ΔG_current']}，G_neuro={values['G_neuro']}，G_self={values['G_self']}，G_evm={values['G_evm']}，G_devour={values['G_devour']}，ΔG_candidate={values['ΔG_candidate']}。gate_open=true，{gate_count} 项子门控通过。这是配置重算，不是新能力 benchmark；不把历史 housekeeping 因子表当测量。

## 找问题
1. 所有现有 head/head_cycle/last_cycle 初始一致为 cycle_198，最新 cycles 键也是 cycle_198，因此 Variant A，无旧 metadata gap。
2. 兼容入口 SKILL.md/references/scripts 均为指向 root 的 symlink farm，结构通过；自比较 SHA 和递归镜像相等不是独立内容证明。
3. 入口 live SHA 为 `{a['sync_check']['root_skill_md_sha256']}`，保留的 approved baseline 为 `{a['sync_check']['last_known_good_sha256']}`，仍不相符。没有把 cycle_198 的 observed SHA 自动转为批准基线。上轮与本轮 source payload 清单差异：{json.dumps(a['observed_payload_changes_since_previous'],ensure_ascii=False)}。内容变化不等于已获批准，未自动背书。
4. skill preflight 的 cargo 异常聚合缺陷仍可复现：模拟 FileNotFoundError 时返回 error 且无 returncode，旧规则 `not in (0,None)` 未标失败；正确规则 `returncode != 0` 会失败。本轮独立直接执行三 crate 测试，不依赖这一缺陷分支。只报告，未越界修改技能。
5. gene_pool_stats 仍为 genes={r['gene_pool_stats'].get('total_genes')}/cycles={r['gene_pool_stats'].get('total_cycles')}，实际 gene_pool={len(r['gene_pool'])}、注册后 cycles={len(r['cycles'])+1}；旧计数字段语义不确定，保留不改。SOUL 仍指向旧 tick，目录外文案未改。
6. 本轮未发现新的、有证据支持且可在授权范围内修复的运行缺陷，选择 watch；不为产生增益数字而改代码。

## 优化
- 备份 registry、experiments.jsonl、watch_archive.sqlite 到 maintenance/cycle_199/backup/，不在技能测量树中创建备份；本轮 SQLite 使用 backup API，不以裸文件复制假设 WAL 已落盘。
- 注册前比较 registry 快照以发现并发变化，但此比较不是 writer lock；多工件提交不具备跨文件原子性。
- 新增本轮证据 runner/audit/finalize 工件；alias/head/approved SHA/harness 四类门控各验证正反路径，共 {len(a['fixture_checks'])} 项夹具通过。
- 新增 cycle_199 并滚动所有 head/timestamp 别名，保留全部旧 cycle、其他顶层数据及 list 类型 drift_repair_cycles。不新增基因、不声称新能力门控。
- 追加 experiments 与 SQLite watch archive，本地 session_anchor 留存当前状态；已知 SHA 批准基线连续保留。

## 验证
|真实命令/检查|本轮结果|
|---|---|
|根目录 cargo test --offline|{counts['cargo_root']} passed / 0 failed|
|apex_devour/ cargo test --offline|{counts['cargo_devour']} passed / 0 failed|
|evomaster_claw_core/ cargo test --offline|{counts['cargo_evomaster']} passed / 0 failed|
|python3 -B -m pytest tests -q -p no:cacheprovider|{pytest_count} passed|
|python3 -B scripts/apex_harness_cycle.py|verification_ok=true；decision=allow；risk={h['harness_risk_score']}|
|python3 -B scripts/indicator.py --json|V_H=true；I_continue=false；无坏 JSON、orphan、registry_without_file|
|apex_devour/ cargo run --offline --quiet -- gate|{gate_count} 子门控通过|
|EVM venv EVMCore.calculate_evm()|{evm['evm']}；defect_total={evm['defect_total']}；非零项={evm['nonzero']}|
|python3 -B maintenance/cycle_199/audit.py|{len(a['fixture_checks'])} 正反向夹具通过；独立 SHA 基线不匹配|
|preflight --cron-id 5f24f9cc168e|exit=0 但带 warnings，不等于全部审计项健康|

Rust 合计 {sum(counts.values())}；pytest 已包含 harness 回归，不重复累加。Rust 编译 warning 保留在各 JSON stderr。EVM 零缺陷只是其模型输出，不表示整个系统无缺陷。
当前 scheduler 身份经 jobs.json 只读发现，并由 preflight 复核为 enabled、每周一 00:00 `0 0 * * 1`、marker 存在；未创建/修改任务。
参考文件顶层 {a['reference_counts']['detector_count']}，递归 {a['reference_counts']['recursive_count']}；脚本顶层 {a['script_counts']['detector_count']}（已有 pycache 不计顶层源文件）。source payload 哈希清单在 verifier_audit.json。

## 输出证据 / 变更文件
- 修改：evolution/registry.json、evolution/experiments.jsonl、evolution/watch_archive.sqlite。
- 新增：{report_rel}；maintenance/cycle_199/ 下 runner、audit、finalize、备份、JSON 原始输出、registry diff、本地 session_anchor 和 final_verification。
- 核心证据：maintenance/cycle_199/final_verification.json；maintenance/cycle_199/verifier_audit.json；cargo_*.json、pytest.json、runtime_gate.json、harness_final.json、indicator_final.json。
- 回滚材料：maintenance/cycle_199/backup/。恢复前须确认没有新的并发注册/归档；禁止 git reset、stash pop 或批量删除。

## 未完成 / 风险 / 真实性门控
已达成：本轮命令验证及 watch 登记归档；未达成：skill approved baseline 审批与目录外 preflight 修复；未验证：真实能力提升（unknown）。SOUL 和共享 session anchor 未同步，当前准确状态以本地证据为准。已有 fail-closed-watch-verification.md 已覆盖本轮遇到的风险，不新增重复 skill、不修改 pinned skill。
最终复读和归档哈希以 final_verification.json 为准；任何断言失败均不得把本轮视为完成。维护动作不等于实测能力提升。
'''
assert not (ROOT/report_rel).exists();(ROOT/report_rel).write_text(report)
entry={'cycle':cycle,'timestamp':now,'status':'completed_cron_verification_watch','overall_status':'partial_pending_skill_baseline_review','variant':'A','selected_gene':'verification_watch_no_gate','verification_mode':'watch','delta_g':values['ΔG_candidate'],'delta_g_evolved':values['ΔG_candidate'],'delta_g_self_repair':0.0,'delta_g_housekeeping':None,'measured_capability_gain':'unknown','formula_factors':a['formula'],'runtime_value_caveat':'Recomputed configured gate, not a fresh capability benchmark','live_gate_baseline':{'delta_g_current':values['ΔG_current'],'G_neuro':values['G_neuro'],'G_self':values['G_self'],'G_evm':values['G_evm'],'G_devour':values['G_devour'],'delta_g_candidate':values['ΔG_candidate'],'gate_open':True,'evm_value':evm['evm'],'defect_total':evm['defect_total']},'sync_check':a['sync_check'],'verification':{'cargo_counts':counts,'pytest_passed':pytest_count,'verifier_fixture_checks':len(a['fixture_checks']),'runtime_subgates_passed':gate_count,'harness_verification_ok':True},'unresolved':['Skill SHA pending approved-baseline review','External preflight cargo exception aggregation remains fail-open','gene_pool_stats ambiguous; SOUL stale and outside local write scope'],'artifacts':{'report_path':report_rel,'evidence_dir':'maintenance/cycle_199','backup_dir':'maintenance/cycle_199/backup','experiments':'evolution/experiments.jsonl','archive':'evolution/watch_archive.sqlite'}}
r['cycles'][cycle]=entry
for k in ['head','head_cycle','last_cycle']:r[k]=cycle
for k in ['last_updated','last_verified','updated_at']:r[k]=now
assert rpath.read_bytes()==original
rpath.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
save('session_anchor',{'active_task':{'what':'APEX weekly cycle_199','phase':'in_progress','done_steps':['runtime and verifier checks','Variant A registration'],'pending_steps':['post-write verification and archive'],'key_files':[report_rel]}})
b=json.loads(original);actual=json.loads(rpath.read_text());assert all(actual['cycles'][k]==v for k,v in b['cycles'].items());assert all(actual[k]==v for k,v in b.items() if k not in ['cycles','head','head_cycle','last_cycle','last_updated','last_verified','updated_at'])
for name,cmd in [('harness_final',['python3','-B','scripts/apex_harness_cycle.py']),('indicator_final',['python3','-B','scripts/indicator.py','--json']),('preflight_final',['python3','-B','/home/ubuntu/.hermes/skills/apex-spiral-v10/scripts/apex_housekeeping_preflight.py','--cron-id','5f24f9cc168e']),('stash_final',['git','stash','list'])]:assert run(name,cmd)['returncode']==0
assert json.loads(read('harness_final')['stdout'])['verification_ok'] is True
assert json.loads(read('harness_final')['stdout'])['raw']['omega']['registry']['head_cycle']==cycle
assert read('stash_before')['stdout']==read('stash_final')['stdout']
pre=json.loads(read('preflight_final')['stdout']); assert pre['checks']['registry']['variant']=='A'
assert pre['checks']['alias_topology']['structural_ok']
assert pre['checks']['reference_counts']['detector_count']==a['reference_counts']['detector_count']
assert sha(pathlib.Path('/home/ubuntu/.hermes/skills/apex-spiral-v10/SKILL.md'))==a['sync_check']['root_skill_md_sha256']
record={'cycle':cycle,'timestamp':now,'mode':'watch','status':'partial','report':report_rel,'report_sha256':sha(ROOT/report_rel),'measured_capability_gain':'unknown'}
exp=ROOT/'evolution/experiments.jsonl';assert exp.read_bytes()==(OUT/'backup/experiments.jsonl').read_bytes()
assert not any(json.loads(line).get('cycle')==cycle for line in exp.read_text().splitlines())
with exp.open('a') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')
db=sqlite3.connect(ROOT/'evolution/watch_archive.sqlite');db.execute('INSERT INTO watch_cycles VALUES (?,?,?)',(cycle,now,json.dumps(record,ensure_ascii=False)));db.commit();assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert json.loads(db.execute('SELECT payload_json FROM watch_cycles WHERE cycle=?',(cycle,)).fetchone()[0])==record
db.close();assert json.loads(exp.read_text().splitlines()[-1])==record
assert exp.read_bytes().startswith((OUT/'backup/experiments.jsonl').read_bytes())
import subprocess
current_files=set(subprocess.check_output(['git','ls-files','-c','-o','--exclude-standard','-z'],cwd=ROOT).decode().split('\0'))- {''}
new_files=current_files-set(read('existing_hashes'))
assert all(f.startswith('maintenance/cycle_199/') or f==report_rel for f in new_files),new_files
old=sqlite3.connect(OUT/'backup/watch_archive.sqlite');new=sqlite3.connect(ROOT/'evolution/watch_archive.sqlite');assert all(new.execute('SELECT * FROM watch_cycles WHERE cycle=?',(row[0],)).fetchone()==row for row in old.execute('SELECT * FROM watch_cycles'));old.close();new.close()
existing=read('existing_hashes');changed=[f for f,v in existing.items() if not (ROOT/f).is_file() or sha(ROOT/f)!=v];assert set(changed)=={'evolution/registry.json','evolution/experiments.jsonl','evolution/watch_archive.sqlite'},changed
actual=json.loads(rpath.read_text());latest=max(actual['cycles'],key=lambda k:int(k.split('_')[1]));assert latest==cycle;assert all(actual[k]==cycle for k in ['head','head_cycle','last_cycle']);assert all(actual[k]==now for k in ['last_updated','last_verified','updated_at'])
(OUT/'registry.json.diff').write_text(''.join(difflib.unified_diff(original.decode().splitlines(True),rpath.read_text().splitlines(True),fromfile='before/registry.json',tofile='after/registry.json')))
result={'timestamp':datetime.datetime.now().astimezone().isoformat(),'status':'partial','head_aliases':{k:actual[k] for k in ['head','head_cycle','last_cycle']},'cycle_count':len(actual['cycles']),'checks':checks,'cargo_counts':counts,'rust_total':sum(counts.values()),'pytest_passed':pytest_count,'fixture_checks':len(a['fixture_checks']),'old_registry_preserved':True,'old_sqlite_rows_preserved':True,'archive_roundtrip':True,'sqlite_integrity':'ok','stash_unchanged':True,'changed_preexisting_files':changed,'skill_baseline_matches':False,'report_sha256':record['report_sha256'],'measured_capability_gain':'unknown'}
save('final_verification',result);save('session_anchor',{'session_id':str(uuid.uuid4()),'last_updated':result['timestamp'],'active_task':{'what':'APEX weekly cycle_199','phase':'completed','status':'partial','done_steps':['runtime tests and verifier audit','Variant A registration; all head aliases consistent','archives roundtrip and prior-file preservation verified'],'pending_steps':['approved skill baseline review','external preflight cargo aggregation repair','external SOUL continuity update'],'key_files':[report_rel,'maintenance/cycle_199/final_verification.json']},'scope_note':'Local anchor only; shared /tmp and SOUL untouched'})
print(json.dumps(result,ensure_ascii=False,indent=2))
