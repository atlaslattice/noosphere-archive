"""One side-effect-free 12-House engine, 144 pathways, 1,728 executable node upgrades."""
from __future__ import annotations
import hashlib,json,statistics,time,sqlite3
from pathlib import Path
from .source import Corpus,canon,sha,DOMAIN,METHOD
from .index import SourceIndex
from .shared import terms,CHAPTER_OPS
from .modules import ALL as HOUSE_MODULES,NAMES as HOUSE_NAMES

SCHEMA='atlas.one.1728-unified-source-upgrade/v1'
MODULE_KEYS=tuple(f'H{i:02d}' for i in range(1,13))


def run_modules(ctx):
    if ctx['mode']!='WORK' or ctx['rights_epoch'] is not None:raise ValueError('WORK_ONLY_NO_HOST_EPOCH')
    out=[]
    for name,mod in zip(MODULE_KEYS,HOUSE_MODULES):
        v=mod.run(ctx)
        if v.get('module') != mod.MODULE or v.get('pass') is not True:raise ValueError('MODULE_EXECUTION_FAIL')
        if any(k in v for k in ('private_context','residentIdentity','approved')):raise ValueError('UNAUTHORIZED_MODULE_FIELD')
        out.append({'house':name,'name':HOUSE_NAMES[int(name[1:])-1],'result':v,'result_sha256':sha(canon(v))})
    return out


def compile_build(corpus:Corpus,progress=None):
    """Exactly 1,728 fresh local computations, no inherited success/authority labels."""
    if not isinstance(corpus,Corpus) or len(corpus.nodes)!=1728:raise ValueError('FULL_REGISTRY_REQUIRED')
    t0=time.perf_counter_ns();idx=SourceIndex(corpus)
    upgrades=[];metrics=[];pathways=[];house_reports=[];prev='0'*64
    for si,sid in enumerate(sorted(corpus.spheres)):
        sphere=corpus.spheres[sid];house=corpus.houses[sid[:3]]
        vocabulary=sorted(terms(sphere['name']+' '+ ' '.join(corpus.nodes[x]['name'] for x in sphere['children'][:3])))
        # 144 different executable lens functions, each bound to its authentic source.
        lens=idx.search(' '.join(vocabulary),mode='ANY')
        lens_digest=sha(canon({'sphere':sid,'source':corpus.registry_sha,'terms':vocabulary,'matches':lens[:12]}))
        kids=[]
        for chapter,nid in enumerate(sphere['children']):
            node=corpus.nodes[nid]
            original,linear_comparisons=idx.linear_find(nid)
            optimized,indexed_comparisons=idx.indexed_find(nid)
            if original != optimized or original['source_record_sha256']!=node['source_record_sha256']:raise AssertionError('LOOKUP_PARITY')
            ctx={'coordinate':nid,'node':node,'node_digest':node['source_record_sha256'],
                 'sphere':sphere,'house':house,'corpus':corpus,'index':idx,
                 'module_index':si,'chapter_index':chapter,'source_sha':corpus.registry_sha,
                 'mode':'WORK','rights_epoch':None,'input_claims':{}}
            mods=run_modules(ctx)
            bundle={'coordinate':nid,'chapter':chapter+1,'chapter_operator':CHAPTER_OPS[chapter],
                'source_node_name':node['name'],'source_node_record_sha256':node['source_record_sha256'],
                'source_role':node['kind'],'source_edition':'Ariadne v0.7',
                'source_root_sha256':corpus.registry_sha,'sphere':sid,'house':sid[:3],
                'sphere_lens_digest':lens_digest,'implementation_pathway':f'GF9-R1:{sid}',
                'change_id':sha(canon([nid,node['source_record_sha256'],lens_digest,'GF9-R1'])),
                'module_output_digests':{m['house']:m['result_sha256'] for m in mods},
                'module_outputs':mods,
                'acceptance':'LOCAL_PARITY_AND_MODULE_GATES_ONLY',
                'hosted_effect':'NONE','semantic_acceptance':'NOT_PERFORMED',
                'implementation_state':'LOCAL_DERIVED_EXECUTABLE_PROFILE_NOT_HOSTED',
                'private_creative_import':False,'gpt_weights_changed':False}
            bundle['digest_sha256']=sha(canon(bundle))
            metric={'coordinate':nid,'metric_id':f'EXACT_LOOKUP_COMPARISONS:{nid}',
                'baseline_linear_comparisons':linear_comparisons,
                'optimized_indexed_comparisons':indexed_comparisons,
                'strict_improvement':indexed_comparisons<linear_comparisons,
                'exact_parity':True,'module_checks_passed':len(mods),'module_checks_total':len(HOUSE_MODULES),
                'outcome_type':'ALGORITHM_COMPARISON_COUNT_NOT_HOSTED_LATENCY',
                'benchmark_status':'STRUCTURAL_COMPUTATION_VERIFIED'}
            metric['digest_sha256']=sha(canon(metric))
            upgrades.append(bundle);metrics.append(metric);kids.append(bundle['digest_sha256'])
        path={'pathway':f'GF9-R1:{sid}','sphere':sid,'source_name':sphere['name'],
              'house':sid[:3],'role':corpus.nodes[sphere['children'][0]]['kind'],
              'node_coordinates':list(sphere['children']),'node_upgrade_digests':kids,
              'compiled_query_terms':vocabulary,'lens_digest':lens_digest,
              'compiled_search_preview_count':len(lens),'pathway_action':'SOURCE_BOUND_12_CHAPTER_DISPATCH',
              'previous_path_digest':prev,'source_sha256':corpus.registry_sha,
              'publication_status':'NOT_DEPLOYED','semantic_review':'REQUIRED'}
        path['digest_sha256']=sha(canon(path));prev=path['digest_sha256'];pathways.append(path)
        if progress and (si+1)%12==0:progress(si+1)
    for hi in range(1,13):
        hid=f'H{hi:02d}';subset=[p for p in pathways if p['house']==hid]
        if len(subset)!=12:raise AssertionError('HOUSE_12_PATHWAYS')
        report={'module':f'GF9_R1_HOUSE_M{hi:02d}','house':hid,
            'source_house_name':corpus.houses[hid]['name'],'pathway_digests':[p['digest_sha256'] for p in subset],
            'source_edition':'Ariadne v0.7','source_root_sha256':corpus.registry_sha,
            'node_count':144,'sphere_count':12,
            'executable_house_gate':HOUSE_MODULES[hi-1].MODULE,
            'status':'LOCAL_IMPLEMENTATION_CANDIDATE_NOT_HOSTED'}
        report['digest_sha256']=sha(canon(report));house_reports.append(report)
    summary={'schema':SCHEMA,'source_edition':'Ariadne v0.7','source_sha256':corpus.registry_sha,
       'original_source_bytes_verified':corpus.exact_source_verified,
       'historical_topic_sha256':corpus.topic_sha,
       'unreviewed_topic_candidate_edges':sum(len(x) for x in corpus.topic_edges.values()),
       'house_modules':12,'sphere_pathways':len(pathways),'node_upgrades':len(upgrades),
       'module_node_checks':sum(x['module_checks_total'] for x in metrics),
       'distinct_per_node_metrics':len(metrics),
       'strictly_improved_lookup_metrics':sum(x['strict_improvement'] for x in metrics),
       'unchanged_lookup_metrics':sum(not x['strict_improvement'] for x in metrics),
       'baseline_lookup_comparisons':sum(x['baseline_linear_comparisons'] for x in metrics),
       'indexed_lookup_comparisons':sum(x['optimized_indexed_comparisons'] for x in metrics),
       'work_implementation_status':'LOCAL_CODE_PROFILES_AND_VERIFICATION_ONLY',
       'genuinely_measured_civilizational_gains':0,'independent_model_wakes':0,
       'resident_experts_authenticated':0,'host_deployed':False,
       'automatic_semantic_equivalence':False,'rights_at_host_return_verified':False,
       'gpt_parameters_modified':False,'canon_modified':False,
       'private_modes_ingested':False,
       'terminal_sphere_digest':prev,
       'local_compile_elapsed_ms':round((time.perf_counter_ns()-t0)/1e6,3)}
    summary['build_digest_sha256']=sha(canon({k:v for k,v in summary.items() if k not in ('local_compile_elapsed_ms','build_digest_sha256')}))
    out={'summary':summary,'modules':house_reports,'pathways':pathways,'nodes':upgrades,'metrics':metrics}
    verify_build(out,corpus)
    return out


