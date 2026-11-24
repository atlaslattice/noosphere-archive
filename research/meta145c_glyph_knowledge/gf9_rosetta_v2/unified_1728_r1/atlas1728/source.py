"""Exact-edition Ariadne source loader. All untrusted input is nonauthoritative."""
from __future__ import annotations
import csv, hashlib, io, json, re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

ARIADNE_SHA = '07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6'
OPENALEX_SHA = 'a306c7306a79754b033e9f8c41c0de5ff5176b4544a6a80b5c740e2f8d2cc903'
HSN = re.compile(r'^H(0[1-9]|1[0-2])\.S(0[1-9]|1[0-2])\.N(0[1-9]|1[0-2])$')
SPHERE = re.compile(r'^H(0[1-9]|1[0-2])\.S(0[1-9]|1[0-2])$')
DOMAIN = 'DOMAIN_SPECIALIZATION'
METHOD = 'EPISTEMIC_META'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canon(obj) -> bytes:
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')


def check_registry(data: dict) -> dict:
    if type(data) is not dict or set(data) != {'houses','spheres','nodes','catalog'}:
        raise ValueError('REGISTRY_SCHEMA')
    houses,spheres,nodes=(data[k] for k in ('houses','spheres','nodes'))
    if (len(houses),len(spheres),len(nodes)) != (12,144,1728):raise ValueError('CARDINALITY')
    kinds={DOMAIN:0,METHOD:0};sphere_kinds={DOMAIN:0,METHOD:0}
    for i in range(1,13):
        h=f'H{i:02d}';a=houses.get(h)
        if not isinstance(a,dict) or a.get('id')!=h or len(a.get('children',[]))!=12 or not isinstance(a.get('name'),str):raise ValueError('HOUSE')
        for s in range(1,13):
            sp=f'{h}.S{s:02d}';b=spheres.get(sp)
            if not isinstance(b,dict) or b.get('id')!=sp or b.get('parent')!=h or len(b.get('children',[]))!=12 or sp not in a['children']:raise ValueError('SPHERE')
            sphere_roles=set()
            for n in range(1,13):
                nid=f'{sp}.N{n:02d}';c=nodes.get(nid)
                if not isinstance(c,dict) or c.get('id')!=nid or c.get('parent')!=sp or nid not in b['children'] or not HSN.fullmatch(nid) or c.get('kind') not in kinds:raise ValueError('NODE')
                if not all(isinstance(c.get(k),str) and c[k] for k in ('name','definition','includes','excludes')) or not re.fullmatch('[a-f0-9]{64}',c.get('source_record_sha256','')):raise ValueError('NODE_SOURCE')
                kinds[c['kind']]+=1;sphere_roles.add(c['kind'])
            if len(sphere_roles)!=1:raise ValueError('SPHERE_MIXED_ROLE')
            sphere_kinds[next(iter(sphere_roles))]+=1
    if kinds!={DOMAIN:1008,METHOD:720} or sphere_kinds!={DOMAIN:84,METHOD:60}:raise ValueError('ORIGINAL_ROLE_DISTRIBUTION')
    return {'houses':12,'spheres':144,'nodes':1728,'roles':kinds,'sphere_roles':sphere_kinds}


@dataclass
class Corpus:
    houses: dict
    spheres: dict
    nodes: dict
    registry_sha: str
    topic_edges: dict
    topics: dict
    topic_sha: str|None
    exact_source_verified: bool

    @classmethod
    def original(cls,ariadne: str|Path,topic_csv: str|Path|None=None):
        raw=Path(ariadne).read_bytes()
        if sha(raw)!=ARIADNE_SHA:raise ValueError('ORIGINAL_ARIADNE_BYTES_MISMATCH')
        data=json.loads(raw);check_registry(data)
        edges={k:[] for k in data['nodes']}; topics={};topic_sha=None
        if topic_csv is not None:
            raw_t=Path(topic_csv).read_bytes()
            if sha(raw_t)!=OPENALEX_SHA:raise ValueError('ORIGINAL_OPENALEX_BYTES_MISMATCH')
            topic_sha=sha(raw_t)
            rows=list(csv.DictReader(io.StringIO(raw_t.decode('utf-8-sig'))))
            if len(rows)!=4516:raise ValueError('TOPIC_CARDINALITY')
            for row in rows:
                tid=row['T_ID']; primary=row['Candidate_HSN'];others=row['Other_4_HSN_candidates'].split(';')
                if not re.fullmatch(r'T\d{1,8}',tid) or tid in topics or len(others)!=4 or len(set([primary,*others]))!=5 or any(n not in edges for n in [primary,*others]):raise ValueError('TOPIC_FORMAT')
                topics[tid]={'id':tid,'label':row['OpenAlex_topic_name_source'],'source_status':row['Status'],'accepted':False}
                for rank,nid in enumerate([primary,*others],1):
                    edges[nid].append({'topic_id':tid,'rank':rank,'role':'PRIMARY' if rank==1 else 'ALTERNATE','status':'UNREVIEWED_HEURISTIC_NOT_SEMANTIC_EQUIVALENCE'})
            if sum(len(x) for x in edges.values())!=22580:raise ValueError('TOPIC_EDGE_CARDINALITY')
        return cls(data['houses'],data['spheres'],data['nodes'],sha(raw),edges,topics,topic_sha,True)

    @classmethod
    def synthetic(cls):
        """Synthetic exact-shaped source for tests. Never masquerades as original."""
        houses={};spheres={};nodes={}
        for h in range(1,13):
            hk=f'H{h:02d}'; houses[hk]={'id':hk,'name':f'Synthetic house {h}','children':[f'{hk}.S{s:02d}' for s in range(1,13)]}
            for s in range(1,13):
                sid=f'{hk}.S{s:02d}'; role=DOMAIN if s<=7 else METHOD
                spheres[sid]={'id':sid,'name':f'Synthetic sphere H{h:02d} S{s:02d}','parent':hk,'children':[f'{sid}.N{n:02d}' for n in range(1,13)]}
                for n in range(1,13):
                    nid=f'{sid}.N{n:02d}'
                    nodes[nid]={'id':nid,'name':f'Synthetic coordinate {nid}', 'parent':sid,'kind':role,'source_record_sha256':sha(nid.encode()),'definition':'Artificial test subject only','includes':'Synthetic reviewed test field','excludes':'Human-accepted scientific or cultural equivalence'}
        check_registry({'houses':houses,'spheres':spheres,'nodes':nodes,'catalog':{}})
        return cls(houses,spheres,nodes,'0'*64,{k:[] for k in nodes},{},None,False)

    def safe_node(self,coordinate:str):
        if not isinstance(coordinate,str) or not HSN.fullmatch(coordinate):raise ValueError('INVALID_COORDINATE')
        try:return self.nodes[coordinate]
        except KeyError:raise ValueError('UNKNOWN_COORDINATE') from None
