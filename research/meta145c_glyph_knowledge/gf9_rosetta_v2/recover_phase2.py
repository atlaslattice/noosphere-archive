"""Fail-closed crash recovery from a partially committed event journal.
Accept only a contiguous chain rooted at the trusted 5k checkpoint.
Preserve the original 9790 records, append only remaining indices, then audit all 15000.
"""
from pathlib import Path
import json,os,hashlib
from src.evolution import load_state,save_state,run_phase,verify_log,event_hash,independent_benchmark,check_state,GENESIS
from run import OUT,R1,R2,filehash

def replay_partial(path):
  state=load_state(OUT/'CHECKPOINT_5000.json')
  original=state['counts'].copy();original_head=state['head'];valid=0
  for lineno,line in enumerate(path.read_text(encoding='utf-8').splitlines(),start=1):
    row=json.loads(line);e=row['event']
    i=state['next_index'];mi=i%144
    if e['trial']!=i+1 or e['phase']!='PHASE_2_EXPANSION' or e['module']!=f'H{mi//12+1:02d}.S{mi%12+1:02d}':raise ValueError('PARTIAL_LOG_INDEX_OR_PHASE_TAMPERED')
    if row['prior']!=state['head'] or row['hash']!=event_hash(state['head'],e):raise ValueError('PARTIAL_HASH_CHAIN_INVALID')
    if e['old']!=state['policies'][mi] or e['new_policy']!=(e['proposed'] if e['accepted'] else e['old']):raise ValueError('PARTIAL_POLICY_INVALID')
    if e['accepted']:
      state['policies'][mi]=e['new_policy'];state['counts']['accepted']+=1
    else:state['counts']['rejected']+=1
    state['counts']['false_acceptances']+=e['old_result']['false_accepted']+e['candidate_result']['false_accepted']
    state['counts']['postflight_holds']+=e['old_result']['postflight_holds']+e['candidate_result']['postflight_holds']
    state['head']=row['hash'];state['next_index']+=1;state['counts']['evaluated']+=1;valid+=1
  check_state(state)
  a=verify_log(state,[R1,R2]);assert a['status']=='CHAIN_AND_POLICY_REPLAY_PASS',a
  return state,original,original_head,valid

def main():
  state,orig,head,done=replay_partial(R2)
  if done>10000:raise ValueError('TOO_MANY_PHASE2_TRIALS')
  print('RECOVERED',done,'verified',state['next_index'],state['head'],flush=True)
  remaining=10000-done
  if remaining:
    tail=OUT/'phase2_tail_recovery.jsonl'
    mini=run_phase(state,remaining,tail,'PHASE_2_EXPANSION')
    print('TAIL',mini,flush=True)
    content=R2.read_bytes()+tail.read_bytes()
    draft=OUT/'phase2_10000.joined.tmp'
    draft.write_bytes(content);os.replace(draft,R2)
  else:pass
  # Replace partial tail summary by complete phase record. Timeout time is unknown.
  phase1=state['phase_summaries'][0]
  phase2={'phase':'PHASE_2_EXPANSION','trials':10000,'from':5001,'to':15000,
    'full_144_batches':69,'partial_batch':64,'accepted':state['counts']['accepted']-orig['accepted'],
    'rejected':state['counts']['rejected']-orig['rejected'],
    'entry_tip':head,'exit_tip':state['head'],'elapsed_s_local_cpu_wall':'PARTIAL_ATTEMPT_TIMED_OUT_NOT_ESTIMATED',
    'status':'FINITE_SIMULATION_RECOVERED_AND_COMPLETED'}
  state['phase_summaries']=[phase1,phase2]
  save_state(state,OUT/'CHECKPOINT_15000.json')
  aud=verify_log(state,[R1,R2]);assert aud['status']=='CHAIN_AND_POLICY_REPLAY_PASS',aud
  blind=independent_benchmark(state,5)
  (OUT/'BENCHMARK_15000.json').write_text(json.dumps(blind,indent=2)+'\n',encoding='utf-8')
  receipt={'phase1':phase1,'phase2':phase2,'counts':state['counts'],'audit':aud,
    'holdout_summary':{k:v for k,v in blind.items() if k!='per_module'},
    'source_registry_sha256':'07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6',
    'immutable_log_digests':{R1.name:filehash(R1),R2.name:filehash(R2)},
    'checkpoint_digest':filehash(OUT/'CHECKPOINT_15000.json'),
    'actual_model_wakes':0,'hosted_runs':0,'learned_model_weights':False,'real_language_translation_proven':False,
    'semantic_evidence_accepted':0,'simulation_status':'ACTUAL_FINITE_LOCAL_COMPUTE'}
  (OUT/'FINAL_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
  print(json.dumps({'status':'FULLY_REPLAYED','counts':state['counts'],'tip':state['head'],'holdout_summary':receipt['holdout_summary'],'audit':aud['status']}),flush=True)
if __name__=='__main__':main()
