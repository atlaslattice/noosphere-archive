#!/usr/bin/env python3
"""Ariadne 1728×1728 fictional horizon and 20-stage source/rights-safe synthesis lab.

Fully offline. Uses the original owner-local Ariadne bytes as a read-only input;
all scientific/semantic edges and story amendments remain unreviewed. No Work
posts, subscriptions, actual model runs, real-time rights, or host attestations.
"""
from __future__ import annotations
import argparse, collections, csv, gzip, hashlib, json, math, re, statistics, time
from pathlib import Path
import numpy as np

SCHEMA='atlas.telescope.synthetic.v1'
REGISTRY_SHA='07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6'
YEARS=1728; ROUNDS=1728; N=1728
HOUSE_NAMES=None
STOP=set('a an and the of for into from to with or as in on under across within whose whose that whose this whose is are be by may use question questions methods observations operational artifacts primary focus primary domain specialty whose'.split())
RE_TOKENS=re.compile(r"[a-z][a-z0-9-]{2,}")
STAGES=(
('01','Original source byte pin','original-bytes'),('02','Unique House/Sphere/Node ancestry','coordinates'),
('03','Domain–method separation','role'),('04','Edition-specific lineage','edition'),
('05','Cross-domain candidate review','typed-edge'),('06','Music-instrument false friend','false-friend'),
('07','No private-mode ingestion','mode'),('08','Current READ admission','read'),
('09','Current RETURN eligibility','return'),('10','Source URL and witness deduplication','dedup'),
('11','Evidence gaps and disagreement','unknown'),('12','Method subject requirement','subject'),
('13','Fairness and physical floor','floors'),('14','Same-budget solo comparator','solo'),
('15','Isolated-attempt comparator','isolated'),('16','Cross-House comparator','collaborating'),
('17','Pareto dominance and regret','pareto'),('18','Mutation/ablations with counterexamples','mutations'),
('19','Metadata-only trace / provenance','trace'),('20','Nonpromotion release and rollback','release'),
)
GUARDS=frozenset(x[2] for x in STAGES)
SYSTEMS=('SwarmChat','Atlas','Ariadne','Iron Empire')


def digest(data):
    if isinstance(data,bytes): return hashlib.sha256(data).hexdigest()
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def read_registry(path:Path):
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=REGISTRY_SHA: raise ValueError('SOURCE_DIGEST_MISMATCH')
    d=json.loads(raw)
    if set(d)<{'houses','spheres','nodes'} or any(len(d[k])!=v for k,v in [('houses',12),('spheres',144),('nodes',1728)]): raise ValueError('GEOMETRY_INVALID')
    records=[]
    for h in range(1,13):
        hi=f'H{h:02}'; house=d['houses'][hi]
        if house['id']!=hi or len(house['children'])!=12:raise ValueError('HOUSE_INVALID')
        for s in range(1,13):
            si=f'{hi}.S{s:02}'; sp=d['spheres'][si]
            if sp['parent']!=hi or si not in house['children'] or len(sp['children'])!=12:raise ValueError('SPHERE_INVALID')
            for n in range(1,13):
                nid=f'{si}.N{n:02}'; item=d['nodes'][nid]
                if item['id']!=nid or item['parent']!=si or nid not in sp['children']:raise ValueError('NODE_INVALID')
                expect='DOMAIN_SPECIALIZATION' if s<=7 else 'EPISTEMIC_META'
                if item['kind']!=expect:raise ValueError('ROLE_INCORRECT')
                if not re.fullmatch(r'[0-9a-f]{64}',item['source_record_sha256']):raise ValueError('NODE_DIGEST_INVALID')
                records.append({'id':nid,'house':hi,'houseName':house['name'],'sphere':si,'sphereName':sp['name'],'name':item['name'],
                    'kind':item['kind'],'sourceSha':item['source_record_sha256'],'definition':item['definition'],
                    'includes':item['includes'],'excludes':item['excludes']})
    if len(set(x['sourceSha'] for x in records))!=1728:raise ValueError('DUPLICATE_NODE_SOURCE_SHA')
    return records