def verify_build(build,corpus):
    s=build['summary'];p=build['pathways'];u=build['nodes'];m=build['metrics'];h=build['modules']
    if (len(h),len(p),len(u),len(m))!=(12,144,1728,1728):raise ValueError('BAD_BUILD_COUNTS')
    if s['source_sha256']!=corpus.registry_sha:raise ValueError('SOURCE_CHANGED')
    if len({x['coordinate'] for x in u})!=1728 or len({x['pathway'] for x in p})!=144:raise ValueError('DUPLICATE_OR_MISSING')
    for record,kind in [*[(v,'node') for v in u],*[(v,'metric') for v in m],*[(v,'pathway') for v in p],*[(v,'module') for v in h]]:
        digest=record.get('digest_sha256')
        if digest!=sha(canon({k:v for k,v in record.items() if k!='digest_sha256'})):raise ValueError('TAMPERED_'+kind.upper())
    for v in u:
        node=corpus.safe_node(v['coordinate'])
        if node['source_record_sha256']!=v['source_node_record_sha256'] or len(v['module_outputs'])!=12:raise ValueError('NODE_PIN_OR_GATE_MISSING')
        if any(mod['result_sha256']!=sha(canon(mod['result'])) for mod in v['module_outputs']):raise ValueError('MODULE_OUTPUT_TAMPER')
    return True


