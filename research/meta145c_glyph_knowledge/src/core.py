"""Atlas R14: exact-source 144-perspective synthesis, reversible functional memory,
and namespace-isolated glyph/cymatic navigation. No AI model training or CANON.

The public module accepts owner-authorized source paths; no private source data
is shipped in the public GitHub code package.
"""
from __future__ import annotations
import csv,gzip,hashlib,json,re,sqlite3,statistics,time,io
from collections import Counter,defaultdict
from pathlib import Path
from .glyph import REGISTRY_SHA,typed_route,hsn_parts
from .memory import LocalMemory,canonical,sha

OPENALEX_SHA='a306c7306a79754b033e9f8c41c0de5ff5176b4544a6a80b5c740e2f8d2cc903'
ROLE_DOMAIN='DOMAIN_SPECIALIZATION';ROLE_META='EPISTEMIC_META'
STOP=frozenset('and the or of in on at to a an for with by from as is are into their whose within science scientific studies systems study general theory methods learning research design effects questions models model knowledge history ai'.split())
TOKENS=re.compile(r'[a-z0-9]+')

def tokens(s):
    if not isinstance(s,str):raise ValueError('TEXT_REQUIRED')
    return frozenset(x for x in TOKENS.findall(s.casefold()) if len(x)>2 and x not in STOP)

