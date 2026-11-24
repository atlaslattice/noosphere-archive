"""Separate *review-only* promotion gate after 15k trials.
Uses a validation set never used during evolution; reports a third, independent
synthetic blind set after selection. Neither is real-world validation.
"""
from .protocol import Policy,BASE,evaluate,channel_rate,make_message,valid_message
import hashlib,json

def seed_set(namespace,mod,chapter,count):
    return tuple(int.from_bytes(hashlib.sha256(f'{namespace}:{mod}:{chapter}:{j}'.encode()).digest()[:8],'big')%2**63 for j in range(count))

def numerical_safety(p:Policy,mod:int)->bool:
    return all(valid_message(make_message(mod,c,p),mod,c) for c in range(12))

def candidate_eval(p:Policy,mod:int,namespace:str,n:int=4)->dict:
    total=correct=held=bytes_total=0
    for c in range(12):
        r=evaluate(p,mod,c,seed_set(namespace,mod,c,n),channel_rate(mod,c))
        correct+=r['passes'];held+=r['postflight_holds'];total+=n;bytes_total+=r['wire_bytes']*n
    return {'correct':correct,'held':held,'total':total,'bytes':bytes_total,
      'delivery_rate':correct/total,
      'utility':round(correct/total-0.035*(p.repetition-1)-0.001*max(0,p.decimals-4),9)}

def choose_promotions(raw_policies:list[dict])->list[dict]:
    if len(raw_policies)!=144:raise ValueError('REQUIRE_144_POLICIES')
    out=[]
    for mi,current in enumerate(raw_policies):
        raw=Policy(**current)
        # Recover from compromised numeric precision. All viable candidates
        # MUST pass every one of this Sphere's twelve chapter checks.
        candidate_set={Policy(1,6),Policy(3,4),Policy(3,6),Policy(3,8),Policy(5,4),Policy(5,6),Policy(5,8),raw}
        trials=[]
        for p in sorted(candidate_set,key=lambda p:(p.repetition,p.decimals)):
            safe=numerical_safety(p,mi)
            e=candidate_eval(p,mi,'GF9-R2-VALIDATION',4) if safe else None
            trials.append({'policy':{'repetition':p.repetition,'decimals':p.decimals},'safe':safe,'validation':e})
        eligible=[x for x in trials if x['safe'] and x['validation']['held']==0]
        best=max(eligible,key=lambda x:(x['validation']['utility'],-x['validation']['bytes']))
        out.append({'module':f'H{mi//12+1:02d}.S{mi%12+1:02d}',
           'prior_candidate':current,'selected':best['policy'],
           'basis':'MULTICHAPTER_NUMERICAL_SAFETY_PLUS_VALIDATION_NO_SEMANTIC_GRANTS',
           'validation':best['validation'],
           'competing_policies':trials,
           'status':'LOCAL_REVIEW_PROPOSAL_NOT_HOSTED_OR_AUTONOMOUS'})
    return out

def blind_compare(raw_policies,selected,namespace='GF9-R2-INDEPENDENT-BLIND'):
    categories={'initial_minimal':[],'fixed_robust':[],'evolved_15000':[],'guarded_selection':[]}
    for i in range(144):
        entries={'initial_minimal':BASE,'fixed_robust':Policy(3,6),
            'evolved_15000':Policy(**raw_policies[i]),'guarded_selection':Policy(**selected[i]['selected'])}
        for k,p in entries.items():categories[k].append(candidate_eval(p,i,namespace,6))
    summary={}
    for name,rows in categories.items():
        total=sum(x['total'] for x in rows);ok=sum(x['correct'] for x in rows);bad=sum(x['held'] for x in rows)
        summary[name]={'passed':ok,'total':total,'rate':round(ok/total,8),
          'held_by_postflight':bad,'wire_bytes':sum(x['bytes'] for x in rows),
          'module_count':len(rows)}
    return {'schema':'atlas.gf9-r2.blind-benchmark/v2','evaluations':sum(v['total'] for v in summary.values()),
     'holdout_seed_namespace':namespace,'source':'OFFLINE_SIMULATED_CHANNEL',
     'results':summary,'using_holdout_to_choose_policy':False,
     'actual_gpt_weight_training':False,'semantic_translation_validated':False}
