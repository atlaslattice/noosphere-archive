import json,sys
from pathlib import Path
from src.evolution import load_state
from src.promotion import candidate_eval
from src.protocol import BASE,Policy
OUT=Path(__file__).parent/'outputs'
chunk=int(sys.argv[1]);assert chunk in range(4)
start=chunk*36;end=(chunk+1)*36
st=load_state(OUT/'CHECKPOINT_15000.json')
sel=json.loads((OUT/'POLICY_PROMOTION_REVIEW_144.json').read_text())
results=[]
for i in range(start,end):
  policies={'initial_minimal':BASE,'fixed_robust':Policy(3,6),
   'evolved_15000':Policy(**st['policies'][i]),'guarded_selection':Policy(**sel[i]['selected'])}
  results.append({'module_index':i,'results':{name:candidate_eval(p,i,'GF9-R2-INDEPENDENT-BLIND',4) for name,p in policies.items()}})
path=OUT/f'BLIND_CHUNK_{chunk+1:02d}.json';path.write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({'chunk':chunk+1,'modules':len(results),'evaluated_packet_cases':len(results)*4*12*4,'status':'ACTUAL_COMPUTED','path':str(path)}))
