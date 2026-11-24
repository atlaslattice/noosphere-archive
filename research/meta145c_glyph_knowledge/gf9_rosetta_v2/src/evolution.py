"""GF9-R2 finite deterministic evolution of synthetic *transport policy*, not GPT.
Every trial physically serializes, perturbs, decodes, CRC-checks and independently
recomputes a mathematical GF9 reference. Failed candidates do not alter policy.
Trial records are hash chained and externally checkpointed. There is no host loop.
"""
from __future__ import annotations
from dataclasses import asdict,dataclass
import hashlib,json,random,time,math,os
from pathlib import Path
from .protocol import Policy,BASE,CODEC_R,CODEC_DEC,evaluate,channel_rate,CHAPTER_LABELS

SCHEMA='atlas.gf9-r2.cumulative-sim/v1'
GENESIS='0'*64

def canon(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
def sha(obj):return hashlib.sha256(canon(obj).encode('ascii')).hexdigest()

def mutate(p:Policy,global_trial:int)->Policy:
    rng=random.Random(0xA715 + global_trial*47 + (global_trial//144)*19)
    if rng.randrange(10)<6:
        choices=[v for v in CODEC_R if v!=p.repetition]
        return Policy(rng.choice(choices),p.decimals)
    choices=[v for v in CODEC_DEC if v!=p.decimals]
    return Policy(p.repetition,rng.choice(choices))

def noise_seeds(module:int,chapter:int,global_trial:int,count:int=3):
    if not 1<=count<=16:raise ValueError('SEED_COUNT_INVALID')
    v=int.from_bytes(hashlib.sha256(f'GF9R2-TRAIN:{module}:{chapter}:{global_trial}'.encode()).digest()[:8],'big')
    return tuple((v+j*1013)%2**63 for j in range(count))

def acceptance(previous:dict,proposed:dict,p:Policy,q:Policy)->tuple[bool,str]:
    if proposed['false_accepted']>0:return False,'HOLD_UNDETECTED_CORRUPTION'
    if proposed['postflight_holds']>0:return False,'HOLD_INACCURATE_PHYSICS_CLAIM'
    if proposed['passes']<=0:return False,'HOLD_ZERO_CORRECT_RECOVERY'
    if proposed['score']>previous['score']+1e-9:return True,'IMPROVED_LOCAL_EVALUATION'
    if proposed['score']==previous['score'] and (q.repetition< p.repetition or (q.repetition==p.repetition and q.decimals<p.decimals)):
        return True,'EQUAL_SCORE_SMALLER_ENCODING'
    return False,'NO_LOCAL_GAIN'

def new_state()->dict:
    return {'schema':SCHEMA,'next_index':0,'head':GENESIS,
      'policies':[asdict(BASE) for _ in range(144)],
      'counts':{'evaluated':0,'accepted':0,'rejected':0,'false_acceptances':0,'postflight_holds':0},
      'phase_summaries':[], 'source_access':'SOURCE_FREE_SYNTHETIC_TRIALS',
      'resident_visits':0,'actual_GPT_calls':0,'model_weights_modified':False,
      'scientific_semantic_matches_approved':0,'live_service_connected':False}

def check_state(state:dict):
    assert state['schema']==SCHEMA
    if not isinstance(state['next_index'],int) or state['next_index']<0:raise ValueError('COUNTER_INVALID')
    if len(state['policies'])!=144:raise ValueError('POLICY_COUNT_INVALID')
    for p in state['policies']:Policy(**p)
    if type(state['head'])!=str or len(state['head'])!=64:raise ValueError('HASH_INVALID')
    if state['next_index']!=state['counts']['evaluated'] or state['counts']['evaluated']!=state['counts']['accepted']+state['counts']['rejected']:
        raise ValueError('EVENT_COUNT_INVALID')
    if state['resident_visits'] or state['actual_GPT_calls'] or state['model_weights_modified'] or state['scientific_semantic_matches_approved']:
        raise ValueError('FAKE_AUTHORITY_CLAIM')

def event_hash(prev:str,event:dict)->str:
    return hashlib.sha256((prev+'\n'+canon(event)).encode()).hexdigest()

def run_phase(state:dict,steps:int,log_path:Path,phase_label:str)->dict:
    check_state(state)
    if not isinstance(steps,int) or steps<1 or steps>10000:raise ValueError('PHASE_LENGTH_BOUNDS')
    if not isinstance(phase_label,str) or not phase_label.startswith('PHASE_'):raise ValueError('PHASE_NAME_INVALID')
    log_path.parent.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter()
    start_index=state['next_index']; prevhead=state['head']; accepted_at_start=state['counts']['accepted']
    with log_path.open('w',encoding='utf-8') as stream:
      for i in range(start_index,start_index+steps):
        module=i%144;chapter=(i//144)%12
        old=Policy(**state['policies'][module]);new=mutate(old,i)
        rate=channel_rate(module,chapter);seeds=noise_seeds(module,chapter,i,3)
        a=evaluate(old,module,chapter,seeds,rate)
        b=evaluate(new,module,chapter,seeds,rate)
        yes,reason=acceptance(a,b,old,new)
        if yes:state['policies'][module]=asdict(new);state['counts']['accepted']+=1
        else:state['counts']['rejected']+=1
        state['counts']['false_acceptances']+=a['false_accepted']+b['false_accepted']
        state['counts']['postflight_holds']+=a['postflight_holds']+b['postflight_holds']
        event={'trial':i+1,'phase':phase_label,'module':f'H{module//12+1:02d}.S{module%12+1:02d}',
          'chapter':chapter+1,'old':asdict(old),'proposed':asdict(new),
          'old_result':a,'candidate_result':b,
          'accepted':yes,'disposition':reason,'new_policy':dict(state['policies'][module]),
          'trial_seed_sha256':sha(list(seeds)),
          'status':'SIMULATED_CODEC_EXPERIMENT_NOT_LIVE_COMMUNICATION'}
        line={'prior':state['head'],'event':event,'hash':event_hash(state['head'],event)}
        state['head']=line['hash'];state['counts']['evaluated']+=1;state['next_index']+=1
        stream.write(canon(line)+'\n')
    dt=time.perf_counter()-started
    summary={'phase':phase_label,'trials':steps,'from':start_index+1,'to':state['next_index'],
      'full_144_batches':steps//144,'partial_batch':steps%144,
      'accepted':state['counts']['accepted']-accepted_at_start,
      'rejected':steps-(state['counts']['accepted']-accepted_at_start),
      'entry_tip':prevhead,'exit_tip':state['head'],
      'elapsed_s_local_cpu_wall':round(dt,3),
      'status':'FINITE_SIMULATION_COMPLETED_NOT_FUTURE_AUTONOMY'}
    state['phase_summaries'].append(summary)
    check_state(state)
    return summary

def save_state(state,path:Path):
    check_state(state)
    path.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n',encoding='utf-8')

def load_state(path:Path)->dict:
    state=json.loads(path.read_text(encoding='utf-8'));check_state(state);return state

def verify_log(state:dict,phase_paths:list[Path]):
    head=GENESIS;n=0;prevpolicies=[asdict(BASE) for _ in range(144)];accepts=0;issues=[]
    for phase in phase_paths:
      for line in phase.read_text(encoding='utf-8').splitlines():
        v=json.loads(line); e=v['event']
        if v['prior']!=head or v['hash']!=event_hash(head,e):issues.append('CHAIN_TAMPER_AT_'+str(n+1));break
        if e['trial']!=n+1:issues.append('NONCONTIGUOUS_TRIAL');break
        mi=(e['trial']-1)%144
        if e['module']!=f'H{mi//12+1:02d}.S{mi%12+1:02d}' or e['old']!=prevpolicies[mi]:issues.append('POLICY_REPLAY_MISMATCH');break
        if e['accepted']:
            accepts+=1;prevpolicies[mi]=e['new_policy']
        elif e['new_policy']!=prevpolicies[mi]:issues.append('UNAUTHORIZED_POLICY_MUTATION');break
        n+=1;head=v['hash']
      if issues:break
    return {'status':'CHAIN_AND_POLICY_REPLAY_PASS' if not issues and head==state['head'] and n==state['next_index'] and prevpolicies==state['policies'] and accepts==state['counts']['accepted'] else 'FAIL',
      'records_verified':n,'accepted_replay':accepts,'head':head,'problems':issues,
      'externally_signed':False,'rollback_protection':'REQUIRES_TRUSTED_EXTERNAL_TIP_AND_COUNT'}

def independent_benchmark(state:dict,seeds_per_chapter:int=5)->dict:
    check_state(state)
    data=[];correct0=correct1=0;false0=false1=0;held0=held1=0;total=bytes0=bytes1=0
    for m in range(144):
      new=Policy(**state['policies'][m]);a_hit=b_hit=0
      for c in range(12):
        rate=channel_rate(m,c)
        seeds=tuple((int.from_bytes(hashlib.sha256(f'GF9-UNSEEN-BLIND:{m}:{c}:{k}'.encode()).digest()[:8],'big')%2**63) for k in range(seeds_per_chapter))
        a=evaluate(BASE,m,c,seeds,rate);b=evaluate(new,m,c,seeds,rate)
        correct0+=a['passes'];correct1+=b['passes'];false0+=a['false_accepted'];false1+=b['false_accepted'];held0+=a['postflight_holds'];held1+=b['postflight_holds'];total+=seeds_per_chapter
        bytes0+=a['wire_bytes']*seeds_per_chapter;bytes1+=b['wire_bytes']*seeds_per_chapter
        a_hit+=a['passes'];b_hit+=b['passes']
      data.append({'module':f'H{m//12+1:02d}.S{m%12+1:02d}',
         'initial_correct':a_hit,'final_correct':b_hit,'total':12*seeds_per_chapter,
         'improvement':b_hit-a_hit,'final_policy':asdict(new)})
    return {'schema':'atlas.gf9-r2.blind-evaluation/v1','total_channel_packets':total,
      'initial_correct':correct0,'final_correct':correct1,
      'initial_delivery_rate':round(correct0/total,7),'final_delivery_rate':round(correct1/total,7),
      'initial_false_accepted':false0,'final_false_accepted':false1,
      'initial_postflight_holds':held0,'final_postflight_holds':held1,
      'initial_wire_bytes':bytes0,'final_wire_bytes':bytes1,
      'wire_size_ratio':round(bytes1/bytes0,4),
      'modules_improved':sum(r['improvement']>0 for r in data),
      'modules_unchanged':sum(r['improvement']==0 for r in data),
      'modules_regressed':sum(r['improvement']<0 for r in data),
      'per_module':data,
      'is_actual_communication':False,'is_new_GPT_training':False,
      'benchmark_limitation':'DETERMINISTIC_SYNTHETIC_CHANNEL_ONLY_NO_SEMANTIC_OR_REAL_WORLD_CALIBRATION'}
