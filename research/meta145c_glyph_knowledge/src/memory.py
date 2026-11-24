"""Append-only local review-event memory. Never a host rights or canon issuer.

A typed synthetic Work review can change *triage ordering*, but cannot upgrade
scientific authority, verified knowledge or trained model weights.
"""
from __future__ import annotations
import json,hashlib,re,sqlite3
from typing import Mapping
from .glyph import hsn_parts

SCHEMA='atlas.meta145.local-functional-memory/v1'
ACTIONS={'NOTE','CHALLENGE','RETRACT'}
ALLOWED={'event_id','mode','scope','coordinate','topic_id','action','source_ref','source_digest','retract_event_id'}


def canonical(x)->str:return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def sha(x)->str:return hashlib.sha256(x.encode('utf-8') if isinstance(x,str) else x).hexdigest()

class LocalMemory:
    def __init__(self,path):
        self.db=sqlite3.connect(path)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('CREATE TABLE IF NOT EXISTS review_events(seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE, mode TEXT NOT NULL, coordinate TEXT NOT NULL, topic_id TEXT, action TEXT NOT NULL, source_ref TEXT NOT NULL, source_digest TEXT NOT NULL, retract_event_id TEXT, prev_hash TEXT NOT NULL, event_hash TEXT NOT NULL)')
        self.db.commit()
    def close(self):self.db.close()
    def events(self):
        return [dict(zip(('seq','event_id','mode','coordinate','topic_id','action','source_ref','source_digest','retract_event_id','prev_hash','event_hash'),r)) for r in self.db.execute('SELECT seq,event_id,mode,coordinate,topic_id,action,source_ref,source_digest,retract_event_id,prev_hash,event_hash FROM review_events ORDER BY seq')]
    def append(self,event:Mapping)->dict:
        """Local (not authenticated) SYNTHETIC_WORK ONLY; never grants permissions."""
        if type(event)!=dict or set(event)-ALLOWED or any(k not in event for k in ('event_id','mode','scope','coordinate','action','source_ref','source_digest')):raise ValueError('EVENT_SCHEMA_INVALID')
        if event['mode']!='WORK' or event['scope']!='SYNTHETIC_LOCAL_REVIEW':raise ValueError('PRIVATE_OR_HOST_MODE_DENIED')
        hsn_parts(event['coordinate'])
        if event['action'] not in ACTIONS:raise ValueError('EVENT_ACTION_INVALID')
        if not re.fullmatch(r'[a-z][a-z0-9._:-]{4,90}',str(event['event_id'])):raise ValueError('EVENT_ID_INVALID')
        if not isinstance(event['source_ref'],str) or not (event['source_ref'].startswith('urn:atlas:synthetic:') or event['source_ref'].startswith('https://')) or len(event['source_ref'])>350:raise ValueError('SOURCE_REF_INVALID')
        if not re.fullmatch(r'[a-f0-9]{64}',str(event['source_digest'])):raise ValueError('SOURCE_DIGEST_INVALID')
        topic=event.get('topic_id')
        if topic is not None and not re.fullmatch(r'T[1-9][0-9]*',topic):raise ValueError('TOPIC_ID_INVALID')
        prior=self.events()
        if any(row['event_id']==event['event_id'] for row in prior):raise ValueError('DUPLICATE_EVENT')
        target=event.get('retract_event_id')
        if event['action']=='RETRACT':
            if not isinstance(target,str) or not any(r['event_id']==target and r['action']!='RETRACT' and r['coordinate']==event['coordinate'] and r['topic_id']==topic for r in prior):raise ValueError('INVALID_RETRACTION')
            if any(r['action']=='RETRACT' and r['retract_event_id']==target for r in prior):raise ValueError('ALREADY_RETRACTED')
        elif target is not None:raise ValueError('RETRACT_ID_WITHOUT_RETRACTION')
        prev=prior[-1]['event_hash'] if prior else '0'*64
        payload={k:event.get(k) for k in ('event_id','mode','coordinate','topic_id','action','source_ref','source_digest','retract_event_id')}
        stamp=sha(prev+'|'+canonical(payload))
        self.db.execute('INSERT INTO review_events(event_id,mode,coordinate,topic_id,action,source_ref,source_digest,retract_event_id,prev_hash,event_hash) VALUES(?,?,?,?,?,?,?,?,?,?)',
                        (payload['event_id'],payload['mode'],payload['coordinate'],topic,payload['action'],payload['source_ref'],payload['source_digest'],target,prev,stamp))
        self.db.commit()
        return {'schema':SCHEMA,'status':'LOCAL_REVIEW_EVENT_RECORDED_UNVERIFIED','event_hash':stamp,
                'host_verified':False,'model_weights_updated':False,'knowledge_truth_upgraded':False,'canon_effect':'NONE'}
    def verify(self)->dict:
        prev='0'*64
        rows=self.events()
        for row in rows:
            payload={k:row[k] for k in ('event_id','mode','coordinate','topic_id','action','source_ref','source_digest','retract_event_id')}
            if row['prev_hash']!=prev or sha(prev+'|'+canonical(payload))!=row['event_hash']:
                return {'status':'FAIL_CHAIN','seq':row['seq']}
            prev=row['event_hash']
        return {'status':'LOCAL_HASH_CHAIN_VERIFIED','count':len(rows),'tip':prev,'external_signer':'NONE'}
    def triage_delta(self,coordinate:str,topic_id:str|None=None)->int:
        hsn_parts(coordinate)
        rows=self.events()
        retracted={r['retract_event_id'] for r in rows if r['action']=='RETRACT'}
        return sum((1 if r['action']=='NOTE' else -1) for r in rows if r['coordinate']==coordinate and r['topic_id']==topic_id and r['action'] in ('NOTE','CHALLENGE') and r['event_id'] not in retracted)

    def verified_triage_batch(self, coordinates, *, expected_tip, expected_count):
        """Return coordinate/topic deltas from one verified snapshot; local only.

        The caller must obtain the expected tip/count from an independent trusted
        checkpoint. This verifies local integrity, not host consent or authority.
        A fresh rights check at RETURN remains the host publisher's responsibility.
        """
        if (not isinstance(expected_tip, str) or not re.fullmatch(r'[a-f0-9]{64}', expected_tip)
                or type(expected_count) is not int or expected_count < 0):
            raise ValueError('CHECKPOINT_INVALID')
        if not isinstance(coordinates, (tuple, list)) or not 1 <= len(coordinates) <= 1728:
            raise ValueError('BATCH_SCOPE_INVALID')
        for coordinate in coordinates:
            hsn_parts(coordinate)
        if len(set(coordinates)) != len(coordinates):
            raise ValueError('DUPLICATE_COORDINATE')
        rows = self.events()
        prev = '0' * 64
        seen = {}
        retracted = set()
        for row in rows:
            payload = {k:row[k] for k in ('event_id','mode','coordinate','topic_id','action','source_ref','source_digest','retract_event_id')}
            if row['prev_hash'] != prev or sha(prev+'|'+canonical(payload)) != row['event_hash']:
                raise ValueError('FAIL_CHAIN')
            hsn_parts(row['coordinate'])
            event_id, action, target = row['event_id'], row['action'], row['retract_event_id']
            if row['mode'] != 'WORK' or action not in ACTIONS or event_id in seen:
                raise ValueError('EVENT_SCOPE_INVALID')
            if action == 'RETRACT':
                original = seen.get(target)
                if (original is None or original['action'] == 'RETRACT' or target in retracted
                        or original['coordinate'] != row['coordinate'] or original['topic_id'] != row['topic_id']):
                    raise ValueError('INVALID_RETRACTION')
                retracted.add(target)
            elif target is not None:
                raise ValueError('INVALID_RETRACTION')
            seen[event_id] = row
            prev = row['event_hash']
        if len(rows) != expected_count or prev != expected_tip:
            raise ValueError('CHECKPOINT_CHANGED')
        result = {coordinate: {} for coordinate in coordinates}
        for row in rows:
            if (row['coordinate'] in result and row['event_id'] not in retracted
                    and row['action'] in ('NOTE', 'CHALLENGE')):
                topics = result[row['coordinate']]
                topic = row['topic_id']
                topics[topic] = topics.get(topic, 0) + (1 if row['action'] == 'NOTE' else -1)
        return result
