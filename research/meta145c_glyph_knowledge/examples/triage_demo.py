"""Cumulative knowledge reorganization demo: historical → note → restart → retract.
Records a purely synthetic review note, does not assess OpenAlex topic accuracy.
"""
from pathlib import Path
import sqlite3,hashlib,json
from src.memory import LocalMemory
from src.knowledge import topic_view,shared_topic_neighbors,source_card
BASE=Path(__file__).parents[1]


def run(db_path,memory_path):
    db=sqlite3.connect(db_path);mem=LocalMemory(memory_path)
    hsn='H01.S05.N10';target='T10642';src='urn:atlas:synthetic:triage-pilot-t10642'
    event={'event_id':'triagenote01','mode':'WORK','scope':'SYNTHETIC_LOCAL_REVIEW','coordinate':hsn,'topic_id':target,'action':'NOTE','source_ref':src,'source_digest':hashlib.sha256(src.encode()).hexdigest()}
    before=topic_view(db,hsn,mem,limit=20)
    mem.append(event)
    noted=topic_view(db,hsn,mem,limit=20)
    mem.close();mem=LocalMemory(memory_path)
    after_restart=topic_view(db,hsn,mem,limit=20)
    mem.append({**event,'event_id':'triageretract01','action':'RETRACT','retract_event_id':'triagenote01'})
    retracted=topic_view(db,hsn,mem,limit=20)
    card=source_card(db,hsn,'07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6')
    neighbors=shared_topic_neighbors(db,hsn)
    result={'node':hsn,'topic':target,
      'historical_first':before['items'][0]['topic_id'],
      'after_note_first':noted['items'][0]['topic_id'],
      'after_restart_first':after_restart['items'][0]['topic_id'],
      'after_retraction_first':retracted['items'][0]['topic_id'],
      'memory_chain_verification':mem.verify(),
      'source_card':{k:card[k] for k in ('hsn','name','role','record_digest')},
      'shared_topic_candidate_paths':neighbors['total_candidate_paths'],
      'no_hosting':True,'no_model_weight_updates':True,'no_accepted_semantic_edges':True,'no_auto_canon':True}
    mem.close();db.close()
    return result

if __name__=='__main__':
 p=BASE/'outputs';res=run(p/'atlas_meta145_knowledge.sqlite',p/'LOCAL_TRIAGE_REORGANIZATION_DEMO.sqlite')
 (p/'TRIAGE_ORGANIZATION_RECEIPT.json').write_text(json.dumps(res,indent=2)+'\n')
 print(json.dumps(res,indent=2))
