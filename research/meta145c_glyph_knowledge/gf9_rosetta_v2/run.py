#!/usr/bin/env python3
"""Finite 5,000 + 10,000 synthetic GF9 trials. Stage 2 reloads stage 1."""
from pathlib import Path
import json,sys,hashlib,time
from src.evolution import new_state,run_phase,save_state,load_state,verify_log,independent_benchmark
from src.ontology import bind_registry
from src.linguistics import PROFILES,registry_digest,original_style_grammar
ROOT=Path(__file__).parent
OUT=ROOT/'outputs';OUT.mkdir(parents=True,exist_ok=True)
R1=OUT/'phase1_5000.jsonl';R2=OUT/'phase2_10000.jsonl'

def filehash(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def run_one():
    modules=bind_registry(ROOT/'private_inputs'/'ariadne_v07_atlas.json')
    (OUT/'MODULES_144_X_CHAPTERS_12_PRIVATE.json').write_text(json.dumps(modules,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    st=new_state();summary=run_phase(st,5000,R1,'PHASE_1_GROUNDING')
    save_state(st,OUT/'CHECKPOINT_5000.json')
    audit=verify_log(st,[R1]); assert audit['status']=='CHAIN_AND_POLICY_REPLAY_PASS'
    benchmark=independent_benchmark(st,5)
    (OUT/'BENCHMARK_5000.json').write_text(json.dumps(benchmark,indent=2)+'\n',encoding='utf-8')
    (OUT/'RECEIPT_5000.json').write_text(json.dumps({'summary':summary,'audit':audit,'benchmark':{k:v for k,v in benchmark.items() if k!='per_module'},'source_digest':modules[0]['source_sha256'],'log_sha256':filehash(R1),'module_bytes_sha256':filehash(OUT/'MODULES_144_X_CHAPTERS_12_PRIVATE.json')},indent=2)+'\n')
    print(json.dumps({'status':'PHASE1_COMPLETE','summary':summary,'blind_initial':benchmark['initial_delivery_rate'],'blind_final':benchmark['final_delivery_rate'],'head':st['head']}))

def run_two():
    st=load_state(OUT/'CHECKPOINT_5000.json')
    audit=verify_log(st,[R1]);assert audit['status']=='CHAIN_AND_POLICY_REPLAY_PASS'
    summary=run_phase(st,10000,R2,'PHASE_2_EXPANSION')
    save_state(st,OUT/'CHECKPOINT_15000.json')
    audit=verify_log(st,[R1,R2]); assert audit['status']=='CHAIN_AND_POLICY_REPLAY_PASS'
    benchmark=independent_benchmark(st,5)
    (OUT/'BENCHMARK_15000.json').write_text(json.dumps(benchmark,indent=2)+'\n',encoding='utf-8')
    report={'schema':'atlas.gf9.cumulative.evidence/v1','phase1':json.loads((OUT/'RECEIPT_5000.json').read_text())['summary'],
     'phase2':summary,'counts':st['counts'],'audit':audit,
     'independent_holdout':{k:v for k,v in benchmark.items() if k!='per_module'},
     'gpt_calls':0,'hosted_site_updates':0,'model_weights_changed':False,
     'human_historical_script_translations_claimed':0,'script_profiles_researched':len(PROFILES),
     'module_names_source':'OWNER_PRIVATE_ARIADNE_V07_EXACT',
     'fiction':'ORIGINAL_HYPOTHETICAL_FIRST_CONTACT',
     'source_registry_sha256':json.loads((OUT/'RECEIPT_5000.json').read_text())['source_digest'],
     'language_profiles_sha256':registry_digest(),
     'log_sha256':{R1.name:filehash(R1),R2.name:filehash(R2)},
     'checkpoint_sha256':filehash(OUT/'CHECKPOINT_15000.json')}
    (OUT/'FINAL_RECEIPT.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PHASE2_COMPLETE','summary':summary,'audit':audit['status'],'counts':st['counts'],'holdout_summary':report['independent_holdout'],'head':st['head']}))
if __name__=='__main__':
    if len(sys.argv)!=2 or sys.argv[1] not in ('phase1','phase2'):raise SystemExit('Usage: python run.py phase1|phase2')
    (run_one if sys.argv[1]=='phase1' else run_two)()
