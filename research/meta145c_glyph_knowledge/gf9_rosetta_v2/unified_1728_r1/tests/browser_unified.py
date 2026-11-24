"""Owner-source offline 1728-node viewer acceptance test, no network access."""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('--html',required=True);p.add_argument('--receipt',required=True);args=p.parse_args()
checks=[];errors=[];req=[]
def yes(label,value):
    checks.append({'check':label,'pass':bool(value)})
    if not value:raise AssertionError(label)
with sync_playwright() as pl:
    browser=pl.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':430,'height':840})
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:req.append(r.url))
    page.set_content(Path(args.html).read_text(),wait_until='load',timeout=30000)
    yes('DOM renders heading',page.locator('h1').count()==1)
    yes('Exactly twelve House options',page.locator('#house option').count()==13)
    yes('Exactly 144 Sphere options',page.locator('#sphere option').count()==145)
    yes('Initially all 1728 match', '1728 of 1,728' in page.locator('#count').inner_text())
    yes('First 48 records rendered',page.locator('.node').count()==48)
    page.locator('#next').click()
    yes('Pagination renders 96',page.locator('.node').count()==96)
    page.locator('#query').fill('H01.S05.N10')
    yes('Exact coordinate filter matches one', '1 of 1,728' in page.locator('#count').inner_text())
    yes('Plasma confinement appears', 'Plasma confinement' in page.locator('.node').first.inner_text())
    page.locator('.node').first.click()
    yes('Twelve module results visible',page.locator('#checks li').count()==12)
    yes('Physical model uncalibrated label', 'simulated, not measured' in page.locator('#detail').inner_text())
    yes('Typed GF7 analogy shown', 'GF7.B01.M05.C10' in page.locator('#detail').inner_text())
    page.locator('#query').fill('')
    page.locator('#house').select_option('H08')
    yes('One House 144 nodes', '144 of 1,728' in page.locator('#count').inner_text())
    page.locator('#sphere').select_option('H08.S01')
    yes('One Sphere twelve nodes', '12 of 1,728' in page.locator('#count').inner_text())
    page.locator('#query').fill('H08.S01.N10')
    yes('Music instrument type/source present',page.locator('.node').count()==1)
    page.locator('.node').first.click()
    yes('Method versus domain surfaced',page.locator('#detail .tag').count()==2)
    yes('Source hash visible', 'Source-bound record digest' in page.locator('#detail').inner_text())
    yes('No browser script errors',len(errors)==0)
    yes('No external network requests',len(req)==0)
    page.screenshot(path=str(Path(args.html).with_suffix('.png')),full_page=True)
    browser.close()
receipt={'status':'PASS' if all(x['pass'] for x in checks) else 'FAIL','checks_passed':sum(x['pass'] for x in checks),'checks_total':len(checks),
         'checks':checks,'network_calls':req,'exceptions':errors,'scope':'LOCAL_IN_MEMORY_CHROMIUM_NO_HOST'}
Path(args.receipt).write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:receipt[k] for k in ('status','checks_passed','checks_total','network_calls','exceptions')},indent=2))
