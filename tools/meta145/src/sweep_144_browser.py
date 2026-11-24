#!/usr/bin/env python3
"""144 real offline Chromium sphere-navigation checks, NOT 144 agent turns."""
from pathlib import Path
import argparse,hashlib,json,statistics
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--optimized',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
allout={}
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage','--disable-background-networking'])
 for key,path in [('baseline',a.baseline),('optimized',a.optimized)]:
  page=browser.new_page(viewport={'width':412,'height':915},device_scale_factor=1)
  page.set_content(path.read_text(),wait_until='domcontentloaded')
  rows=page.evaluate('''()=>{
     const raw=JSON.parse(document.querySelector('#dataset').textContent).nodes;
     const names=[...new Set(raw.map(n=>n.sphere))];
     const sphere=document.querySelector('#sphere'),house=document.querySelector('#house'),q=document.querySelector('#search'),entries=document.querySelector('#entries');
     house.value='';q.value='';const result=[];
     for(const sid of names){
       sphere.value=sid;const start=performance.now();sphere.dispatchEvent(new Event('input',{bubbles:true}));const elapsed=performance.now()-start;
       const found=entries.querySelectorAll('button.entry'),valid=found.length===12&&
         found[0].dataset.coord?found[0].dataset.coord.startsWith(sid+'.'):found[0].textContent.startsWith(sid+'.');
       result.push({sphere:sid,elapsed_ms:elapsed,found:found.length,sourceValid:!!valid});
     }
     return result;
  }''')
  assert len(rows)==144 and all(r['sourceValid'] and r['found']==12 for r in rows),(key,'failed sphere check')
  ms=[r['elapsed_ms'] for r in rows]
  allout[key]={'viewer_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'checks':len(rows),'status':'144_BROWSER_FILTERS_PASS_LOCAL',
    'median_ms':round(statistics.median(ms),4),'p95_ms':round(sorted(ms)[int(.95*(len(ms)-1))],4),'max_ms':round(max(ms),4),'rows':rows}
  page.close()
 browser.close()
result={'schema':'atlas.meta145.sphere-ui-sweep/v1','spheres_checked':144,'source_nodes_per_sphere':12,
        'computation_only':True,'hosted_not_verified':True,'variants':allout,
        'median_speedup':round(allout['baseline']['median_ms']/allout['optimized']['median_ms'],2) if allout['optimized']['median_ms']>0 else None}
a.out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:{x:v[x] for x in ['checks','median_ms','p95_ms','max_ms']} for k,v in allout.items()}))
