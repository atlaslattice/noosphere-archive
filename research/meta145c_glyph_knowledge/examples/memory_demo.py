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
 # A fresh trial has a known empty anchor; keep it outside the mutable ledger.
 checkpoint={'expected_tip':'0'*64,'expected_count':0}
 for eid,act,prior in events:
  ev={**base,'event_id':eid,'action':act}
  if prior:ev['retract_event_id']=prior
  receipt=mem.append(ev,**checkpoint)
  checkpoint={'expected_tip':receipt['event_hash'],'expected_count':receipt['count']}
  batch=mem.verified_triage_batch([base['coordinate']],**checkpoint)
  vals.append({'event':eid,'triage_delta':batch[base['coordinate']].get(base['topic_id'],0)})
 tip=mem.verify();mem.close();mem=LocalMemory(a.db)
 batch=mem.verified_triage_batch([base['coordinate']],**checkpoint)
 result={'states':vals,'verify_after_reopen':mem.verify(),'retained_local_checkpoint':checkpoint,
         'after_reopen_delta':batch[base['coordinate']].get(base['topic_id'],0),
         'real_source_reviewed':False,'source_verified':False,'model_weights_updated':False,'can_write_canon':False,'real_learning_observed':'PERSISTENT_LOCAL_REVIEW_ROUTING_ONLY'}
 mem.close();print(json.dumps(result,indent=2))
if __name__=='__main__':main()
