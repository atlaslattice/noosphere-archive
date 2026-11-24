"""One finite Work-only SYNTHETIC memory trial: note → reload → challenge → retract.
The review events never become source truth, model updates, canonical knowledge,
resident identity, session permission, or scientific experimental results.
"""
from __future__ import annotations
import argparse,hashlib,json
from src.memory import LocalMemory

def main():
 p=argparse.ArgumentParser();p.add_argument('--db',required=True);a=p.parse_args()
 mem=LocalMemory(a.db)
 src='urn:atlas:synthetic:meta145-c-memory-trial'
 base={'mode':'WORK','scope':'SYNTHETIC_LOCAL_REVIEW','coordinate':'H01.S05.N10','topic_id':'T10346',
       'source_ref':src,'source_digest':hashlib.sha256(src.encode()).hexdigest()}
 events=[('note001','NOTE',None),('challenge001','CHALLENGE',None),('retract001','RETRACT','challenge001')]
 vals=[]
 for eid,act,prior in events:
  ev={**base,'event_id':eid,'action':act}
  if prior:ev['retract_event_id']=prior
  mem.append(ev)
  vals.append({'event':eid,'triage_delta':mem.triage_delta(base['coordinate'],base['topic_id'])})
 tip=mem.verify();mem.close();mem=LocalMemory(a.db)
 result={'states':vals,'verify_after_reopen':mem.verify(),'after_reopen_delta':mem.triage_delta(base['coordinate'],base['topic_id']),
         'real_source_reviewed':False,'source_verified':False,'model_weights_updated':False,'can_write_canon':False,'real_learning_observed':'PERSISTENT_LOCAL_REVIEW_ROUTING_ONLY'}
 mem.close();print(json.dumps(result,indent=2))
if __name__=='__main__':main()
