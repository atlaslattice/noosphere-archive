"""Local Work memory with serialized writes and independent-checkpoint reads.

A self-hash is not a signature, current host right or rollback anchor. Retain
expected tip/count outside this mutable ledger to detect rollback or rewrites.
"""
from __future__ import annotations
import json, hashlib, re, sqlite3
from typing import Mapping
from .glyph import hsn_parts

SCHEMA='atlas.meta145.local-functional-memory/v1'
ACTIONS={'NOTE','CHALLENGE','RETRACT'}
FIELDS=('event_id','mode','coordinate','topic_id','action','source_ref','source_digest','retract_event_id')
ALLOWED=set(FIELDS)|{'scope'}
ZERO='0'*64

def canonical(x)->str:return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def sha(x)->str:return hashlib.sha256(x.encode('utf-8') if isinstance(x,str) else x).hexdigest()

class _IntegrityError(ValueError):
    def __init__(self,reason,seq):super().__init__(reason);self.seq=seq

def _payload_valid(p):
    if p['mode']!='WORK':raise ValueError('PRIVATE_OR_HOST_MODE_DENIED')
    hsn_parts(p['coordinate'])
    if not isinstance(p['action'],str) or p['action'] not in ACTIONS:raise ValueError('EVENT_ACTION_INVALID')
    if not isinstance(p['event_id'],str) or not re.fullmatch(r'[a-z][a-z0-9._:-]{4,90}',p['event_id']):raise ValueError('EVENT_ID_INVALID')
    ref=p['source_ref']
    if not isinstance(ref,str) or len(ref)>350 or not ref.startswith(('urn:atlas:synthetic:','https://')):raise ValueError('SOURCE_REF_INVALID')
    digest=p['source_digest']
    if not isinstance(digest,str) or not re.fullmatch(r'[a-f0-9]{64}',digest):raise ValueError('SOURCE_DIGEST_INVALID')
    topic=p['topic_id']
    if topic is not None and (not isinstance(topic,str) or not re.fullmatch(r'T[1-9][0-9]*',topic)):raise ValueError('TOPIC_ID_INVALID')
    if p['action']!='RETRACT' and p['retract_event_id'] is not None:raise ValueError('RETRACT_ID_WITHOUT_RETRACTION')
    if p['action']=='RETRACT' and not isinstance(p['retract_event_id'],str):raise ValueError('INVALID_RETRACTION')

def _checkpoint_valid(tip,count):
    if not isinstance(tip,str) or not re.fullmatch(r'[a-f0-9]{64}',tip) or type(count) is not int or count<0:raise ValueError('CHECKPOINT_INVALID')

def _relation_valid(p,seen,retracted):
    if p['event_id'] in seen:raise ValueError('DUPLICATE_EVENT')
    if p['action']=='RETRACT':
        target=p['retract_event_id'];original=seen.get(target)
        if (original is None or original['action']=='RETRACT'
                or original['coordinate']!=p['coordinate'] or original['topic_id']!=p['topic_id']):raise ValueError('INVALID_RETRACTION')
        if target in retracted:raise ValueError('ALREADY_RETRACTED')
        retracted.add(target)
    seen[p['event_id']]=p

def _verified_rows(rows):
    """Validate the exact materialized snapshot subsequently consumed."""
    prev=ZERO;previous_seq=0;seen={};retracted=set()
    for row in rows:
        try:
            p={k:row[k] for k in FIELDS}
            if row['prev_hash']!=prev or sha(prev+'|'+canonical(p))!=row['event_hash']:raise ValueError('FAIL_CHAIN')
            if type(row['seq']) is not int or row['seq']<=previous_seq:raise ValueError('EVENT_SEQUENCE_INVALID')
            _payload_valid(p);_relation_valid(p,seen,retracted)
        except (ValueError,TypeError,KeyError,OverflowError) as error:
            raise _IntegrityError(str(error),row.get('seq')) from error
        prev=row['event_hash'];previous_seq=row['seq']
    return prev,seen,retracted

def _aggregate(rows,coordinates,retracted):
    result={coordinate:{} for coordinate in coordinates}
    for row in rows:
        if row['coordinate'] in result and row['event_id'] not in retracted and row['action'] in ('NOTE','CHALLENGE'):
            topics=result[row['coordinate']];topic=row['topic_id']
            topics[topic]=topics.get(topic,0)+(1 if row['action']=='NOTE' else -1)
    return result