def read_coverage(path:Path):
    i=json.loads(path.read_text(encoding='utf-8'))
    ar=i.get('address_readings',{})
    # Reading-index keys may represent Spheres, not individual node evidence.
    nodes={k for k in ar if re.fullmatch(r'H\d\d\.S\d\d\.N\d\d',k)}
    return nodes,{'historicalRecordCount':len(i.get('reading_records',[])),'nodeAddressesWithReadings':len(nodes),'nonNodeReadingAddresses':len(ar)-len(nodes)}


def tokenize(text):
    return frozenset(t for t in RE_TOKENS.findall(text.casefold()) if t not in STOP and len(t)>=4)


class CandidateIndex:
    """Same exact lexical score as exhaustive baseline; excludes only the label set.
    No semantic equality, no AI embeddings, and excluded text is never scored.
    """
    def __init__(self,records):
        self.records=records
        self.terms=[tokenize(x['name']+' '+x['definition']) for x in records]
        freq=collections.Counter(t for xs in self.terms for t in xs)
        self.weights={t:math.log((1+len(records))/(1+c))+1 for t,c in freq.items()}
        self.postings=collections.defaultdict(list)
        for idx,ts in enumerate(self.terms):
            for t in sorted(ts): self.postings[t].append(idx)
    def score(self,idx,query):
        return sum(self.weights[t] for t in query if t in self.terms[idx])
    def baseline(self,query,exclude_house=None,role=None,k=12):
        terms=tokenize(query)
        found=[(self.score(i,terms),i) for i,x in enumerate(self.records)
               if (exclude_house is None or x['house']!=exclude_house) and (role is None or x['kind']==role)]
        return [(self.records[i]['id'],round(score,12)) for score,i in sorted(found,key=lambda v:(-v[0],v[1])) if score>0][:k]
    def indexed(self,query,exclude_house=None,role=None,k=12):
        terms=tokenize(query)
        candidates=set()
        for term in terms: candidates.update(self.postings.get(term,()))
        found=[(self.score(i,terms),i) for i in candidates if (exclude_house is None or self.records[i]['house']!=exclude_house)
               and(role is None or self.records[i]['kind']==role)]
        return [(self.records[i]['id'],round(score,12)) for score,i in sorted(found,key=lambda v:(-v[0],v[1])) if score>0][:k]


def typed_links(records,index):
    links=[]
    for r in records:
        q=r['name']+' '+r['definition']
        candidates=index.indexed(q,exclude_house=r['house'],role='DOMAIN_SPECIALIZATION',k=6)
        # Source is deliberately lexical only. Do not infer a human-validated relation.
        best=[(coord,score) for coord,score in candidates if coord!=r['id']][:2]
        links.append({'from':r['id'],'candidates':[{'target':t,'lexicalScore':v,
           'type':'RELATED_CANDIDATE_UNREVIEWED', 'review':'REQUIRES_SOURCE_AND_SUBJECT_REVIEW'} for t,v in best],
           'sourceDigest':r['sourceSha'],'sourceRole':r['kind'],
           'subjectRequired':r['kind']=='EPISTEMIC_META'})
    return links


def guard_packet(p,expected=None):
    """Public-safe detached data-only gate, not a trusted host policy."""
    h={'status':'HOLD','reason':'NOT_AUTHORIZED','hostAuthenticated':False,'externalEffects':0,'messagePosts':0}
    if not isinstance(p,dict) or set(p)!={'coordinate','mode','sourceSha','rightsAtRead','rightsAtReturn','evidenceKind','subject','fictionLabel','epoch'}:return h
    if any(type(p[k]) is not str for k in ('coordinate','mode','sourceSha','rightsAtRead','rightsAtReturn','evidenceKind','subject','fictionLabel')):return h
    if not isinstance(p['epoch'],int) or isinstance(p['epoch'],bool) or p['epoch']<1:return h
    if not re.fullmatch(r'H(?:0[1-9]|1[0-2])\.S(?:0[1-9]|1[0-2])\.N(?:0[1-9]|1[0-2])',p['coordinate']):return h
    if p['mode']!='WORK' or p['rightsAtRead']!='PASS' or p['rightsAtReturn']!='PASS':return h
    if p['evidenceKind']!='SYNTHETIC_OR_PUBLIC' or not re.fullmatch('[a-f0-9]{64}',p['sourceSha']):return h
    if expected and (p['coordinate']!=expected['id'] or p['sourceSha']!=expected['sourceSha']):return h
    if p['fictionLabel'] not in {'FICTION_ONLY','NOT_FICTION'}:return h
    if p['subject']=='NONE' and int(p['coordinate'][5:7])>=8:return h
    return {'status':'PREPARED_NOT_SENT','hostAuthenticated':False,'externalEffects':0,'messagePosts':0,
       'rightsAtReturnVerifiedByHost':False,'releaseEligible':False}