def digest_file(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class SourceSnapshot:
    def __init__(self,registry_path,openalex_path=None,expected_sha=REGISTRY_SHA,expected_topic_sha=OPENALEX_SHA):
        raw=Path(registry_path).read_bytes()
        self.registry_sha=sha(raw)
        if self.registry_sha!=expected_sha:raise ValueError('ARIADNE_SOURCE_DIGEST_MISMATCH')
        j=json.loads(raw)
        if not all(k in j for k in ('houses','spheres','nodes')):raise ValueError('ARIADNE_STRUCTURE_MISSING')
        self.houses=j['houses'];self.spheres=j['spheres'];self.nodes=j['nodes']
        if (len(self.houses),len(self.spheres),len(self.nodes))!=(12,144,1728):raise ValueError('ARIADNE_CARDINALITY_INVALID')
        for h in range(1,13):
            hid=f'H{h:02d}';hr=self.houses.get(hid)
            if not isinstance(hr,dict) or hr.get('id')!=hid or len(hr.get('children',[]))!=12:raise ValueError('HOUSE_INTEGRITY')
            roles=[]
            for s in range(1,13):
                sid=f'{hid}.S{s:02d}';sr=self.spheres.get(sid)
                if not isinstance(sr,dict) or sr.get('id')!=sid or sr.get('parent')!=hid or len(sr.get('children',[]))!=12 or sid not in hr['children']:raise ValueError('SPHERE_INTEGRITY')
                child_roles=set()
                for n in range(1,13):
                    nid=f'{sid}.N{n:02d}';nr=self.nodes.get(nid)
                    if not isinstance(nr,dict) or nr.get('id')!=nid or nr.get('parent')!=sid or nid not in sr['children'] or nr.get('kind') not in (ROLE_DOMAIN,ROLE_META) or not re.fullmatch(r'[0-9a-f]{64}',nr.get('source_record_sha256','')):raise ValueError('NODE_INTEGRITY')
                    child_roles.add(nr['kind'])
                if len(child_roles)!=1:raise ValueError('MIXED_SPHERE_ROLES')
                roles.append(next(iter(child_roles)))
            if roles.count(ROLE_DOMAIN)!=7 or roles.count(ROLE_META)!=5:raise ValueError('HOUSE_SPHERE_ROLE_DISTRIBUTION')
        self.node_ids=tuple(sorted(self.nodes))
        self.sphere_ids=tuple(sorted(self.spheres))
        self.topic_rows=[];self.topics_sha=None;self.topic_edges=[]
        if openalex_path:
            b=Path(openalex_path).read_bytes();self.topics_sha=sha(b)
            if self.topics_sha!=expected_topic_sha:raise ValueError('OPENALEX_SOURCE_DIGEST_MISMATCH')
            rows=list(csv.DictReader(b.decode('utf-8-sig').splitlines()))
            if len(rows)!=4516:raise ValueError('OPENALEX_COUNT')
            ids=set()
            for r in rows:
                tid=r['T_ID'];v=[r['Candidate_HSN']]+r['Other_4_HSN_candidates'].split(';')
                if tid in ids or not re.fullmatch(r'T[1-9][0-9]*',tid) or len(v)!=5 or len(set(v))!=5 or any(x not in self.nodes for x in v):raise ValueError('OPENALEX_CANDIDATE_STRUCTURE')
                if r['verified_exact'].lower()=='true' or r['reviewer_accepted'].lower()=='true':raise ValueError('OPENALEX_SOURCE_UNEXPECTED_PROMOTION')
                ids.add(tid)
                self.topic_rows.append({'topic_id':tid,'title':r['OpenAlex_topic_name_source'],
                   'subfield':r['Source_subfield_name'],'status':r['Status'],'candidates':v,'original_rank_score':r['Rank_score_NOT_probability']})
                for rank,nid in enumerate(v,1):self.topic_edges.append((tid,nid,rank,'HISTORICAL_HEURISTIC_CANDIDATE_UNREVIEWED'))
            if len(self.topic_edges)!=22580:raise ValueError('OPENALEX_EDGE_COUNT')

class SearchIndex:
    def __init__(self,snapshot):
        self.snapshot=snapshot
        self.documents=[tokens(snapshot.nodes[nid]['name']+' '+snapshot.spheres[nid[:7]]['name']) for nid in snapshot.node_ids]
        postings=defaultdict(list)
        for i,doc in enumerate(self.documents):
            for t in doc:postings[t].append(i)
        self.postings={k:tuple(v) for k,v in postings.items()}
    def perspective_terms(self,sid):
        s=self.snapshot.spheres[sid]
        # One source-grounded vocabulary lens per exact original Sphere.
        return tokens(s['name']+' '+' '.join(self.snapshot.nodes[nid]['name'] for nid in s['children'][:3]))
    def linear(self,termset):
        return [len(doc&termset) for doc in self.documents]
    def indexed(self,termset):
        out=[0]*len(self.documents)
        for t in termset:
            for i in self.postings.get(t,()):out[i]+=1
        return out
    def rank(self,query,limit=12,exclude_sphere=None,cross_house=False):
        if not isinstance(query,str) or not isinstance(limit,int) or not 1<=limit<=50:raise ValueError('QUERY_INVALID')
        score=self.indexed(tokens(query))
        out=[]
        for i,v in enumerate(score):
            if v<=0:continue
            nid=self.snapshot.node_ids[i]
            if exclude_sphere and nid.startswith(exclude_sphere+'.'):continue
            if cross_house and exclude_sphere and nid[:3]==exclude_sphere[:3]:continue
            out.append((nid,v))
        return sorted(out,key=lambda a:(-a[1],a[0]))[:limit]

def initialize_db(path,snapshot):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(p)
    db.executescript('''PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS sources(name TEXT PRIMARY KEY, digest TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS houses(hsn TEXT PRIMARY KEY,name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS spheres(hsn TEXT PRIMARY KEY,house TEXT NOT NULL,name TEXT NOT NULL,role TEXT NOT NULL,review_digest TEXT);
CREATE TABLE IF NOT EXISTS nodes(hsn TEXT PRIMARY KEY,sphere TEXT NOT NULL,name TEXT NOT NULL,role TEXT NOT NULL,record_digest TEXT NOT NULL,axg1 TEXT NOT NULL UNIQUE,gf7 TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS topics(id TEXT PRIMARY KEY,label TEXT NOT NULL,original_status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS topic_candidates(topic_id TEXT NOT NULL,hsn TEXT NOT NULL,rank INTEGER NOT NULL,relation TEXT NOT NULL,PRIMARY KEY(topic_id,rank));
CREATE TABLE IF NOT EXISTS sphere_lexical_candidates(sphere TEXT NOT NULL,hsn TEXT NOT NULL,overlap INTEGER NOT NULL,review_status TEXT NOT NULL,PRIMARY KEY(sphere,hsn));
CREATE INDEX IF NOT EXISTS topic_candidate_by_node ON topic_candidates(hsn);
CREATE INDEX IF NOT EXISTS sphere_candidate_by_node ON sphere_lexical_candidates(hsn);
''')
    db.execute('DELETE FROM sources');db.execute('INSERT INTO sources VALUES(?,?,?)',('ariadne_v07',snapshot.registry_sha,'EXACT_ORIGINAL_BYTES_VERIFIED'))
    if snapshot.topics_sha:db.execute('INSERT INTO sources VALUES(?,?,?)',('openalex_4516',snapshot.topics_sha,'HISTORICAL_UNREVIEWED_NOT_LIVE'))
    db.execute('DELETE FROM houses');db.execute('DELETE FROM spheres');db.execute('DELETE FROM nodes');db.execute('DELETE FROM topics');db.execute('DELETE FROM topic_candidates');db.execute('DELETE FROM sphere_lexical_candidates')
    db.executemany('INSERT INTO houses VALUES(?,?)',[(k,v['name']) for k,v in sorted(snapshot.houses.items())])
    db.executemany('INSERT INTO spheres(hsn,house,name,role) VALUES(?,?,?,?)',[(sid,s['parent'],s['name'],snapshot.nodes[s['children'][0]]['kind']) for sid,s in sorted(snapshot.spheres.items())])
    rows=[]
    for nid,n in sorted(snapshot.nodes.items()):
        route=typed_route(nid,snapshot.registry_sha)
        rows.append((nid,n['parent'],n['name'],n['kind'],n['source_record_sha256'],route['authored_axg1'],route['gf7_positional_analogy']))
    db.executemany('INSERT INTO nodes VALUES(?,?,?,?,?,?,?)',rows)
    if snapshot.topic_rows:
        db.executemany('INSERT INTO topics VALUES(?,?,?)',[(r['topic_id'],r['title'],r['status']) for r in snapshot.topic_rows])
        db.executemany('INSERT INTO topic_candidates VALUES(?,?,?,?)',snapshot.topic_edges)
    db.commit();return db

def compute_circuit(snapshot,index,outdir,db=None):
    """Runs 144 unique source-named lenses against 1,728 nodes each; no model turns."""
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    prev='0'*64; all_briefs=[]; house_followups=[]; comparisons=0; total_positive=0; unique_cross=set()
    with gzip.GzipFile(filename=str(out/'sphere_node_pair_matrix_248832.csv.gz'),mode='wb',compresslevel=6,mtime=0) as gz, io.TextIOWrapper(gz,encoding='utf-8',newline='') as f:
        writer=csv.writer(f);writer.writerow(('sphere','node','lexical_overlap','structural_relation','candidate_authority'))
        for sid in snapshot.sphere_ids:
            sphere=snapshot.spheres[sid];termset=index.perspective_terms(sid)
            scores=index.indexed(termset);cross=[];local=0;domain=0;meta=0
            for i,nid in enumerate(snapshot.node_ids):
                s=scores[i];comparisons+=1
                relation='SAME_SPHERE_SOURCE' if nid[:7]==sid else ('SAME_HOUSE_BROWSE' if nid[:3]==sid[:3] else 'CROSS_HOUSE_REVIEW_CANDIDATE')
                writer.writerow((sid,nid,s,relation,'NONE'))
                if s>0:
                    total_positive+=1
                    if nid[:3]!=sid[:3]:cross.append((nid,s));unique_cross.add((sid,nid))
                    if relation=='SAME_SPHERE_SOURCE':local+=1
                if snapshot.nodes[nid]['kind']==ROLE_DOMAIN:domain+=1
                else:meta+=1
            if domain!=1008 or meta!=720:raise AssertionError('INTEGRITY_ROLE')
            cross.sort(key=lambda x:(-x[1],x[0]))
            candidates=[{'hsn':nid,'overlap_count':s,'status':'UNREVIEWED_LEXICAL_NAVIGATION_ONLY'} for nid,s in cross[:8]]
            if db:
                db.executemany('INSERT INTO sphere_lexical_candidates VALUES(?,?,?,?)',[(sid,n,s,'UNREVIEWED_NAVIGATION_ONLY') for n,s in cross[:8]])
            brief={'sphere':sid,'name':sphere['name'],'house':sid[:3],
              'role':snapshot.nodes[sphere['children'][0]]['kind'],'unique_perspective':f'Compare each Ariadne address to {sid}: {sphere["name"]}, separating source containment from lexical navigation.',
              'query_terms':sorted(termset),'source_node_ids':sphere['children'],
              'source_node_record_digests':[snapshot.nodes[n]['source_record_sha256'] for n in sphere['children']],
              'total_comparisons':len(snapshot.node_ids),'same_sphere_positive_overlap':local,
              'cross_house_positive_overlap_candidates':len(cross),'top_cross_house_candidates':candidates,
              'negative_control':'Shared lexical tokens do not prove HSN meaning, causal effects, same-as, physics, rights or resident expertise.',
              'cumulative_prior_hash':prev,'unique_cross_candidate_count_so_far':len(unique_cross),
              'role_checks':{'domain_nodes':domain,'meta_nodes':meta},
              'status':'COMPUTED_SOURCE_TYPED_REVIEW_NOT_SEMANTICALLY_APPROVED'}
            receipt=sha(canonical(brief));brief['receipt_sha256']=receipt;prev=receipt;all_briefs.append(brief)
        if comparisons!=248832:raise AssertionError('CIRCUIT_COUNT')
    for hid in sorted(snapshot.houses):
        subset=[r for r in all_briefs if r['house']==hid]
        assert len(subset)==12
        follow={'house':hid,'name':snapshot.houses[hid]['name'],'sphere_receipts':[s['receipt_sha256'] for s in subset],
            'source_spheres':[s['sphere'] for s in subset],
            'source_nodes':[k for s in subset for k in s['source_node_ids']],
            'review_question':'Which historical source, contradictory evidence, role boundaries and rights gates would independently validate this House projection?',
            'status':'COMPUTED_HOUSE_REVIEW_REQUIREMENTS_NOT_PEER_JUDGMENTS'}
        follow['receipt_sha256']=sha(canonical(follow));house_followups.append(follow)
    if db:
        db.executemany('UPDATE spheres SET review_digest=? WHERE hsn=?',[(b['receipt_sha256'],b['sphere']) for b in all_briefs]);db.commit()
    (out/'sphere144_reviews.json').write_text(json.dumps(all_briefs,indent=2,ensure_ascii=False)+'\n')
    (out/'house12_followups.json').write_text(json.dumps(house_followups,indent=2,ensure_ascii=False)+'\n')
    return {'sphere_reviews':all_briefs,'house_followups':house_followups,'comparisons':comparisons,'positive_lexical_hits':total_positive,
            'unique_cross_house_candidate_pairs':len(unique_cross),'terminal_sphere_digest':prev}

def benchmark(index,repeat=31):
    if not 5<=repeat<=500:raise ValueError('BENCH_SAMPLE_COUNT')
    q=[index.perspective_terms(sid) for sid in index.snapshot.sphere_ids]
    baseline=[index.linear(x) for x in q]
    alt=[index.indexed(x) for x in q]
    if baseline!=alt:raise AssertionError('INDEX_PARITY_FAILURE')
    a=[];b=[]
    for _ in range(5):
        for terms in q: index.linear(terms);index.indexed(terms)
    for n in range(repeat):
        # alternate order avoids conflating monotonic drift with one algorithm
        order=('linear','indexed') if n%2==0 else ('indexed','linear')
        samples={}
        for method in order:
            t=time.perf_counter_ns()
            result=[getattr(index,method)(terms) for terms in q]
            elapsed=(time.perf_counter_ns()-t)/1e6
            if result!=baseline:raise AssertionError('BENCH_PARITY_FAILURE')
            samples[method]=elapsed
        a.append(samples['linear']);b.append(samples['indexed'])
    def p95(x):return sorted(x)[min(len(x)-1,int(len(x)*.95))]
    meda,medb=statistics.median(a),statistics.median(b)
    return {'kind':'LOCAL_PYTHON_CPU_BENCHMARK','scope':'144 source-grounded token-overlap query vectors across 1728 original nodes',
      'baseline_method':'LINEAR_FULL_SCAN','candidate_method':'INVERTED_INDEX_POSTINGS','samples':repeat,
      'baseline_median_ms':round(meda,5),'indexed_median_ms':round(medb,5),
      'baseline_p95_ms':round(p95(a),5),'indexed_p95_ms':round(p95(b),5),
      'median_speed_ratio':round(meda/medb,3) if medb else None,
      'paired_output_parity':True,'network_latency_measured':False,'hosted_swarmchat_measured':False,
      'model_weight_training':False}

def build(source_path,topics_path,outdir,repeat=31):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    s=SourceSnapshot(source_path,topics_path)
    start=time.perf_counter_ns();idx=SearchIndex(s);index_ms=(time.perf_counter_ns()-start)/1e6
    db=initialize_db(out/'atlas_meta145_knowledge.sqlite',s)
    circuit=compute_circuit(s,idx,out,db)
    perf=benchmark(idx,repeat)
    audit=sqlite3.connect(out/'atlas_meta145_knowledge.sqlite')
    rows={name:audit.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0] for name in ('houses','spheres','nodes','topics','topic_candidates','sphere_lexical_candidates')};integ=audit.execute('PRAGMA integrity_check').fetchone()[0];audit.close();db.close()
    if rows['topic_candidates']!=22580 or integ!='ok':raise AssertionError('DB_COVERAGE_FAILURE')
    meta={'schema':'atlas.meta145.glyph-functional-knowledge/v1','build_number':145,'algorithm':'144 source-unique Sphere lenses +1 non-authoritative synthesis',
       'source_reg_sha256':s.registry_sha,'historical_openalex_sha256':s.topics_sha,
       'synthetic_gf7_status':'ANALYTIC_MODEL_NOT_CALIBRATED','glyph_namespace':'AXG1_AUTHORED_ROUTING_NOT_ORIGINAL_KG8',
       'perspectives':144,'house_followups':12,'source_nodes':1728,'sphere_node_comparisons':circuit['comparisons'],
       'lexical_candidate_pairs_with_overlap':circuit['positive_lexical_hits'],'cross_house_lexical_candidate_pairs':circuit['unique_cross_house_candidate_pairs'],
       'topic_to_node_edges_unreviewed':len(s.topic_edges),'db_counts':rows,
       'source_circuit_terminal_receipt':circuit['terminal_sphere_digest'],
       'performance':{**perf,'index_build_time_ms':round(index_ms,4)},
       'real_resident_visits_claimed':0,'semantic_edges_approved':0,'wikimedia_live_fetches':0,'weights_trained':0,'host_rights_verified':False,
       'functional_memory':'APPEND_ONLY_LOCAL_REVIEW_EVENTS; TRIAGE_ONLY',
       'actual_measured_gain':'CPU retrieval speed for parity-equal lexical candidate queries only; not model capability/welfare or new knowledge truth',
       'can_auto_promote_canon':False,'deployment':'LOCAL_ONLY_NOT_HOSTED'}
    meta['meta_receipt_sha256']=sha(canonical(meta))
    (out/'META145_GLYPH_SYNTHESIS.json').write_text(json.dumps(meta,indent=2)+'\n')
    # Public-safe overview with counts; no source names/raw/private bodies.
    (out/'PUBLIC_RECEIPT.json').write_text(json.dumps({k:v for k,v in meta.items() if k not in ('performance',)},indent=2)+'\n')
    return meta
