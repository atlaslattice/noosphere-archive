#!/usr/bin/env python3
"""Offline deterministic Chromium responsiveness comparison. No network or host use."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import argparse,json,statistics,hashlib
p=argparse.ArgumentParser();p.add_argument('--baseline',required=True);p.add_argument('--optimized');p.add_argument('--out');p.add_argument('--samples',type=int,default=32)
a=p.parse_args()
inputfiles={'baseline':Path(a.baseline)}
if a.optimized:inputfiles['optimized']=Path(a.optimized)

with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--disable-background-networking','--disable-features=NetworkService','--disable-extensions'])
 result={'schema':'atlas.meta145.local.chromium.benchmark/v1','browser':'/usr/bin/chromium','runs':a.samples,'offline':True,'hostedSwarmLatencyMeasured':False,'pages':{}}
 for name,path in inputfiles.items():
  page=b.new_page(viewport={'width':412,'height':915},device_scale_factor=1)
  txt=path.read_text(encoding='utf-8')
  page.set_content(txt,wait_until='domcontentloaded')
  page.wait_for_function("document.querySelector('#count')?.textContent.includes('1,728')",timeout=20000)
  data=page.evaluate('''(samples)=>{
      const q=document.querySelector('#search');
      const count=document.querySelector('#count');
      const house=document.querySelector('#house');
      let rows={fullReset:[],narrowExact:[],houseSelect:[]};
      const edit=(text)=>{q.value=text;const t=performance.now();q.dispatchEvent(new Event('input',{bubbles:true}));return performance.now()-t;};
      const houseEdit=(val)=>{house.value=val;const t=performance.now();house.dispatchEvent(new Event('input',{bubbles:true}));return performance.now()-t;};
      for(let i=0;i<samples+6;i++){
         houseEdit('');edit('H08.S01.N10');const exact=edit('H12.S03.N04');
         const reset=edit('');
         const selected=houseEdit('H10');
         if(i>=6){rows.fullReset.push(reset);rows.narrowExact.push(exact);rows.houseSelect.push(selected);}
      }
      houseEdit('');edit('');
      let entries=document.querySelectorAll('#entries button.entry').length;
      return {events:rows,fullMatchCount:count.textContent.trim(),visibleDomRows:entries,clientHeapMB:performance.memory?.usedJSHeapSize/1048576||null};
  }''',a.samples)
  def metric(values):return {'median_ms':round(statistics.median(values),3),'p95_ms':round(sorted(values)[int(.95*(len(values)-1))],3),'min_ms':round(min(values),3),'max_ms':round(max(values),3)}
  result['pages'][name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':len(path.read_bytes()),'source':str(path),'fullMatchCount':data['fullMatchCount'],'visibleDomRows':data['visibleDomRows'],'clientHeapMBApprox':data['clientHeapMB'],'metrics':{k:metric(v) for k,v in data['events'].items()},'rawEventMs':data['events']}
  page.close()
 b.close()
if a.optimized:
 result['speedupMedian']={key:round(result['pages']['baseline']['metrics'][key]['median_ms']/max(.001,result['pages']['optimized']['metrics'][key]['median_ms']),2) for key in ('fullReset','narrowExact','houseSelect')}
if a.out:Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:{'bytes':v['bytes'],'visibleDomRows':v['visibleDomRows'],'metrics':v['metrics']} for k,v in result['pages'].items()},indent=2))
if 'speedupMedian' in result:print('speedupMedian:',result['speedupMedian'])