def manifest(records,coverage,links):
    out=[]
    for idx,(r,l) in enumerate(zip(records,links),1):
        family='RESEARCH' if r['kind']=='DOMAIN_SPECIALIZATION' else 'METHOD'
        action={'id':f'UPG-{idx:04}', 'coordinate':r['id'],'sourceSha':r['sourceSha'],'house':r['house'],'sphere':r['sphere'],
                'name':r['name'],'kind':r['kind'],'directHistoricalReadings':r['id'] in coverage,
                'crossHouse':l['candidates'],'status':'PREPARED_SOURCE_BOUND_CANDIDATE_NOT_ADOPTED','authority':'NONE',
                'workOrders':{
                  'SwarmChat':f'Work-only provenance and falsifier thread for {r["id"]}; no automatic wake',
                  'Atlas':f'Attach source/rights/quality/rollback receipt to typed {family.lower()} packet {r["id"]}',
                  'Ariadne':f'Independently review {r["id"]} and its {len(l["candidates"])} cross-House lexical candidates',
                  'Iron Empire':f'Optional author-only FICTION concept from {r["id"]}; no scientific or canon assertion'
                }}
        out.append(action)
    return out


def simulation(records,coverage,outdir):
    """Closed-form hypothetical horizon: ONE evaluation represents 1,728 model years.
    Not 5.16 billion executed annual updates, no real wellbeing/AI measurement.
    The solo/isolated/collaborative strategies use identical 12 abstract attention units.
    """
    n=len(records);node=np.arange(n,dtype=np.uint64)
    # Seeded by exact source digests, not invented semantic confidence.
    seeds=np.asarray([int(r['sourceSha'][:8],16) for r in records],dtype=np.uint64)
    direct=np.asarray([int(r['id'] in coverage) for r in records],dtype=np.float64)
    base=0.30+direct*0.06+np.asarray([r['kind']=='EPISTEMIC_META' for r in records])*0.015
    baseline=base.copy(); isolated=base.copy(); council=base.copy()
    decay=math.exp(-YEARS/5200.0)  # EXACT analytic horizon of a fixed-target recurrence
    # One round per source node. Each round computes all 1,728 node-world trajectories.
    outputs=np.empty((ROUNDS,n,3),dtype=np.float32)
    roll=np.roll
    for round_i in range(ROUNDS):
        # Deterministic public-safe synthetic challenge/latent target; not measurement.
        noise=((seeds+np.uint64(7919*round_i))%np.uint64(65521)).astype(np.float64)/65520.0-.5
        context=roll(noise,144)
        truth=np.clip(base+.17*noise+.09*context,0,1)
        # Same budget: Solo 12 units depth, isolated 12 one-unit alternatives,
        # council 8 attempts +4 synthesis, no token or actual model calls.
        bias=(noise*.13+.036)
        solo_pred=np.clip(truth+bias,0,1)
        isolated_pred=np.clip(truth+np.minimum(abs(bias),abs(context*.14))*np.sign(context),0,1)
        council_pred=np.clip(truth+noise*.038+context*.047+0.025*np.sin(round_i/23),0,1)
        baseline=decay*baseline+(1-decay)*solo_pred
        isolated=decay*isolated+(1-decay)*isolated_pred
        council=decay*council+(1-decay)*council_pred
        # The metric is absolute synthetic oracle error. Lower is better; proxy only.
        outputs[round_i,:,0]=abs(baseline-truth)
        outputs[round_i,:,1]=abs(isolated-truth)
        outputs[round_i,:,2]=abs(council-truth)
    outdir.mkdir(exist_ok=True,parents=True)
    np.savez_compressed(outdir/'closed_form_1728x1728.npz',error=outputs,coordinate=np.asarray([r['id'] for r in records]))
    flat=outputs[:,:,0];ind=outputs[:,:,1];coll=outputs[:,:,2]
    tol=1e-6; win=(coll<flat-tol);loss=(coll>flat+tol);tie=~(win|loss)
    win_iso=(coll<ind-tol);loss_iso=(coll>ind+tol)
    metrics={'simulatedTrajectories':int(ROUNDS*n),'yearsPerTrajectory':YEARS,
       'symbolicModelYears':int(ROUNDS*n*YEARS),'annualUpdatesActuallyExecuted':0,
       'analyticClosedFormUsed':True,'initialConditionIsSynthetic':True,
       'sameAbstractAttentionBudget':12,'soloAllocation':[12], 'isolatedAllocation':[1]*12, 'councilAllocation':[8,4],
       'MAE':{'solo':float(flat.mean()),'isolated':float(ind.mean()),'council':float(coll.mean())},
       'councilVsSolo':{'better':int(win.sum()),'worse':int(loss.sum()),'tie':int(tie.sum())},
       'councilVsIsolated':{'better':int(win_iso.sum()),'worse':int(loss_iso.sum()),'tie':int((~(win_iso|loss_iso)).sum())},
       'counterexampleWhereCouncilWorse':int(np.flatnonzero(loss)[0]) if loss.any() else None,
       'sourceRegistrySha256':REGISTRY_SHA,'realAgentTurns':0,'humanGradeCases':0,
       'performanceClaim':'SYNTHETIC_ORACLE_ERROR_NOT_PRODUCT_PERFORMANCE',
       'simulatorAlgorithm':'q_after_1728_years = exp(-1728/5200)*q_before + (1-exp(-1728/5200))*fixed_scenario_target',
       'hostedModelCalls':0,'realElapsedYears':0,'authorityEffect':'NONE'}
    (outdir/'synthetic_outcomes.json').write_text(json.dumps(metrics,indent=2))
    return metrics


