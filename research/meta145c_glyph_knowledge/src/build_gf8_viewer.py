"""Offline standalone GF8 frequency/geometry/mode explorer, no server or network."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import json
from .gf8 import (Plate,GF7_BANDS,GF7_MATERIALS,GF7_MODES,reference_for_gf7,
    driven_glyph,resonance_table,mode_hz,gfpayload_hash)

# Can also be imported/executed as python -m src.build_gf8_viewer

def build_data()->dict:
    cards=[]
    for band in range(1,13):
        for mode in range(1,13):
            for ctx in range(1,13):
                cards.append(reference_for_gf7(f'GF7.B{band:02d}.M{mode:02d}.C{ctx:02d}'))
    plate=Plate()
    resonances=[];seen=[]
    for item in resonance_table(plate,8,8):
        if any(abs(item['frequency_hz']-x)<1e-6 for x in seen):continue
        if abs(item['drive_coupling'])<0.04:continue
        g=driven_glyph(plate,item['frequency_hz'],max_mode=8,grid=51)
        if g['status']!='ANALYTIC_DRIVEN_FIELD_NEAR_RESONANCE':continue
        resonances.append({'mode':[item['m'],item['n']],'frequency_hz':item['frequency_hz'],
                           'nodal_bitmap':g['nodal_proxy_bitmap'],
                           'max_field_m_per_force_n':g['peak_complex_displacement_m_per_unit_forcing'],
                           'status':g['status']})
        seen.append(item['frequency_hz'])
        if len(resonances)==18:break
    if len(cards)!=1728 or len(resonances)<12:raise AssertionError('EXPLORER_INCOMPLETE')
    counts=Counter(x['model_validity']['status'] for x in cards)
    data={'schema':'atlas.gf8.bounded-plate-viewer/v1','source_system':'GF7 positional reference, new GF8 scientific model',
          'physics_scope':'LINEAR_SIMPLY_SUPPORTED_RECTANGULAR_PLATE_ONLY',
          'all_modeled_1728_is_not_empirical':True,'source_edition_of_original_gf7':'v0.7 source-only',
          'model':Plate().metadata(), 'cards':cards,'fixed_plate_resonances':resonances,
          'status_counts':dict(counts),'no_live_measurements':True,
          'no_host_or_model_weight_changes':True}
    data['data_sha256']=gfpayload_hash(data)
    return data


def make_html(data:dict)->str:
    payload=json.dumps(data,ensure_ascii=True,separators=(',',':')).replace('</','<\\/')
    return r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Atlas GF8 · Physically grounded cymatic glyphs</title>
<style>
:root{color-scheme:dark;--ink:#e9f5ff;--muted:#a9c6d1;--line:#315867;--bg:#06121a;--panel:#0d2631;--accent:#7df3d3;--warn:#fbc77b}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 17% 0%,#193c46,transparent 42%),var(--bg);color:var(--ink);font-family:system-ui,Segoe UI,Arial,sans-serif}header,main,footer{max-width:1120px;margin:auto;padding:22px}h1{margin:6px 0;font-size:clamp(1.65rem,4vw,2.55rem)}p{color:var(--muted);line-height:1.55}.pill{font-size:.75rem;letter-spacing:.06em;font-weight:800;color:#05181c;background:var(--accent);display:inline-block;padding:5px 9px;border-radius:30px}.grid{display:grid;grid-template-columns:minmax(280px,1.3fr) minmax(260px,.7fr);gap:16px}.panel{background:var(--panel);padding:20px;border:1px solid var(--line);border-radius:14px;min-width:0}.controls{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.controls label{font-size:.82rem;color:var(--muted);display:block}select,button{width:100%;padding:10px;margin-top:6px;background:#12313c;border:1px solid #4c7787;color:var(--ink);border-radius:8px;font:inherit}button{cursor:pointer}button:hover{border-color:var(--accent)}canvas{width:100%;height:auto;aspect-ratio:1;border-radius:8px;border:1px solid #54717c;background:#041219;image-rendering:auto}.notice{color:var(--warn);border-left:3px solid var(--warn);padding:12px 16px;background:#30261c}.good{color:var(--accent)}.fields{display:grid;grid-template-columns:repeat(2,1fr);gap:6px;margin-top:14px}.metric{border:1px solid #274c5b;padding:10px;border-radius:7px}.metric label{color:var(--muted);font-size:.72rem;display:block}.metric b{font-size:1.05rem;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}.muted{color:var(--muted);font-size:.82rem}.bars{display:grid;grid-template-columns:repeat(12,1fr);gap:3px;margin:10px 0 18px}.bars button{margin:0;padding:8px 2px;font-size:.73rem}.bars button.active{background:var(--accent);color:#041319}.small{font-size:.77rem}.line{height:1px;background:var(--line);margin:15px 0}.box{margin-top:10px;padding:12px;border-radius:8px;background:#12313c}.split{display:flex;gap:8px;align-items:center;justify-content:space-between;flex-wrap:wrap}.ft{font-size:.78rem}a{color:var(--accent)}@media(max-width:750px){.grid{grid-template-columns:1fr}.controls{grid-template-columns:1fr 1fr}.panel{padding:14px}.bars{grid-template-columns:repeat(6,1fr)}}
</style></head><body><header><span class="pill">SOURCE-ONLY ANALYTIC MODEL · NO CALIBRATION</span><h1>Atlas GF8: From frequency to actual nodal geometry</h1><p>GF7 bands are useful addresses. GF8 predicts how a specified plate would vibrate under an explicitly declared boundary model. Every display is source-typed; no frequency is a universal glyph, no sand experiment is claimed, and no GPT model weights are changed.</p></header><main>
<div class="panel"><h2>12 original frequency bands</h2><div class="bars" id="bands"></div><div class="controls"><label>Mode <select id="mode"></select></label><label>Material / aspect <select id="context"></select></label><label>Representation <select id="view"><option value="inverse">Inverse-designed mode</option><option value="fixed">Fixed-plate forced response</option></select></label></div></div><div class="grid" style="margin-top:16px">
<section class="panel"><h2 id="head">Mode glyph</h2><canvas id="glyph" width="480" height="480" aria-label="Analytic simulated nodal pattern"></canvas><p class="small" id="visualNote"></p></section>
<section class="panel"><h2>Physics & provenance</h2><div class="fields" id="metrics"></div><div id="assessment" class="box"></div><div class="line"></div><p class="muted">Predictions use Kirchhoff–Love isotropic bending with simply supported boundaries. The baseline steel plate is 30 cm square and 1 mm thick. Free-edge or clamped Chladni plates require a different solver.</p></section>
</div><section class="panel" style="margin-top:16px"><h2>Fixed test plate: actual modeled resonances</h2><p>Choose one of the predicted resonances for a single unchanged plate. Unlike the inverse-design demonstration above, dimensions stay fixed. This is modal superposition with damping and off-centre excitation, but does not simulate individual grains.</p><div class="controls" style="grid-template-columns:repeat(2,1fr)"><label>Predicted resonance <select id="resonance"></select></label><label>Explanation <button id="fixedButton">Show forced response</button></label></div><div class="box" id="fixedDetails"></div></section>
</main><footer><p class="ft">No API requests. GF7 positional namespace ≠ Ariadne HSN ≠ KG8 language aliases ≠ physical resonance. Synthetic GF8 computations are not calibrated measurements, cultural truth, CANON, or resident identity. Source: PMC6812332 (simply supported rectangular plate measurements); SInES Chladni tool (boundary/excitation modes).</p></footer>
<script type="application/json" id="atlas-data">'''+payload+r'''</script>
<script>
(()=>{'use strict';const d=JSON.parse(document.querySelector('#atlas-data').textContent);const $=x=>document.getElementById(x);const cards=new Map(d.cards.map(x=>[x.source_coordinate,x]));let currentBand=4;
const N=x=>Number(x).toLocaleString(undefined,{maximumFractionDigits:4});
for(let i=1;i<=12;i++){const b=document.createElement('button');b.textContent='B'+String(i).padStart(2,'0');b.dataset.band=i;b.setAttribute('aria-label','Frequency band '+i);b.onclick=()=>{currentBand=i;$('view').value='inverse';render()};$('bands').append(b)}
for(let i=1;i<=12;i++){const m=document.createElement('option');m.value=i;m.textContent='M'+String(i).padStart(2,'0');$('mode').append(m);const c=document.createElement('option');c.value=i;const a=d.cards.find(x=>x.source_coordinate===`GF7.B01.M01.C${String(i).padStart(2,'0')}`);c.textContent='C'+String(i).padStart(2,'0')+' '+a.material+' · '+a.aspect_b_over_a;$('context').append(c)}
$('mode').value='01';$('mode').value='1';$('context').value='5';
for(let i=0;i<d.fixed_plate_resonances.length;i++){const r=d.fixed_plate_resonances[i],o=document.createElement('option');o.value=i;o.textContent=N(r.frequency_hz)+' Hz  ('+r.mode.join(',')+')';$('resonance').append(o)}
const canv=$('glyph'),ctx=canv.getContext('2d');
function paintField(arr){const n=arr.length,sz=canv.width/n;ctx.fillStyle='#05131a';ctx.fillRect(0,0,canv.width,canv.height);
 for(let y=0;y<n;y++)for(let x=0;x<n;x++){let v=arr[y][x];const a=Math.max(0,Math.min(1,v));let R=Math.round(3+28*a),G=Math.round(245-177*a),B=Math.round(201-104*a);ctx.fillStyle=`rgb(${R},${G},${B})`;ctx.fillRect(x*sz,y*sz,sz+0.6,sz+0.6)} }
function pattern(m,n){const size=161,arr=[];for(let j=0;j<size;j++){const row=[];for(let i=0;i<size;i++){const a=Math.abs(Math.sin(m*Math.PI*i/(size-1))*Math.sin(n*Math.PI*j/(size-1)));row.push(a)}arr.push(row)}paintField(arr)}
function bitmapToImage(bitmap){paintField(bitmap.map(row=>[...row].map(v=>v==='1'?0:1)))}
function details(k,v){const e=document.createElement('div');e.className='metric';const a=document.createElement('label');a.textContent=k;const b=document.createElement('b');b.textContent=v;e.append(a,b);return e}
function render(){for(const b of $('bands').children)b.classList.toggle('active',Number(b.dataset.band)===currentBand);
 const m=Number($('mode').value),c=Number($('context').value),key=`GF7.B${String(currentBand).padStart(2,'0')}.M${String(m).padStart(2,'0')}.C${String(c).padStart(2,'0')}`;const x=cards.get(key);if(!x)throw Error('MISSING_CARD');
 $('metrics').replaceChildren(details('GF7 address',key),details('Target',N(x.target_frequency_hz)+' Hz'),details('Calculated mode',N(x.analytic_frequency_hz)+' Hz'),details('Mode indices',x.mode.join(' × ')),details('Plate width',N(x.required_width_m*100)+' cm'),details('Plate height',N(x.required_height_m*100)+' cm'),details('Thickness',N(x.thickness_m*1e3)+' mm'),details('Material',x.material));
 $('head').textContent=`Mode (${x.mode[0]},${x.mode[1]}) — ${N(x.target_frequency_hz)} Hz`;pattern(...x.mode);
 const valid=x.model_validity.status==='SCREENING_MODEL_IN_ENVELOPE';$('assessment').replaceChildren();const strong=document.createElement('strong');strong.textContent=valid?'WITHIN DECLARED SCREENING ENVELOPE':'HOLD: NOT PHYSICALLY QUALIFIED';strong.className=valid?'good':'';$('assessment').append(strong);const p=document.createElement('p');p.textContent=valid?'Analytic nodal eigenfunction for an inverse-sized simply-supported plate. Still unmeasured.':'Geometry/wavelength model limits: '+x.model_validity.reasons.join(', ')+'. Do NOT treat the colorful glyph as a predicted physical experiment.';$('assessment').append(p);
 $('visualNote').textContent='Blue-green color maps |sin(mπx/a) sin(nπy/b)|. Bright curves denote modeled nodal regions; this is an eigenmode, not a photograph or sand-flow simulation.';
}
function fixed(){const r=d.fixed_plate_resonances[Number($('resonance').value)];bitmapToImage(r.nodal_bitmap);$('metrics').replaceChildren(details('Fixed plate','30 × 30 cm'),details('Material','steel'),details('Thickness','1 mm'),details('Drive frequency',N(r.frequency_hz)+' Hz'),details('Predicted mode',r.mode.join(' × ')),details('Boundary','Simply supported'),details('Damping','0.012'),details('Model status','Analytic only'));$('head').textContent=`Fixed plate driven field: ${N(r.frequency_hz)} Hz`;const box=$('fixedDetails');box.textContent='Nominal steel 30×30 cm, 1 mm thick, damping 0.012, drive at normalized (0.31,0.43). Modal basis 8×8, linear response at modeled resonance '+N(r.frequency_hz)+' Hz; no calibration or grain transport. Model mode '+r.mode.join('×')+'.';$('assessment').textContent='Model output only; experiment and mounting are unverified.';$('visualNote').textContent='Nodal-proxy field from the complex driven modal superposition, not a unique frequency-to-meaning language.';}
$('mode').addEventListener('change',()=>{$('view').value='inverse';render()});$('context').addEventListener('change',()=>{$('view').value='inverse';render()});$('view').addEventListener('change',()=>{$('view').value==='fixed'?fixed():render()});$('fixedButton').onclick=()=>{$('view').value='fixed';fixed()};$('resonance').addEventListener('change',()=>{if($('view').value==='fixed')fixed()});
render();window.__atlasGF8={schema:d.schema,cards:d.cards.length,resonances:d.fixed_plate_resonances.length,allStatuses:d.status_counts,dataDigest:d.data_sha256,selectBand:(b)=>{if(!Number.isInteger(b)||b<1||b>12)throw Error('bad-band');currentBand=b;render()}};
})();</script></body></html>'''


def main():
    output=Path('outputs');output.mkdir(exist_ok=True)
    data=build_data();(output/'GF8_ALL_1728_INVERSE_DESIGNS.json').write_text(json.dumps(data,indent=2)+'\n')
    (output/'GF8_FREQUENCY_EXPLORER.html').write_text(make_html(data))
    print(json.dumps({'cards':len(data['cards']),'resonances':len(data['fixed_plate_resonances']),
                      'model_envelope':data['status_counts'],'json_sha256':data['data_sha256']},indent=2))

if __name__=='__main__':main()
