#!/usr/bin/env python3
"""Atlas META145 glyph + knowledge organization circuit (original, source-only).

Not a resident, autonomous learning agent, audio/music generator, host permission,
physics measurement, CANON operation, or real SwarmChat publisher. All reads are
local and all output is candidate-only and source edition bound.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, math, os, re, sqlite3, statistics, tempfile, time
from pathlib import Path

SOURCE_SHA = '07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6'
SOURCE_EDITION='Ariadne v0.7'
ENGINE_VERSION='atlas.meta145.glyph.functional-memory/v2.0'
Q=('sala','sele','sili','solo','sulu','tara','tere','tiri','toro','turu','mara','mere')
S=('gal','gel','gil','gol','gul','nal','nel','nil','nol','nul','thal','thel')
STOP=frozenset('the and are for of a an to within from with each whose into there which whose whose or as by on this that its does only research primary focus questions methods observations artifacts source house sphere review records status histories source link proposed relevant original concepts explicit evidence across subjects scope domain node meta decision records history editorial and proof general material ideas learning'.split())
TOKEN=re.compile(r"[A-Za-z][A-Za-z0-9'-]*")
SPHERE_RE=re.compile(r'^H(0[1-9]|1[0-2])\.S(0[1-9]|1[0-2])$')
NODE_RE=re.compile(r'^H(0[1-9]|1[0-2])\.S(0[1-9]|1[0-2])\.N(0[1-9]|1[0-2])$')

class Held(ValueError):pass

def require(cond,code):
    if not cond:raise Held(code)

def sha(raw):return hashlib.sha256(raw).hexdigest()
def canon(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(obj):return sha(canon(obj).encode('utf-8'))
def write(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')

def tokens(text):return frozenset(x.lower() for x in TOKEN.findall(text) if len(x)>2 and x.lower() not in STOP)

def load_registry(path):
    raw=Path(path).read_bytes();require(sha(raw)==SOURCE_SHA,'ORIGINAL_SOURCE_HASH_MISMATCH')
    data=json.loads(raw)
    require(len(data['houses'])==12 and len(data['spheres'])==144 and len(data['nodes'])==1728,'SOURCE_CENSUS_MISMATCH')
    for h in range(1,13):
        house=f'H{h:02d}';require(len(data['houses'][house]['children'])==12,'HOUSE_CENSUS_MISMATCH')
        for s in range(1,13):
            sid=f'{house}.S{s:02d}';sphere=data['spheres'][sid];require(sphere['parent']==house and len(sphere['children'])==12,'SPHERE_CENSUS_MISMATCH')
            role='DOMAIN_SPECIALIZATION' if s<=7 else 'EPISTEMIC_META'
            for n in range(1,13):
                coord=f'{sid}.N{n:02d}';x=data['nodes'][coord]
                require(x['parent']==sid and x['kind']==role and re.fullmatch('[0-9a-f]{64}',x['source_record_sha256']) is not None,'ROLE_OR_RECORD_MISMATCH')
    return data

def gid(h,s,n,voice='Q'):
    require(1<=h<=12 and 1<=s<=12 and 1<=n<=12,'COORD_RANGE')
    require(voice in ('Q','S'),'VOICE_UNKNOWN')
    lex=Q if voice=='Q' else S
    return f'KG8{voice}:{SOURCE_SHA[:12]}:{lex[h-1]}.{lex[s-1]}.{lex[n-1]}'

def parse_glyph(code):
    require(isinstance(code,str),'GLYPH_INVALID')
    m=re.fullmatch(r'KG8([QS]):([0-9a-f]{12}):([a-z]+)\.([a-z]+)\.([a-z]+)',code)
    require(m and m[2]==SOURCE_SHA[:12],'GLYPH_EDITION_OR_NAMESPACE_MISMATCH')
    lex=Q if m[1]=='Q' else S
    try:h,s,n=[lex.index(x)+1 for x in m.groups()[2:]]
    except ValueError:raise Held('GLYPH_VOCABULARY_INVALID')
    return f'H{h:02d}.S{s:02d}.N{n:02d}'

def gf7(h,s,n):
    require(1<=h<=12 and 1<=s<=12 and 1<=n<=12,'COORD_RANGE')
    return {'coordinate':f'GF7.B{h:02d}.M{s:02d}.C{n:02d}', 'quenyaProjectCode':f'Q:{Q[h-1]}.{Q[s-1]}.{Q[n-1]}',
            'sindarinProjectCode':f'S:{S[h-1]}.{S[s-1]}.{S[n-1]}',
            'relation':'POSITIONAL_VISUAL_INDEX_ONLY','actualPlateMeasured':False,'physicalCouplingDemonstrated':False,
            'authorityEffect':'NONE','context':'SYNTHETIC_CYMATIC_PROFILE_NOT_HSN_MEANING'}

def parse_gf7(code):
    require(isinstance(code,str),'GF7_INVALID')
    m=re.fullmatch(r'GF7\.B(0[1-9]|1[0-2])\.M(0[1-9]|1[0-2])\.C(0[1-9]|1[0-2])',code)
    require(m,'GF7_INVALID')
    return 'H'+m[1]+'.S'+m[2]+'.N'+m[3]

def node_index(data):
    ids=list(data['nodes'])
    doc=[];postings=collections.defaultdict(list);frequency=collections.Counter()
    for i,c in enumerate(ids):
        x=data['nodes'][c]
        t=tokens(x['name']+' '+x['definition']+' '+x['includes'])
        doc.append(t)
        for word in sorted(t):postings[word].append(i);frequency[word]+=1
    require(len(doc)==1728,'INDEX_CENSUS_MISMATCH')
    return ids,doc,postings,frequency

def perspectives(data,df):
    out=[];signatures=set()
    for h in range(1,13):
        hid=f'H{h:02d}'
        for s in range(1,13):
            sid=f'{hid}.S{s:02d}';sphere=data['spheres'][sid]
            role='DOMAIN_SPECIALIZATION' if s<=7 else 'EPISTEMIC_META'
            own=sphere['children'];names=[data['nodes'][k]['name'] for k in own]
            house_words=tokens(data['houses'][hid]['name']);sphere_words=tokens(sphere['name']);node_words=collections.Counter(w for name in names for w in tokens(name))
            # Denominators tie weights to the pinned corpus. Integer weights make the
            # inverted and brute scorers exactly comparable without rounding claims.
            weighted={}
            for w in sphere_words|house_words|set(node_words):
                if df.get(w,0)>240:continue
                idf=max(1,min(64,1728//(1+df.get(w,0))))
                factor=(12 if w in sphere_words else 0)+(5 if w in house_words else 0)+min(4,node_words[w])*2
                weighted[w]=idf*factor
            # Repeated epistemic labels are still distinct HSN source records;
            # their shared tokens are NEVER scientific SAME_AS edges.
            require(weighted,'EMPTY_SPHERE_PERSPECTIVE')
            profile={'sphere':sid,'house':hid,'houseName':data['houses'][hid]['name'],
                     'sphereName':sphere['name'],'sourceRole':role,'scopeStatus':'EDITORIAL_PERSPECTIVE_NOT_SEMANTIC_REVIEW',
                     'sourceEdition':SOURCE_EDITION,'registrySha256':SOURCE_SHA,
                     'homeNodes':own,'homeNodeDigests':[data['nodes'][k]['source_record_sha256'] for k in own],
                     'weightedTerms':dict(sorted(weighted.items())),
                     'anchorTerms':sorted(weighted,key=lambda w:(-weighted[w],w))[:12],
                     'relationSemantics':'SAME_SPHERE | SAME_HOUSE | CROSS_HOUSE (STRUCTURAL_ONLY)',
                     'methodSubjectRequired':role=='EPISTEMIC_META',
                     'automatedSemanticApprovals':0,'independentlyReviewed':False}
            profile['perspectiveSha256']=digest(profile)
            require(profile['perspectiveSha256'] not in signatures,'DUPLICATE_SPHERE_PROFILE')
            signatures.add(profile['perspectiveSha256']);out.append(profile)
    require(len(out)==144 and len(signatures)==144,'PERSPECTIVE_COUNT')
    return out

def score_brute(profile,doc):
    weights=profile['weightedTerms']
    return [sum(weights.get(w,0) for w in words) for words in doc]

def score_indexed(profile,postings,size=1728):
    result=[0]*size
    for word,wgt in profile['weightedTerms'].items():
        for i in postings.get(word,()):result[i]+=wgt
    return result

def calculate(data,out:Path,do_sqlite=True):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    ids,docs,postings,df=node_index(data)
    profiles=perspectives(data,df)
    nodeProjection=[]
    for c in ids:
        x=data['nodes'][c];m=NODE_RE.fullmatch(c)
        h,s,n=map(int,m.groups());plate=gf7(h,s,n)
        nodeProjection.append({'coordinate':c,'name':x['name'],'kind':x['kind'],'sphere':c[:7], 'house':c[:3],
            'sourceRecordSha256':x['source_record_sha256'],'sourceEdition':SOURCE_EDITION,'sourceSha256':SOURCE_SHA,
            'glyphQ':gid(h,s,n,'Q'),'glyphS':gid(h,s,n,'S'),
            'cymaticAddress':plate['coordinate'],'cymaticRelation':'POSITIONAL_VISUAL_INDEX_ONLY',
            'sourceStatus':'UNREVIEWED_EDITORIAL_LOCATOR','semanticAccepted':False,'normativeAuthority':False})
    sqldb=out/'sphere_node_matrix_248832.sqlite3'
    if do_sqlite:
        if sqldb.exists():sqldb.unlink()
        cx=sqlite3.connect(sqldb)
        cx.execute('PRAGMA journal_mode=DELETE')
        cx.execute('PRAGMA synchronous=FULL')
        cx.executescript('''CREATE TABLE score (sphere TEXT NOT NULL,node TEXT NOT NULL,relation TEXT NOT NULL,score INTEGER NOT NULL,node_kind TEXT NOT NULL,PRIMARY KEY(sphere,node)) WITHOUT ROWID;
         CREATE INDEX score_sphere_rank ON score(sphere,score DESC,node);''')
    edges=[];house=collections.defaultdict(list);perSphere=[];rows=0;pairchain='0'*64
    for profile in profiles:
        sid=profile['sphere'];hid=profile['house']
        scores=score_indexed(profile,postings,len(ids))
        require(scores==score_brute(profile,docs),'INDEXED_SCORE_PARITY_FAILURE')
        allrows=[];eligibleSame=[];eligibleMethod=[]
        for i,c in enumerate(ids):
            relation='SAME_SPHERE' if c[:7]==sid else 'SAME_HOUSE' if c[:3]==hid else 'CROSS_HOUSE'
            role=data['nodes'][c]['kind'];score=scores[i]
            allrows.append((sid,c,relation,score,role));rows+=1
            if relation!='SAME_SPHERE' and score>0:
                # Every relation remains CANDIDATE. Across domain/method roles, a
                # source subject is REQUIRED before an applicability interpretation.
                shared=[w for w in profile['weightedTerms'] if w in docs[i] and df[w]<=96]
                if len(shared)>=2:
                    (eligibleSame if role==profile['sourceRole'] else eligibleMethod).append((score,len(shared),c,sorted(shared)[:5]))
        if do_sqlite:cx.executemany('INSERT INTO score VALUES (?,?,?,?,?)',allrows)
        # bounded, independent review suggestions; no forced connections.
        eligibleSame.sort(key=lambda z:(-z[0],-z[1],z[2]));eligibleMethod.sort(key=lambda z:(-z[0],-z[1],z[2]));
        chosen=eligibleSame[:6]+eligibleMethod[:4]
        cands=[]
        for score,sharedN,c,terms in chosen:
            crossing=data['nodes'][c]['kind']!=profile['sourceRole']
            candidate={'fromSphere':sid,'toNode':c,'toSphere':c[:7], 'toHouse':c[:3],
                    'scoreNotProbability':score,'sharedTermCount':sharedN,'sharedTerms':terms,
                    'fromRole':profile['sourceRole'],'toRole':data['nodes'][c]['kind'],
                    'typedRelation':'METHOD_LENS_APPLICABILITY_CANDIDATE' if crossing else 'LEXICAL_REVIEW_CANDIDATE_ONLY',
                    'requiresExplicitDomainSubject':crossing or profile['sourceRole']=='EPISTEMIC_META',
                    'domainSubjectCoordinate':None,'semanticAcceptance':'NOT_ADJUDICATED',
                    'sourceNodeSha256':data['nodes'][c]['source_record_sha256'],
                    'sourceEdition':SOURCE_EDITION,'sourceSha256':SOURCE_SHA}
            cands.append(candidate);edges.append(candidate)
        p={'sphere':sid,'sphereName':profile['sphereName'],'role':profile['sourceRole'],'house':hid,
           'sourcePerspectiveSha256':profile['perspectiveSha256'],'homeNodes':profile['homeNodes'],
           'evaluatedNodeCount':1728,'sameSphere':12,'sameHouseOtherSphere':132,'crossHouse':1584,
           'distinctiveTerms':profile['anchorTerms'],'topCandidateNodeIds':[c['toNode'] for c in cands],
           'lexicalCandidates':cands,'independentlyReviewed':False,'sourceRoleMismatchCount':0,
           'autonomousModelCalls':0,'semanticAccepted':0,'status':'COMPUTED_CANDIDATES_NOT_ADJUDICATED'}
        p['receiptSha256']=digest(p)
        pairchain=sha((pairchain+p['receiptSha256']).encode())
        p['cumulativeChainHead']=pairchain
        perSphere.append(p);house[hid].append(p)
    if do_sqlite:
        cx.commit();cx.execute('VACUUM');cx.commit();cx.close()
    require(rows==248832,'PAIR_CARDINALITY')
    houseDocs=[]
    for h in range(1,13):
        hid=f'H{h:02d}';items=house[hid];require(len(items)==12,'HOUSE_SPHERE_MISSING')
        r={'house':hid,'houseName':data['houses'][hid]['name'],'sphereIds':[p['sphere'] for p in items],
           'sourcePerspectiveDigests':[p['sourcePerspectiveSha256'] for p in items],
           'candidateNodeRefs':sum(len(p['topCandidateNodeIds']) for p in items),
           'domainSpheres':7,'methodSpheres':5,'domainNodes':84,'methodNodes':60,
           'crossHouseQuestion':f'Which candidate connections from {data["houses"][hid]["name"]} survive a specialist falsifier without overriding consent, rights or another House?',
           'epistemicFalsifier':'Same lexical token, method template or glyph position is not semantic equivalence',
           'releaseStatus':'HOUSE_SYNTHESIS_CANDIDATE_ONLY','canonEffect':'NONE'}
        r['receiptSha256']=digest(r);houseDocs.append(r)
    # Twelve honest House questions for EACH source Sphere. Candidate counts may
    # be zero: absence of lexical overlap is not expert knowledge absence.
    followups=[]
    for p in profiles:
        sid=p['sphere'];per=next(x for x in perSphere if x['sphere']==sid)
        for hi in range(1,13):
            hid=f'H{hi:02d}'
            near=[e for e in per['lexicalCandidates'] if e['toHouse']==hid]
            f={'id':f'{sid}|{hid}', 'sourceSphere':sid,'reviewHouse':hid,
                'reviewHouseName':data['houses'][hid]['name'],
                'perspectiveSha256':p['perspectiveSha256'],
                'sourceRole':p['sourceRole'],
                'question':f'How would {data["houses"][hid]["name"]} test or challenge the source-limited {p["sphereName"]} perspective, with independent evidence and consent?',
                'candidateNodeRefs':[e['toNode'] for e in near],
                'candidateOverlapCount':len(near),
                'domainSubjectRequired':p['sourceRole']=='EPISTEMIC_META',
                'logicalSourceNodeReferencesReused':1728,
                'newIndependentEvaluations':0,
                'reviewState':'FOLLOWUP_PROPOSED_NOT_PERFORMED',
                'semanticStatus':'UNREVIEWED','sourceEdition':SOURCE_EDITION,
                'sourceSha256':SOURCE_SHA,'rightsGranted':False,'canonEffect':'NONE'}
            f['receiptSha256']=digest(f);followups.append(f)
    require(len(followups)==1728 and len(set(f['id'] for f in followups))==1728,'HOUSE_SPHERE_CARDINALITY')
    out.mkdir(parents=True,exist_ok=True)
    (out/'house_sphere_followups_1728.jsonl').write_text(''.join(canon(f)+'\n' for f in followups),encoding='utf8')
    write(out/'perspectives_144.json',profiles)
    write(out/'node_glyphs_1728.json',nodeProjection)
    write(out/'sphere_reviews_144.json',perSphere)
    write(out/'house_syntheses_12.json',houseDocs)
    write(out/'candidate_edges.json',edges)
    meta={'schema':ENGINE_VERSION,'sourceRegistrySHA256':SOURCE_SHA,'sourceEdition':SOURCE_EDITION,
       'sourceRoleDistribution':{'DOMAIN_SPECIALIZATION':1008,'EPISTEMIC_META':720},
       'perspectives':144,'uniquePerspectiveDigests':len(set(p['perspectiveSha256'] for p in profiles)),
       'nodes':1728,'computedPairEvaluations':rows,'sphereReviewReceipts':144,'houseSynthesisReceipts':12,'houseSphereFollowupReceipts':1728,
       'referencedSourceNodePositionsReused':1728*1728,'additionalIndependentPairEvaluationsFromFollowups':0,
       'glyphAliases':2*1728,'syntheticCymaticPositions':1728,'candidateEdges':len(edges),
       'sphereChainHead':pairchain,'candidateLinkKinds':dict(collections.Counter(e['typedRelation'] for e in edges)),
       'previousMeta145':{'source':'https://github.com/atlaslattice/noosphere-archive/pull/35',
         'claimStatus':'HISTORICAL_LOCAL_SOURCE_REPORTED_NOT_REMEASURED_IN_THIS_BUILD',
         'medianBroadSearchSpeedup':12.17,'p95BroadSearchSpeedup':19.25,
         'independentImprovementLayersMustNotBeMultiplied':True},
       'learning':{'kind':'REPRODUCIBLE_FUNCTIONAL_FEEDBACK_NOT_MODEL_WEIGHT_TRAINING',
                   'continuousBackgroundExecution':False,'requiresGenuineInvocation':True,
                   'externalSemanticsAccepted':0,'privateModeContentIngested':0},
       'semanticAcceptanceCount':0,'siteDeployed':False,'hostRightsVerified':False,
       'independentlyAuthenticatedResidents':0,'canonAltered':False,'fictionCanonChanged':False,'paidModelCalls':0,
       'outputs':{}}
    for name in ['perspectives_144.json','node_glyphs_1728.json','sphere_reviews_144.json','house_syntheses_12.json','house_sphere_followups_1728.jsonl','candidate_edges.json']:
        meta['outputs'][name]=sha((out/name).read_bytes())
    if do_sqlite:meta['outputs'][sqldb.name]=sha(sqldb.read_bytes())
    meta['meta145Digest']=digest(meta)
    write(out/'META145_GLYPH_MEMORY.json',meta)
    return meta

class FunctionalMemory:
    """File-backed, voluntarily invoked, append-only algorithm feedback. NOT a Brain.
       No telemetry, task spam, resident identity or silent model retraining.
    """
    def __init__(self,path):self.path=Path(path);self.rows=self.verify(self.path) if self.path.exists() else []
    @staticmethod
    def verify(path):
        prev='0'*64;rows=[];seen={}
        for line in Path(path).read_text(encoding='utf8').splitlines():
            record=json.loads(line); content={k:v for k,v in record.items() if k!='chainSHA256'}
            require(record['previousSHA256']==prev,'MEMORY_CHAIN_BROKEN')
            require(digest(content)==record['chainSHA256'],'MEMORY_HASH_MISMATCH')
            id=record['eventId'];require(id not in seen,'MEMORY_REPLAY_DUPLICATE');seen[id]=True
            require(record['mode']=='WORK' and record['sourceSHA256']==SOURCE_SHA and
                    record['authorityEffect']=='NONE' and record['privateModeIngested']==False,'MEMORY_SCOPE_VIOLATION')
            rows.append(record);prev=record['chainSHA256']
        return rows
    def append(self,event):
        require(set(event)=={'eventId','kind','mode','sourceSHA256','sourceInputDigest','outputsMatch',
                            'benchmark','authorityEffect','privateModeIngested','status'},'MEMORY_EVENT_SHAPE')
        require(event['mode']=='WORK' and event['sourceSHA256']==SOURCE_SHA and
                event['authorityEffect']=='NONE' and event['privateModeIngested'] is False,'MEMORY_SCOPE_VIOLATION')
        require(event['status'] in ('VERIFIED_LOCAL_PERFORMANCE','REGRESSION_FAILED','REVIEW_CANDIDATE') ,'MEMORY_STATUS_INVALID')
        require(event['eventId'] not in {r['eventId'] for r in self.rows},'MEMORY_EVENT_ID_REPLAY')
        if event['status']=='VERIFIED_LOCAL_PERFORMANCE':
            require(event['outputsMatch'] is True and event['benchmark']['baselineMedianMs']>0 and
                event['benchmark']['optimizedMedianMs']>0 and event['benchmark']['medianSpeedup']>1,
                'UNVERIFIED_PERFORMANCE_PROMOTION')
        record={'sequence':len(self.rows)+1,'previousSHA256':self.rows[-1]['chainSHA256'] if self.rows else '0'*64,**event}
        record['chainSHA256']=digest(record)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open('a',encoding='utf8') as f:
            f.write(canon(record)+'\n');f.flush();os.fsync(f.fileno())
        self.rows.append(record)
        return record
    def policy(self,currentSourceInputDigest=None):
        valid=[r for r in self.rows if r['status']=='VERIFIED_LOCAL_PERFORMANCE' and r['outputsMatch']
               and (currentSourceInputDigest is None or r['sourceInputDigest']==currentSourceInputDigest)]
        return {'selected':'POSTINGS_INDEX' if valid else 'BASELINE_SCAN',
                'selectionStatus':'REPLAYED_VERIFIED_LOCAL_FEEDBACK_NOT_SCIENTIFIC_LEARNING',
                'evidenceEventIds':[x['eventId'] for x in valid],
                'sourceSHA256':SOURCE_SHA,'sourceInputDigest':currentSourceInputDigest,'siteDeployed':False}

def benchmark(data,samples=7):
    ids,docs,postings,df=node_index(data);ps=perspectives(data,df)
    expected=[score_brute(p,docs) for p in ps]
    parity=all(score_indexed(p,postings)==expected[i] for i,p in enumerate(ps));require(parity,'SCORE_PARITY_FAILED')
    # Balanced alternating order to reduce systematic warmed-cache bias.
    results={'baseline':[],'indexed':[]}
    for _ in range(2):
        for p in ps[:4]:score_brute(p,docs);score_indexed(p,postings)
    for cycle in range(samples):
        for method in (('baseline','indexed') if cycle%2==0 else ('indexed','baseline')):
            start=time.perf_counter_ns()
            for p in ps:
                if method=='baseline':score_brute(p,docs)
                else:score_indexed(p,postings)
            results[method].append((time.perf_counter_ns()-start)/1e6)
    base=statistics.median(results['baseline']);fast=statistics.median(results['indexed']);ratio=base/fast
    return {'schema':'atlas.meta145.local.cpu-benchmark/v1','samplesPerMethod':samples,
            'benchmarkScope':'144×1728 token-overlap integer scorer, 1 host process, no network',
            'baselineMedianMs':round(base,3),'optimizedMedianMs':round(fast,3),
            'medianSpeedup':round(ratio,3),'exactOutputParity':parity,
            'baselineRunsMs':[round(v,3) for v in results['baseline']],
            'optimizedRunsMs':[round(v,3) for v in results['indexed']],
            'notMeasured':['hosted SwarmChat latency','Cymatic physical computation','AI reasoning quality','model training'],
            'clock':'time.perf_counter_ns','sourceSHA256':SOURCE_SHA}

def verify_build(registry,out):
    data=load_registry(registry);out=Path(out)
    meta=json.loads((out/'META145_GLYPH_MEMORY.json').read_text());h=meta.pop('meta145Digest')
    require(digest(meta)==h,'META145_DIGEST_CHANGED');meta['meta145Digest']=h
    require(meta['sourceRegistrySHA256']==SOURCE_SHA and meta['computedPairEvaluations']==248832,'META145_SOURCE_OR_COUNT')
    for name,v in meta['outputs'].items():require(sha((out/name).read_bytes())==v,'OUTPUT_DIGEST_CHANGED_'+name)
    ps=json.loads((out/'perspectives_144.json').read_text());nodes=json.loads((out/'node_glyphs_1728.json').read_text());sps=json.loads((out/'sphere_reviews_144.json').read_text());houses=json.loads((out/'house_syntheses_12.json').read_text())
    require(len(ps)==144 and len(nodes)==1728 and len(sps)==144 and len(houses)==12,'OUTPUT_COUNTS')
    require(len(set(p['perspectiveSha256'] for p in ps))==144,'PERSPECTIVE_DUPLICATE')
    for p in ps:
        x=dict(p);current=x.pop('perspectiveSha256');require(digest(x)==current,'PERSPECTIVE_HASH_CHANGED')
        require(p['sourceRole']==('DOMAIN_SPECIALIZATION' if int(p['sphere'][5:7])<=7 else 'EPISTEMIC_META'),'ROLE_AXIS_CHANGED')
    for rec in nodes:
        m=NODE_RE.fullmatch(rec['coordinate']);require(m,'NODE_COORDINATE_INVALID')
        a,b,c=map(int,m.groups());require(rec['glyphQ']==gid(a,b,c,'Q') and rec['glyphS']==gid(a,b,c,'S'),'GLYPH_MAPPING_CHANGED')
        require(parse_glyph(rec['glyphQ'])==rec['coordinate'] and parse_gf7(rec['cymaticAddress'])==rec['coordinate'],'GF7_ALIAS_MISMATCH')
        require(rec['kind']==data['nodes'][rec['coordinate']]['kind'] and rec['sourceRecordSha256']==data['nodes'][rec['coordinate']]['source_record_sha256'],'SOURCE_NODE_MISMATCH')
    cx=sqlite3.connect(out/'sphere_node_matrix_248832.sqlite3')
    try:
        n=cx.execute('SELECT count(*) FROM score').fetchone()[0];require(n==248832,'MATRIX_LENGTH')
        for p in (ps[0],ps[85],ps[-1]):
            c=cx.execute('SELECT count(*) FROM score WHERE sphere=?',(p['sphere'],)).fetchone()[0];require(c==1728,'MATRIX_SPHERE_COVERAGE')
    finally:cx.close()
    for s in sps:require(s['semanticAccepted']==0 and s['evaluatedNodeCount']==1728,'SEMANTIC_SCOPE_CHANGED')
    with (out/'house_sphere_followups_1728.jsonl').open(encoding='utf8') as ff:
        n=0
        for line in ff:
            rec=json.loads(line);sid=ps[n//12]['sphere'];hid=f'H{n%12+1:02d}'
            require(rec['sourceSphere']==sid and rec['reviewHouse']==hid,'FOLLOWUP_ADDRESS_CHANGED')
            a=dict(rec);stored=a.pop('receiptSha256');require(digest(a)==stored,'FOLLOWUP_DIGEST_CHANGED')
            require(rec['newIndependentEvaluations']==0 and not rec['rightsGranted'] and rec['semanticStatus']=='UNREVIEWED','FOLLOWUP_FALSE_PROMOTION')
            n+=1
        require(n==1728,'FOLLOWUP_COUNT_CHANGED')
    return {'status':'PASS_LOCAL_REPRODUCIBLE','sourceSHA256':SOURCE_SHA,'spherePerspectives':144,'nodeAliases':1728,'matrixPairs':248832,'meta145Digest':h,'hostVerified':False,'modelWeightsChanged':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('cmd',choices=['build','verify','bench','memory']);p.add_argument('--registry',required=True);p.add_argument('--out',required=True);p.add_argument('--samples',type=int,default=7);a=p.parse_args()
    src=Path(a.registry);out=Path(a.out)
    if a.cmd=='build':print(canon(calculate(load_registry(src),out)))
    elif a.cmd=='verify':print(canon(verify_build(src,out)))
    elif a.cmd=='bench':
        b=benchmark(load_registry(src),a.samples);write(out/'bench_current.json',b);print(canon(b))
    elif a.cmd=='memory':
        perf=json.loads((out/'bench_current.json').read_text());manifest=json.loads((out/'META145_GLYPH_MEMORY.json').read_text());event={
          'eventId':'sphere-scoring-index-v1-'+manifest['meta145Digest'][:16],
          'kind':'SCORING_INDEX_REPLAY','mode':'WORK','sourceSHA256':SOURCE_SHA,'sourceInputDigest':manifest['meta145Digest'],
          'outputsMatch':perf['exactOutputParity'],'benchmark':perf,'authorityEffect':'NONE','privateModeIngested':False,
          'status':'VERIFIED_LOCAL_PERFORMANCE' if perf['exactOutputParity'] and perf['medianSpeedup']>1 else 'REVIEW_CANDIDATE'}
        mem=FunctionalMemory(out/'functional_memory.jsonl')
        if event['eventId'] not in {x['eventId'] for x in mem.rows}:mem.append(event)
        policy=mem.policy(manifest['meta145Digest'])
        write(out/'functional_memory_replay.json',policy);print(canon(policy))
if __name__=='__main__':main()