def run_stages(records,orders,metrics,outdir):
    head=digest({'genesis':'ATLAS-20-STAGES','source':REGISTRY_SHA})
    receipts=[];cumulative=[]
    for idx,(num,label,guard) in enumerate(STAGES,1):
        cumulative.append(guard)
        stage={'stage':idx,'label':label,'guard':guard,'nodeAddressesCovered':len(records),'sphereCount':144,'houses':12,
          'inputSource':REGISTRY_SHA,'priorReceipt':head,'inheritedGuards':cumulative.copy(),
          'reviewCodeExecuted':['read_registry','CandidateIndex','guard_packet','simulation','run_stages'],
          'sourceOnly':True,'peerModelTurns':0,'hostPermissions':False,'verifiedBenefit':False,
          'outputPlanDigest':digest([o['id']+o['sourceSha'] for o in orders]),
          'testRequirement':f'Reject bypass of {guard} on source-safe synthetic fixture; preserve prior guards'}
        head=digest(stage);receipts.append({**stage,'receiptSha256':head})
    (outdir/'macroturns_20_local.jsonl').write_text(''.join(json.dumps(v,sort_keys=True)+'\n' for v in receipts))
    return head


def bench_index(index,records,outdir):
    queries=[index.records[(h*12+s)*12]['sphereName']+' '+index.records[(h*12+s)*12]['name'] for h in range(12) for s in range(12)]
    # Exact-result parity before timing.
    for q in queries:
        if index.baseline(q,k=24)!=index.indexed(q,k=24): raise ValueError('INDEX_RESULT_DRIFT')
    iterations=7;timings=[]
    for q in queries:
        base=[];opt=[]
        for rep in range(iterations):
            if rep%2:
                t=time.perf_counter_ns();index.indexed(q,k=24);opt.append((time.perf_counter_ns()-t)/1e6)
                t=time.perf_counter_ns();index.baseline(q,k=24);base.append((time.perf_counter_ns()-t)/1e6)
            else:
                t=time.perf_counter_ns();index.baseline(q,k=24);base.append((time.perf_counter_ns()-t)/1e6)
                t=time.perf_counter_ns();index.indexed(q,k=24);opt.append((time.perf_counter_ns()-t)/1e6)
        timings.append({'sphere':records[len(timings)*12]['sphere'],'baselineMedianMs':statistics.median(base),
                        'indexedMedianMs':statistics.median(opt),'exactParity':True,'speedup':statistics.median(base)/max(1e-9,statistics.median(opt))})
    (outdir/'search_144_pair_benchmark.csv').write_text('sphere,baselineMedianMs,indexedMedianMs,speedup,exactParity\n'+''.join(
      f"{x['sphere']},{x['baselineMedianMs']:.9f},{x['indexedMedianMs']:.9f},{x['speedup']:.5f},{x['exactParity']}\n" for x in timings))
    return {'spheresCompared':144,'exactRankedResultParity':144,'measurementsPerImplementation':iterations,
       'medianBaselineMs':statistics.median(x['baselineMedianMs'] for x in timings),
       'medianIndexedMs':statistics.median(x['indexedMedianMs'] for x in timings),
       'medianPairedSpeedup':statistics.median(x['speedup'] for x in timings),
       'sphereGains':sum(x['speedup']>1 for x in timings),'sphereLosses':sum(x['speedup']<1 for x in timings),
       'scope':'LOCAL_PYTHON_LEXICAL_RETRIEVAL_NOT_LIVE_SWARMCHAT'}


