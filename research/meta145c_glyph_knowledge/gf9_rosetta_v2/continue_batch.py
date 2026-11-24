#!/usr/bin/env python3
"""One finite 144-iteration continuation per explicitly authorized invocation.
No event loops, daemon, API calls or automatic host permissions.
The source code may be scheduled by a separately trusted system, never self.
"""
from pathlib import Path
import argparse,json,os,sys,hashlib
from src.evolution import load_state,run_phase,save_state,verify_log
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs'; BASELOG=[OUT/'phase1_5000.jsonl',OUT/'phase2_10000.jsonl']

def next_batch(state_path:Path, batch_id:int, outdir:Path=OUT):
    if not (1<=batch_id<=100000):raise ValueError('BATCH_ID_BOUNDS')
    outdir.mkdir(parents=True,exist_ok=True)
    log=outdir/f'CONTINUATION_BATCH_{batch_id:05d}_144.jsonl'
    cp=outdir/f'CHECKPOINT_CONT_{batch_id:05d}.json'
    if log.exists() or cp.exists():raise FileExistsError('NO_OVERWRITE_EXISTING_BATCH_OR_CHECKPOINT')
    state=load_state(state_path)
    if batch_id==1 and state['next_index']!=15000:raise ValueError('START_CHECKPOINT_NOT_15000')
    previous=BASELOG+[outdir/f'CONTINUATION_BATCH_{i:05d}_144.jsonl' for i in range(1,batch_id)]
    if any(not f.is_file() for f in previous):raise FileNotFoundError('PREDECESSOR_CHAIN_MISSING')
    if verify_log(state,previous)['status']!='CHAIN_AND_POLICY_REPLAY_PASS':raise ValueError('PREDECESSOR_CHAIN_BROKEN')
    result=run_phase(state,144,log,f'PHASE_NEXT_{batch_id:05d}')
    check=verify_log(state,previous+[log]);assert check['status']=='CHAIN_AND_POLICY_REPLAY_PASS'
    tmp=cp.with_suffix('.pending');save_state(state,tmp);os.replace(tmp,cp)
    return {'status':'FINITE_BATCH_COMPLETE','batch_id':batch_id,'new_checkpoint':str(cp),
       'log':str(log),'trial_to':state['next_index'],'accepted_this_batch':result['accepted'],
       'chain_verified':check['status'],'new_tip':state['head'],
       'message':'No hosted effects or source semantic promotions'}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--batch',type=int,required=True);parser.add_argument('--from-checkpoint');args=parser.parse_args()
 if args.from_checkpoint:st=Path(args.from_checkpoint)
 elif args.batch==1:st=OUT/'CHECKPOINT_15000.json'
 else:st=OUT/f'CHECKPOINT_CONT_{args.batch-1:05d}.json'
 print(json.dumps(next_batch(st,args.batch),indent=2))