def benchmark_lookup(corpus,passes=31):
    if not 5<=passes<=101:raise ValueError('BENCH_BOUNDS')
    idx=SourceIndex(corpus);keys=idx.ids
    for nid in keys:
        a,_=idx.linear_find(nid);b,_=idx.indexed_find(nid)
        if a!=b:raise AssertionError('BEFORE_AFTER_PARITY')
    def linear():return [idx.linear_find(nid)[0]['source_record_sha256'] for nid in keys]
    def fast():return [idx.indexed_find(nid)[0]['source_record_sha256'] for nid in keys]
    expected=fast()
    if linear()!=expected:raise AssertionError('LOOKUP_BASELINE_NOT_EQUAL')
    for _ in range(3):linear();fast()
    timings={'linear':[],'indexed':[]}
    for i in range(passes):
        for op in (('linear','indexed') if i%2==0 else ('indexed','linear')):
            t=time.perf_counter_ns();v=linear() if op=='linear' else fast()
            if v!=expected:raise AssertionError('BENCH_PARITY_FAILURE')
            timings[op].append((time.perf_counter_ns()-t)/1e6)
    l=statistics.median(timings['linear']);f=statistics.median(timings['indexed'])
    def q95(v):return sorted(v)[int((len(v)-1)*.95)]
    return {'schema':'atlas.1728.lookup-paired-benchmark/v1','passes':passes,'query_count_per_pass':len(keys),
           'linear_median_ms':round(l,6),'indexed_median_ms':round(f,6),
           'linear_p95_ms':round(q95(timings['linear']),6),'indexed_p95_ms':round(q95(timings['indexed']),6),
           'median_speedup':round(l/f,3),'exact_source_result_parity':True,
           'denominator':'1728_SOURCE_IDENTITY_LOOKUPS_NOT_GPT_OR_HOST_END_TO_END',
           'index_build_excluded':True,'host_deployed':False,
           'timings_are_local_and_non_deterministic':True}


def persist_sqlite(build,path):
    dest=Path(path);dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():dest.unlink()
    db=sqlite3.connect(dest)
    try:
        db.executescript('''PRAGMA journal_mode=DELETE;PRAGMA foreign_keys=ON;
CREATE TABLE nodes (coordinate TEXT PRIMARY KEY, sphere TEXT NOT NULL, house TEXT NOT NULL, name TEXT NOT NULL, kind TEXT NOT NULL, receipt TEXT NOT NULL, payload_json TEXT NOT NULL);
CREATE TABLE metrics (coordinate TEXT PRIMARY KEY, baseline INTEGER, optimized INTEGER, parity INTEGER, receipt TEXT NOT NULL);
CREATE TABLE pathways (sphere TEXT PRIMARY KEY, receipt TEXT NOT NULL, payload_json TEXT NOT NULL);
CREATE TABLE house_modules (house TEXT PRIMARY KEY, receipt TEXT NOT NULL, payload_json TEXT NOT NULL);
CREATE TABLE ledger (seq INTEGER PRIMARY KEY, coordinate TEXT NOT NULL UNIQUE, previous_sha TEXT NOT NULL, receipt_sha TEXT NOT NULL);
CREATE INDEX idx_nodes_sphere ON nodes(sphere);CREATE INDEX idx_nodes_house ON nodes(house);''')
        for n in build['nodes']:
            db.execute('INSERT INTO nodes VALUES(?,?,?,?,?,?,?)',(n['coordinate'],n['sphere'],n['house'],n['source_node_name'],n['source_role'],n['digest_sha256'],canon(n).decode('ascii')))
        for m in build['metrics']:
            db.execute('INSERT INTO metrics VALUES(?,?,?,?,?)',(m['coordinate'],m['baseline_linear_comparisons'],m['optimized_indexed_comparisons'],int(m['exact_parity']),m['digest_sha256']))
        for p in build['pathways']:db.execute('INSERT INTO pathways VALUES(?,?,?)',(p['sphere'],p['digest_sha256'],canon(p).decode('ascii')))
        for h in build['modules']:db.execute('INSERT INTO house_modules VALUES(?,?,?)',(h['house'],h['digest_sha256'],canon(h).decode('ascii')))
        prev='0'*64
        for i,n in enumerate(build['nodes'],1):
            receipt=sha(canon({'seq':i,'previous':prev,'coordinate':n['coordinate'],'node_receipt':n['digest_sha256']}))
            db.execute('INSERT INTO ledger VALUES(?,?,?,?)',(i,n['coordinate'],prev,receipt));prev=receipt
        db.commit()
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('SQLITE_INTEGRITY')
        return {'database':str(dest),'ledger_tip':prev,'nodes':db.execute('SELECT COUNT(*) FROM nodes').fetchone()[0],
                'metrics':db.execute('SELECT COUNT(*) FROM metrics').fetchone()[0],
                'pathways':db.execute('SELECT COUNT(*) FROM pathways').fetchone()[0],
                'house_modules':db.execute('SELECT COUNT(*) FROM house_modules').fetchone()[0]}
    finally:db.close()