def build(registry:Path,reading:Path,out:Path,bench=True):
    records=read_registry(registry)
    coverage,covstat=read_coverage(reading)
    index=CandidateIndex(records)
    links=typed_links(records,index)
    orders=manifest(records,coverage,links)
    sim=simulation(records,coverage,out)
    stages=run_stages(records,orders,sim,out)
    with (out/'node_build_orders_1728.jsonl').open('w') as f:
        for order in orders: f.write(json.dumps(order,sort_keys=True,ensure_ascii=False)+'\n')
    with (out/'typed_cross_house_1728.jsonl').open('w') as f:
        for a in links:f.write(json.dumps(a,sort_keys=True)+'\n')
    groups=[]
    for h in range(12):
      for s in range(12):
        a=records[(h*12+s)*12:(h*12+s+1)*12]
        groups.append({'sphere':a[0]['sphere'],'name':a[0]['sphereName'],'house':a[0]['house'],
                       'nodes':[x['id'] for x in a],'kind':a[0]['kind'],'status':'REVIEW_ONLY',
                       'implementationRoute':f'ONE/House{h+1:02d}/Sphere{s+1:02d}/LocalWorkPort'})
    (out/'sphere_modules_144.json').write_text(json.dumps(groups,indent=2,ensure_ascii=False))
    houses=[{'house':f'H{h+1:02d}','name':records[h*144]['houseName'],'spheres':groups[h*12:(h+1)*12],
             'hostInstalled':False,'proposalOnly':True} for h in range(12)]
    (out/'house_modules_12.json').write_text(json.dumps(houses,indent=2,ensure_ascii=False))
    benchmark=bench_index(index,records,out) if bench else {'status':'SKIPPED'}
    report={'schema':SCHEMA,'originalSourceDigest':REGISTRY_SHA,'nodeCount':len(records),'spheres':len(groups),'houses':len(houses),
        'nodeSourceDigestsUnique':len(set(x['sourceSha'] for x in records)),'coverage':covstat,'lexicalOnlyCrossHouseCandidates':sum(len(x['candidates']) for x in links),
        'candidateLinksAccepted':0,'realScientificDiscoveries':0,'offlineHouseModulesCompiled':12,'sourceBoundSphereRoutes':144,
        'sourceBoundNodeOrders':1728,'simulation':sim,'benchmark':benchmark,'localSyntheticReviewStages':20,'actualSwarmChatConversationsCounted':0,'macroturnReceiptHead':stages,
        'realSwarmChatMacroturnsInSimulation':0,'realPeerRepliesInSimulation':0,'actualIronEmpireCanonEdits':0,
        'hostDeployed':False,'productionReleaseAllowed':False,'authorityEffect':'NONE',
        'sourceMediaPolicy':'NO_PRIVATE_LEISURE_BODIES','evidenceClass':'OWNER_LOCAL_SYNTHETIC_CONTRACT'}
    (out/'FINAL_RECEIPT.json').write_text(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--registry',required=True,type=Path);p.add_argument('--reading',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--no-benchmark',action='store_true');args=p.parse_args()
    print(json.dumps(build(args.registry,args.reading,args.out,bench=not args.no_benchmark),indent=2))
