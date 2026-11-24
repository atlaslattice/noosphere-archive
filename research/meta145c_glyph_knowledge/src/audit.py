"""Independent readback of META145C structural, source and memory receipts."""
from pathlib import Path
import gzip,csv,json,sqlite3
from .core import SourceSnapshot
from .glyph import typed_route,decode_axg1,positional_gf7
from .memory import canonical,sha,LocalMemory

def audit(root,ariadne,openalex):
    root=Path(root);s=SourceSnapshot(ariadne,openalex)
    meta=json.loads((root/'META145_GLYPH_SYNTHESIS.json').read_text())
    spheres=json.loads((root/'sphere144_reviews.json').read_text())
    houses=json.loads((root/'house12_followups.json').read_text())
    if len(spheres)!=144 or len(houses)!=12 or meta['perspectives']!=144:raise ValueError('SPHERE_COUNT')
    prev='0'*64;tokens=set();all_nodes=[];comp=0
    for sp in spheres:
        if sp['sphere'] not in s.spheres or sp['name']!=s.spheres[sp['sphere']]['name'] or sp['house']!=sp['sphere'][:3] or len(sp['source_node_ids'])!=12:raise ValueError('SPHERE_SOURCE_MISMATCH')
        if sp['source_node_record_digests']!=[s.nodes[n]['source_record_sha256'] for n in sp['source_node_ids']]:raise ValueError('NODE_RECORD_DIGEST_MISMATCH')
        if sp['cumulative_prior_hash']!=prev:raise ValueError('SPHERE_CHAIN_PREVIOUS_MISMATCH')
        if not sp['unique_perspective'].startswith('Compare each Ariadne address'):raise ValueError('SPHERE_PERSPECTIVE_MISSING')
        key=tuple(sp['query_terms'])
        if key in tokens:raise ValueError('DUPLICATE_SPHERE_COMPUTATION_LENS')
        tokens.add(key)
        stamp=sp['receipt_sha256'];body={k:v for k,v in sp.items() if k!='receipt_sha256'}
        if stamp!=sha(canonical(body)):raise ValueError('SPHERE_HASH_FAIL')
        prev=stamp;comp+=sp['total_comparisons'];all_nodes.extend(sp['source_node_ids'])
    if comp!=248832 or sorted(all_nodes)!=list(s.node_ids) or meta['source_circuit_terminal_receipt']!=prev:raise ValueError('CIRCUIT_INTEGRITY')
    for h in houses:
        if len(h['source_spheres'])!=12 or len(h['source_nodes'])!=144 or h['house'] not in s.houses:raise ValueError('HOUSE_INTEGRITY')
        stamp=h['receipt_sha256'];body={k:v for k,v in h.items() if k!='receipt_sha256'}
        if stamp!=sha(canonical(body)):raise ValueError('HOUSE_HASH_FAIL')
    with gzip.open(root/'sphere_node_pair_matrix_248832.csv.gz','rt') as f:
        reader=csv.DictReader(f)
        expected=iter((sid,nid) for sid in s.sphere_ids for nid in s.node_ids)
        n=0
        for row in reader:
            if (row['sphere'],row['node'])!=next(expected):raise ValueError('PAIR_ORDER_SOURCE_FAIL')
            if row['candidate_authority']!='NONE':raise ValueError('INVENTED_AUTHORITY')
            n+=1
    if n!=248832:raise ValueError('PAIR_TOTAL_FAIL')
    db=sqlite3.connect(root/'atlas_meta145_knowledge.sqlite')
    if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('DB_INTEGRITY')
    counts={t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ['nodes','spheres','houses','topics','topic_candidates']}
    if counts!={'nodes':1728,'spheres':144,'houses':12,'topics':4516,'topic_candidates':22580}:raise ValueError('DB_CARDINALITY')
    for addr,token,gf in db.execute('SELECT hsn,axg1,gf7 FROM nodes ORDER BY hsn'):
        if decode_axg1(token,s.registry_sha)!=addr or positional_gf7(addr)!=gf:raise ValueError('GLYPH_ROUTING_FAIL')
    db.close()
    expected_sha=meta['meta_receipt_sha256'];body={k:v for k,v in meta.items() if k!='meta_receipt_sha256'}
    if sha(canonical(body))!=expected_sha:raise ValueError('META_HASH_FAIL')
    return {'status':'AUDITED_SOURCE_MATCH','spheres':144,'unique_computational_query_lenses':len(tokens),
        'house_followups':12,'independent_pair_rows':n,'glyph_roundtrips':1728,
        'topic_candidates':22580,'meta_receipt':expected_sha,
        'original_registry_sha256':s.registry_sha,'historical_openalex_sha256':s.topics_sha,
        'not_human_approved':True,'host_authority':'NONE','actual_model_wakes':0}
