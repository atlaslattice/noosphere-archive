"""Real Chromium test of the standalone, no-network GF8 viewer."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

html=Path(__file__).resolve().parents[1]/'outputs/GF8_FREQUENCY_EXPLORER.html'
records=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':900,'height':800},reduced_motion='reduce')
    page=context.new_page()
    errors=[]; requests=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda req:requests.append(req.url) if req.url.startswith(('http:','https:')) else None)
    page.set_content(html.read_text(),wait_until='load',timeout=40000) # host file:// blocked; in-memory page
    base=page.evaluate('window.__atlasGF8')
    assert base['cards']==1728 and base['resonances']>=12,base
    assert base['allStatuses']['HOLD_MODEL_ENVELOPE']>0
    assert base['allStatuses']['SCREENING_MODEL_IN_ENVELOPE']>0
    assert page.locator('canvas#glyph').is_visible()
    assert page.locator('#head').inner_text().startswith('Mode')
    assert page.locator('#assessment').inner_text().find('ENVELOPE')>=0
    records.append({'check':'initial','status':'PASS','cards':base['cards']})
    for band in range(1,13):
        page.evaluate('(b)=>window.__atlasGF8.selectBand(b)',band)
        status=page.locator('#assessment').inner_text()
        assert status and page.locator('#metrics').locator('.metric').count()==8
        records.append({'check':f'band_{band:02d}','status':'PASS','status_label':status[:58]})
    page.select_option('#mode','12');page.select_option('#context','12')
    assert page.locator('#head').inner_text().startswith('Mode'),page.locator('#head').inner_text()
    page.evaluate('window.__atlasGF8.selectBand(12)')
    assert 'HOLD' in page.locator('#assessment').inner_text()
    records.append({'check':'large_mode_extreme_hold','status':'PASS'})
    page.select_option('#mode','1');page.select_option('#context','5');page.evaluate('window.__atlasGF8.selectBand(5)')
    assert 'WITHIN DECLARED' in page.locator('#assessment').inner_text()
    records.append({'check':'benchtop_mode_feasible','status':'PASS'})
    page.click('#fixedButton')
    assert 'Fixed plate driven field' in page.locator('#head').inner_text()
    assert 'Modal basis 8×8' in page.locator('#fixedDetails').inner_text()
    records.append({'check':'forced_response','status':'PASS'})
    page.select_option('#resonance','7');
    assert 'Fixed plate driven field' in page.locator('#head').inner_text()
    records.append({'check':'change_driven_resonance','status':'PASS'})
    page.screenshot(path=str(html.parent/'GF8_SCREENSHOT_DESKTOP.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':820})
    page.screenshot(path=str(html.parent/'GF8_SCREENSHOT_MOBILE.png'),full_page=True)
    records.append({'check':'mobile_viewport','status':'PASS'})
    assert not errors,errors
    assert not requests,requests
    browser.close()
    receipts={'schema':'atlas.gf8.browser-smoke/v1','checks':len(records),
              'passed':len(records),'errors':errors,'network_requests':requests,
              'tested_file':html.name,'status':'LOCAL_HEADLESS_CHROMIUM_PASS'}
    (html.parent/'BROWSER_RECEIPT.json').write_text(json.dumps(receipts,indent=2)+'\n')
    print(json.dumps(receipts,indent=2))
