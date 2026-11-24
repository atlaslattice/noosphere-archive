"""Real headless Chromium UI checks on fully offline GF9 R2 visualization."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'outputs'/'GF9_ROSETTA_EXPLORER_PRIVATE.html').read_text()
checks=[];errors=[];requests=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':390,'height':844})
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('request',lambda q:requests.append(q.url))
 page.set_content(HTML,wait_until='load')
 def ck(name,ok):
  checks.append({'name':name,'passed':bool(ok)})
  if not ok:raise AssertionError(name)
 ck('title',page.title()=='GF9-R2 · The Rosetta Lab')
 ck('all modules initially',page.locator('#sphere option').count()==144)
 ck('chapters twelve',page.locator('#chapter option').count()==12)
 ck('trials text',page.locator('#trials').inner_text()=='15,000')
 ck('accepted count',page.locator('#accepted').inner_text()=='3,462')
 ck('benchmarks four bars',page.locator('#bars .bar').count()==4)
 page.locator('#search').fill('Plasma confinement')
 ck('specific node search',page.locator('#sphere option').count()>=1)
 page.locator('#search').fill('H01.S05')
 ck('sphere ID filter',page.locator('#sphere option').count()==1)
 page.locator('#chapter').select_option('7')
 ck('resonance chapter', 'RESONANCE' in page.locator('#operation').inner_text())
 ck('mode caption', 'Mode (' in page.locator('#meshcaption').inner_text())
 ck('source node preserved', 'H01.S05.N08' in page.locator('#proof').inner_text())
 ck('roles clear','NONE' in page.locator('#proof').inner_text())
 ck('canvas drawn',page.locator('#nodal').evaluate('(c)=>c.getContext("2d").getImageData(300,200,1,1).data[3]')==255)
 page.locator('#chapter').select_option('8')
 ck('counterexample HOLD status','HOLD' in page.locator('#proof').inner_text())
 page.locator('#search').fill('nonexistentxyz123')
 ck('empty search accessible','No matching Sphere' in page.locator('#desc').inner_text())
 page.locator('#search').fill('')
 ck('restore 144',page.locator('#sphere option').count()==144)
 ck('zero network requests',len(requests)==0)
 ck('zero JS exceptions',len(errors)==0)
 browser.close()
result={'checks':checks,'passed':sum(x['passed'] for x in checks),'total':len(checks),'page_errors':errors,'network_requests':requests,'html_sha256':hashlib.sha256(HTML.encode()).hexdigest(),'actual_browser':'PLAYWRIGHT_CHROMIUM_SET_CONTENT_OFFLINE','hosted':False}
( ROOT/'outputs'/'BROWSER_SMOKE.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':'PASS' if result['passed']==result['total'] else 'FAIL','passed':result['passed'],'total':result['total'],'browser':'real chromium','network_requests':len(requests),'js_errors':len(errors)}))