class LocalMemory:
    def __init__(self,path):
        self.db=sqlite3.connect(path)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('CREATE TABLE IF NOT EXISTS review_events(seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE, mode TEXT NOT NULL, coordinate TEXT NOT NULL, topic_id TEXT, action TEXT NOT NULL, source_ref TEXT NOT NULL, source_digest TEXT NOT NULL, retract_event_id TEXT, prev_hash TEXT NOT NULL, event_hash TEXT NOT NULL)')
        self.db.commit()
    def close(self):self.db.close()
    def events(self):
        """Raw local inspection only; consumers must verify before using rows."""
        return [dict(zip(('seq',)+FIELDS+('prev_hash','event_hash'),r)) for r in self.db.execute('SELECT seq,event_id,mode,coordinate,topic_id,action,source_ref,source_digest,retract_event_id,prev_hash,event_hash FROM review_events ORDER BY seq')]
    def append(self,event:Mapping,*,expected_tip=None,expected_count=None)->dict:
        """Serialize verification and append; optionally match a trusted anchor.

        Unanchored append detects corruption but not a valid-prefix rollback.
        Pass an externally retained tip/count to reject that rollback as well.
        """
        if (type(event) is not dict or set(event)-ALLOWED
                or any(k not in event for k in ('event_id','mode','scope','coordinate','action','source_ref','source_digest'))):raise ValueError('EVENT_SCHEMA_INVALID')
        if event['scope']!='SYNTHETIC_LOCAL_REVIEW':raise ValueError('PRIVATE_OR_HOST_MODE_DENIED')
        payload={k:event.get(k) for k in FIELDS}
        _payload_valid(payload)
        anchored=expected_tip is not None or expected_count is not None
        if anchored:_checkpoint_valid(expected_tip,expected_count)
        if self.db.in_transaction:raise ValueError('TRANSACTION_ALREADY_ACTIVE')
        # Reserve the write lock before reading the tip across connections.
        self.db.execute('BEGIN IMMEDIATE')
        try:
            rows=self.events()
            prev,seen,retracted=_verified_rows(rows)
            if anchored and (len(rows)!=expected_count or prev!=expected_tip):raise ValueError('CHECKPOINT_CHANGED')
            _relation_valid(payload,seen,retracted)
            stamp=sha(prev+'|'+canonical(payload))
            self.db.execute('INSERT INTO review_events(event_id,mode,coordinate,topic_id,action,source_ref,source_digest,retract_event_id,prev_hash,event_hash) VALUES(?,?,?,?,?,?,?,?,?,?)',
                            tuple(payload[k] for k in FIELDS)+(prev,stamp))
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        return {'schema':SCHEMA,'status':'LOCAL_REVIEW_EVENT_RECORDED_UNVERIFIED','event_hash':stamp,'count':len(rows)+1,
                'host_verified':False,'model_weights_updated':False,'knowledge_truth_upgraded':False,'canon_effect':'NONE'}
    def verify(self)->dict:
        rows=self.events()
        try:tip,_,_=_verified_rows(rows)
        except _IntegrityError as error:return {'status':str(error),'seq':error.seq}
        return {'status':'LOCAL_HASH_CHAIN_VERIFIED','count':len(rows),'tip':tip,'external_signer':'NONE','freshness':'UNANCHORED_LOCAL_CHAIN_ONLY'}
    def triage_delta(self,coordinate:str,topic_id:str|None=None)->int:
        """Legacy local convenience: integrity checked, without a rollback anchor.

        Research consumers use verified_triage_batch with a trusted checkpoint.
        This remains for local-only backwards compatibility.
        """
        hsn_parts(coordinate)
        rows=self.events()
        _,_,retracted=_verified_rows(rows)
        return _aggregate(rows,[coordinate],retracted)[coordinate].get(topic_id,0)

    def verified_triage_batch(self,coordinates,*,expected_tip,expected_count):
        """Aggregate one snapshot matched to an independently trusted tip/count.

        Keep the checkpoint outside the mutable ledger. Matching is local
        integrity evidence only. Actual host READ/RETURN checks remain the
        publisher's responsibility and cannot be cached with this result.
        """
        _checkpoint_valid(expected_tip,expected_count)
        if not isinstance(coordinates,(tuple,list)) or not 1<=len(coordinates)<=1728:raise ValueError('BATCH_SCOPE_INVALID')
        coordinates=tuple(coordinates)
        for coordinate in coordinates:hsn_parts(coordinate)
        if len(set(coordinates))!=len(coordinates):raise ValueError('DUPLICATE_COORDINATE')
        rows=self.events()
        tip,_,retracted=_verified_rows(rows)
        if len(rows)!=expected_count or tip!=expected_tip:raise ValueError('CHECKPOINT_CHANGED')
        return _aggregate(rows,coordinates,retracted)
