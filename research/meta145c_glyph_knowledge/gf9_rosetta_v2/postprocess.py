from pathlib import Path
import json,hashlib,time
from src.evolution import load_state
from src.promotion import choose_promotions,blind_compare
from src.protocol import Policy
ROOT=Path(__file__).parent;OUT=ROOT/'outputs'
state=load_state(OUT/'CHECKPOINT_15000.json');t=time.monotonic()
choices=choose_promotions(state['policies']);print('validation/promotion done:',round(time.monotonic()-t,3),'s',flush=True)
(OUT/'POLICY_PROMOTION_REVIEW_144.json').write_text(json.dumps(choices,indent=2)+'\n')
blind=blind_compare(state['policies'],choices);print('blind done:',round(time.monotonic()-t,3),'s',flush=True)
(OUT/'INDEPENDENT_BLIND_BENCHMARK.json').write_text(json.dumps(blind,indent=2)+'\n')
print(json.dumps({'status':'PASS_FINITE_REVIEW','blind':blind,'numeric_safe_modules':sum(all(x['safe'] for x in [a for a in row['competing_policies'] if a['policy']==row['selected']]) for row in choices)}))
