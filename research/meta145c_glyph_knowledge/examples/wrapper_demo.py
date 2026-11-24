"""No-model-call demo of reasoning-context augmentation and postflight verifier."""
import json, tempfile
from pathlib import Path
from src.gf8 import Plate,mode_hz
from src.reasoning_filter import prepare_reasoning_context,postflight_claim_gate,safe_explanation,with_local_review_tip
from src.memory import LocalMemory

plate=Plate(material='steel',width_m=.30,height_m=.30,thickness_m=.001)
f=mode_hz(plate,1,1)
ctx=prepare_reasoning_context(hsn='H01.S05.N10',gf7='GF7.B01.M05.C10',
                             plate=plate,drive_hz=f,
                             source_refs=('https://pmc.ncbi.nlm.nih.gov/articles/PMC6812332/',))
print(safe_explanation(ctx))
claim={'claim_kind':'GF8_PREDICTED_MODE_ONLY',
       'frequency_hz':ctx['physical_model_output']['nearest_mode']['frequency_hz'],
       'model_status':ctx['physical_model_output']['status']}
print(json.dumps(postflight_claim_gate(ctx,claim),indent=2))
with tempfile.TemporaryDirectory() as d:
    location=str(Path(d)/'review.sqlite')
    memory=LocalMemory(location)
    before=with_local_review_tip(ctx,memory)['receipt_sha256']
    memory.append({'event_id':'gf8-review-demo-001','mode':'WORK','scope':'SYNTHETIC_LOCAL_REVIEW',
        'coordinate':'H01.S05.N10','topic_id':None,'action':'NOTE',
        'source_ref':'urn:atlas:synthetic:gf8-wrapper-demonstration','source_digest':'e'*64})
    after=with_local_review_tip(ctx,memory)['receipt_sha256']
    memory.close()
    reopened=LocalMemory(location)
    assert with_local_review_tip(ctx,reopened)['receipt_sha256']==after
    reopened.close()
    print(json.dumps({'review_hint_changed':before!=after,'survived_restart':True,
                      'model_weight_updates':0,'host_or_canon_changes':0},indent=2))
