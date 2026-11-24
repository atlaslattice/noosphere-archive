"""Private-source exact Ariadne v0.7 binder, returning review-only chapter modules."""
import hashlib,json,re
from pathlib import Path
from .protocol import ANCHOR,CHAPTER_LABELS,CHAPTER_OPS

RE_SPHERE=re.compile(r'^H(0[1-9]|1[0-2])\.S(0[1-9]|1[0-2])$')

def bind_registry(file:Path):
    raw=file.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ANCHOR:raise ValueError('ARIADNE_EXACT_BYTES_MISMATCH')
    source=json.loads(raw)
    if not (len(source['houses'])==12 and len(source['spheres'])==144 and len(source['nodes'])==1728):raise ValueError('ARIADNE_CARDINALITY')
    outputs=[]
    for i,(id,item) in enumerate(sorted(source['spheres'].items())):
        if not RE_SPHERE.fullmatch(id) or item['id']!=id:raise ValueError('SPHERE_ID')
        if item['parent']!=id[:3] or len(item['children'])!=12:raise ValueError('PARENT_OR_CHILDREN')
        children=[source['nodes'][c] for c in item['children']]
        kinds=set(ch['kind'] for ch in children)
        if len(kinds)!=1:raise ValueError('MIXED_SPHERE_KIND')
        outputs.append({'id':id,'name':item['name'],'house':source['houses'][id[:3]]['name'],
         'role':next(iter(kinds)),'node_ids':item['children'],
         'node_names':[c['name'] for c in children],
         'node_source_digests':[c['source_record_sha256'] for c in children],
         'source_edition':'Ariadne v0.7','source_sha256':ANCHOR,
         'work_rights':'CANDIDATE_WORK_REVIEW_ONLY',
         'chapters':[{'chapter':j+1,'title':title,'operator':CHAPTER_OPS[j],
            'target_node':item['children'][j],
            'acceptance':'SOFTWARE_SCHEMA_AND_MATH_NEGATIVE_CONTROL_PASS_NOT_SEMANTIC_MATCH',
            'status':'SIMULATION_TARGET_NOT_REAL_PEER_DIALOGUE'} for j,title in enumerate(CHAPTER_LABELS)]})
    assert len(outputs)==144
    assert len([m for m in outputs if m['role']=='DOMAIN_SPECIALIZATION'])==84
    return outputs
