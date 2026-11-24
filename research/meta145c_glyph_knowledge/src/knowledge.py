"""Review-only, source-typed knowledge projections over the META145 local DB.

Functional memory affects *triage presentation*, never factual authority, weights
of an AI model, source records or an accepted semantic graph.
"""
from __future__ import annotations
import sqlite3
from .glyph import hsn_parts,typed_route
from .memory import LocalMemory


def topic_view(db:sqlite3.Connection,hsn:str,memory:LocalMemory|None=None,limit:int=50,offset:int=0,*,memory_checkpoint:dict|None=None)->dict:
    """Build a page from one independently anchored memory snapshot.

    memory_checkpoint must be retained outside the mutable memory ledger and
    contain expected_tip/expected_count; never self-anchor an existing history.
    """
    hsn_parts(hsn)
    if type(limit)!=int or type(offset)!=int or not 1<=limit<=500 or offset<0:raise ValueError('BAD_LIMIT')
    deltas={}
    if memory is not None:
        if memory_checkpoint is None:raise ValueError('CHECKPOINT_REQUIRED')
        if type(memory_checkpoint) is not dict or set(memory_checkpoint)!={'expected_tip','expected_count'}:raise ValueError('CHECKPOINT_INVALID')
        deltas=memory.verified_triage_batch([hsn],**memory_checkpoint)[hsn]
    elif memory_checkpoint is not None:raise ValueError('MEMORY_REQUIRED_FOR_CHECKPOINT')
    original=db.execute('SELECT c.topic_id,t.label,c.rank,t.original_status FROM topic_candidates c JOIN topics t ON c.topic_id=t.id WHERE c.hsn=?',(hsn,)).fetchall()
    items=[]
    for tid,label,rank,status in original:
        delta=deltas.get(tid,0)
        items.append({'topic_id':tid,'label':label,'historical_rank':rank,'raw_source_status':status,
           'triage_delta':delta,'triage_priority':100-rank*10+max(-4,min(4,delta))*20,
           'relation':'HISTORICAL_HEURISTIC_CANDIDATE_UNREVIEWED','authority':'NONE'})
    items.sort(key=lambda x:(-x['triage_priority'],x['topic_id']))
    return {'coordinate':hsn,'total':len(items),'shown':len(items[offset:offset+limit]),
        'omitted':max(0,len(items)-offset-limit),'primary_count':sum(v['historical_rank']==1 for v in items),
        'alternate_count':sum(v['historical_rank']>1 for v in items),'items':items[offset:offset+limit],
        'triage_memory_used':memory is not None,
        'memory_integrity':'CALLER_CHECKPOINT_MATCHED_LOCAL_SNAPSHOT' if memory is not None else 'NO_MEMORY_USED',
        'semantic_equivalence_approved':False,'hosted_verified':False,
        'privacy':'WORK_SYNTHETIC_LOCAL_ONLY','canon_effect':'NONE'}


def shared_topic_neighbors(db:sqlite3.Connection,hsn:str,limit:int=24)->dict:
    hsn_parts(hsn)
    if type(limit)!=int or not 1<=limit<=100:raise ValueError('BAD_LIMIT')
    rows=db.execute('SELECT a.topic_id,b.hsn FROM topic_candidates a JOIN topic_candidates b ON a.topic_id=b.topic_id WHERE a.hsn=? AND b.hsn<>a.hsn ORDER BY a.topic_id,b.hsn',(hsn,)).fetchall()
    return {'root':hsn,'total_candidate_paths':len(rows),'paths':[{'topic_id':t,'other_hsn':n,'kind':'SHARED_UNREVIEWED_TOPIC_CANDIDATE_NOT_SEMANTIC_SAME_AS'} for t,n in rows[:limit]],
         'relationship':'BROWSE_ONLY','subject_equivalence':False,'shared_source_truth':False,'canon_effect':'NONE'}


def source_card(db:sqlite3.Connection,hsn:str,registry_sha:str)->dict:
    hsn_parts(hsn)
    row=db.execute('SELECT n.hsn,n.name,n.role,n.record_digest,s.name,h.name FROM nodes n JOIN spheres s ON n.sphere=s.hsn JOIN houses h ON s.house=h.hsn WHERE n.hsn=?',(hsn,)).fetchone()
    if not row:raise ValueError('UNAVAILABLE_HSN')
    d={'hsn':row[0],'name':row[1],'role':row[2],'record_digest':row[3],
       'sphere':row[4],'house':row[5], 'edition_sha256':registry_sha,
       'acceptance':'SOURCE_READBACK_METADATA_ONLY','research':'CANDIDATE_NOT_VERIFIED','authorityEffect':'NONE'}
    d['display']=typed_route(hsn,registry_sha)
    return d
