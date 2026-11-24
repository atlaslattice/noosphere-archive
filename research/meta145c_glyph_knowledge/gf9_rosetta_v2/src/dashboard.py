"""Build fully self-contained, owner-private GF9 finite experiment dashboard."""
from __future__ import annotations
from pathlib import Path
import json,html,hashlib
from .compiler import physical_3d_glyph
from .linguistics import PROFILES
from .protocol import CHAPTER_LABELS

def build(root:Path):
 out=root/'outputs'
 modules=json.loads((out/'MODULES_144_X_CHAPTERS_12_PRIVATE.json').read_text())
 blind=json.loads((out/'INDEPENDENT_BLIND_BENCHMARK.json').read_text())
 selections=json.loads((out/'POLICY_PROMOTION_REVIEW_144.json').read_text())
 state=json.loads((out/'CHECKPOINT_15000.json').read_text())
 view=[]
 for i,m in enumerate(modules):
  view.append({'id':m['id'],'name':m['name'],'house':m['house'],'role':m['role'],
   'nodes':m['node_names'],'node_ids':m['node_ids'],
   'initial':{'repetition':1,'decimals':3},'evolved':state['policies'][i],
   'guarded':selections[i]['selected'],
   'source_status':'OWNER_PINNED_V07_RESEARCH_ONLY'})
 payload={'modules':view,'chapters':CHAPTER_LABELS,
  'scripts':[{'code':p.code,'label':p.label,'structure':p.structure,'status':p.status} for p in PROFILES],
  'benchmark':blind['metrics'],'total_trials':state['next_index'],'accepted':state['counts']['accepted'],
  'rejected':state['counts']['rejected'],'trial_tip':state['head'],
  'meaning_claim':'NONE','hosted':False,'alien_contact':False}
 src=json.dumps(payload,ensure_ascii=True,separators=(',',':')).replace('</','<\\/')
 template='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"/><title>GF9-R2 · The Rosetta Lab</title><style>
:root{color-scheme:dark;--bg:#071422;--panel:#102538;--line:#35536b;--mint:#7ff2d2;--gold:#eac886;--ink:#edf5fa;--sub:#b9d0dd;--warn:#edc0a7}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 65% -20%,#1b5360,var(--bg) 60%);font:15px/1.53 system-ui,Arial;color:var(--ink)}main{max-width:1200px;margin:auto;padding:24px 16px 50px}
h1{font-size:clamp(27px,4vw,45px);letter-spacing:-.04em;margin:8px 0}.eyebrow{letter-spacing:.16em;text-transform:uppercase;color:var(--mint);font-size:12px;font-weight:700}.lead{color:var(--sub);max-width:850px;font-size:17px}h2{font-size:21px;margin:0 0 13px}h3{font-size:16px;margin:0 0 8px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:22px 0}.metric{padding:16px;background:var(--panel);border:1px solid var(--line);border-radius:12px}.metric b{display:block;font-size:29px}.metric small{color:var(--sub)}.section{background:var(--panel);border:1px solid var(--line);padding:18px;border-radius:14px;margin:20px 0}.layout{display:grid;grid-template-columns:1.05fr 1fr;gap:16px}.bar{background:#29465a;border-radius:12px;margin:6px 0 14px;overflow:hidden;height:24px}.bar span{height:100%;display:block;background:linear-gradient(90deg,#438a8b,var(--mint));color:#05131c;font-size:12px;text-align:right;padding-right:7px;font-weight:700;min-width:46px}.barrow{display:flex;justify-content:space-between;gap:10px}.barrow strong{font-size:13px}.barrow small{color:var(--sub)}label{display:block;color:var(--sub);font-size:13px;margin:8px 0 3px}input,select{width:100%;min-height:42px;padding:8px;border:1px solid #66859d;background:#081a2b;color:var(--ink);border-radius:8px;font:inherit}option{background:#102538}.small{font-size:12px;color:var(--sub)}.footer{font-size:12px;color:var(--sub)}code{background:#0b1d2c;padding:2px 5px;border-radius:5px;overflow-wrap:anywhere;color:var(--mint)}canvas{display:block;width:100%;height:auto;aspect-ratio:1.4/1;border:1px solid var(--line);border-radius:8px;background:#051c2b}ul{padding-left:20px}li{margin:6px 0}.gold{color:var(--gold)}.warn{color:var(--warn)}.stat{display:flex;flex-wrap:wrap;gap:8px}.pill{border:1px solid var(--line);border-radius:20px;padding:5px 9px;color:var(--sub);font-size:12px}.right{margin-left:auto}#desc{min-height:90px}.two{display:grid;grid-template-columns:1fr 1fr;gap:10px}.pre{padding:12px;background:#091b2a;border:1px solid var(--line);border-radius:8px;white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;color:#d5f2ef}@media(max-width:720px){.cards{grid-template-columns:repeat(2,1fr)}.layout,.two{grid-template-columns:1fr}main{padding:14px}.section{padding:12px}}
</style></head><body><main><div class="eyebrow">ATLAS • 12 Houses • 144 Spheres • 12 Lessons</div><h1>THE ROSETTA LAB</h1><p class="lead">A real finite GF9-R2 experiment inside an original Iron Empire first-contact curriculum. Physically calculated nodal glyphs, reversible notation, source-grade linguistics and cumulative synthetic communication tests. No alien contact, no trained GPT weights, no live service.</p>
<div class="cards"><div class="metric"><b id="trials">15,000</b><small>Recorded synthetic trials</small></div><div class="metric"><b id="accepted">—</b><small>Local policy changes accepted</small></div><div class="metric"><b>144 × 12</b><small>Original-source module/chapter slots</small></div><div class="metric"><b>18</b><small>Script research profiles, not translations</small></div></div>
<div class="section"><h2>Independent synthetic benchmark</h2><p class="small">Each method was tested on the same unseen deterministic channel scenarios. Bars show correctly recovered *and mathematically verified* packets; bandwidth differs between methods.</p><div id="bars"></div><div class="stat"><span class="pill" id="bw"></span><span class="pill">No codec/renderer is hosted</span><span class="pill">CRC32 detects errors, does not authenticate senders</span></div></div>
<div class="layout"><div class="section"><h2>Explore the authentic Ariadne 144</h2><label for="search">Filter by Sphere, House, or node name</label><input id="search" placeholder="Try plasma, music, or H01.S05"/><label for="sphere">Sphere</label><select id="sphere"></select><label for="chapter">One of twelve lesson chapters</label><select id="chapter"></select><div id="desc" aria-live="polite"></div><h3>Illustrative GF9-routed metadata</h3><div id="proof" class="pre"></div></div>
<div class="section"><h2>3D nodal field projection</h2><canvas id="nodal" width="600" height="425" role="img" aria-label="Mode-displacement projection with height mapped to luminous color"></canvas><p id="meshcaption" class="small"></p><div class="two"><div><h3>Original GF9 operator</h3><p id="operation"></p></div><div><h3>Codec policy</h3><p id="policy"></p></div></div></div></div>
<div class="section"><h2>Source boundaries</h2><div class="two"><p>Historical scripts: sign forms, transliterations, readings, languages, meanings and licenses are separate fields. Sumerian cuneiform and Egyptian hieroglyphs are study references, not automatic GF9 semantic mappings. Tolkien's languages and scripts are not reproduced here.</p><p>The nodal image is the mathematical field <code>sin(mπx) sin(nπy)</code> for a simply supported plate. It is not a measured Chladni photograph, atomic resonance signature, or validated interspecies language. The fiction uses this lab as its welcoming first-contact kit.</p></div><div class="footer">Exact Ariadne v0.7 original SHA256: 07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6 · All data local, zero network requests, no private conversation content · Commit rights unchanged</div></div>
<script id="payload" type="application/json">%%DATA%%</script><script>
(()=>{'use strict';const data=JSON.parse(document.getElementById('payload').textContent),mods=data.modules,byId=id=>document.getElementById(id);
byId('trials').textContent=data.total_trials.toLocaleString();byId('accepted').textContent=data.accepted.toLocaleString();
const labels={initial_minimal:'Minimal starting policy',fixed_robust:'Fixed threefold reference',evolved_15000:'Raw 15,000-trial evolution',guarded_selection:'Numerically guarded selection'};
const bars=byId('bars');for(const key of Object.keys(labels)){const metric=data.benchmark[key],pct=100*metric.passed/metric.total;
const row=document.createElement('div');row.className='barrow';const text=document.createElement('strong');text.textContent=labels[key];const m=document.createElement('small');m.textContent=`${metric.passed.toLocaleString()} / ${metric.total.toLocaleString()} (${pct.toFixed(2)}%)`;
row.append(text,m);bars.append(row);const div=document.createElement('div');div.className='bar';const span=document.createElement('span');span.style.width=Math.max(1,pct)+'%';span.textContent=pct.toFixed(1)+'%';div.append(span);bars.append(div)}
byId('bw').textContent='Guarded / fixed-threefold wire volume: '+(data.benchmark.guarded_selection.wire_bytes/data.benchmark.fixed_robust.wire_bytes).toFixed(2)+'×';
const q=byId('search'),s=byId('sphere'),c=byId('chapter');for(let i=0;i<12;i++){const op=document.createElement('option');op.value=i;op.textContent=`${String(i+1).padStart(2,'0')} · ${data.chapters[i]}`;c.append(op)};
function refill(){const t=q.value.toLowerCase();const chosen=s.value;let matches=mods.filter(m=>(m.id+' '+m.name+' '+m.house+' '+m.nodes.join(' ')).toLowerCase().includes(t));s.textContent='';for(const m of matches){let op=document.createElement('option');op.value=m.id;op.textContent=m.id+' · '+m.name;s.append(op)}if(matches.some(m=>m.id===chosen))s.value=chosen;render()}
function render(){const m=mods.find(x=>x.id===s.value);if(!m){byId('desc').textContent='No matching Sphere';return}let ch=+c.value;const idx=mods.findIndex(x=>x.id===m.id),modeM=1+idx%3,modeN=1+Math.floor(idx/12)%3;
byId('desc').textContent=`${m.house} • ${m.role} • Node ${m.node_ids[ch]} — ${m.nodes[ch]}`;
const ex=data.scripts[(idx+ch)%data.scripts.length];const factor=(1.015+((idx*3+ch*11)%17)/100),op=['thickness','width','height'][ch%3];
const core=modeM*modeM+modeN*modeN,changed=ch%3===0?factor*core:(ch%3===1?(modeM/factor)**2+modeN**2:modeM**2+(modeN/factor)**2);const ratio=changed/core;
const r=ch%3===0?factor:ratio;
byId('proof').textContent=JSON.stringify({HSN:m.node_ids[ch],source_edition:'Ariadne v0.7',challenge:data.chapters[ch],script_metadata:ex.code+' · '+ex.structure,translation:'NONE',mode:[modeM,modeN],changed_parameter:op,ratio:factor.toFixed(4),predicted_frequency_ratio:r.toFixed(8),physics:'SSSS plate, modeled only',semantic_status:'UNREVIEWED'},null,2);
byId('operation').textContent=['CONSENT','COUNT','RATIO','ROTATE','CLOCK','ELEMENT','LATTICE','RESONANCE','HOLD','TRANSFORM','SONIFY','TEACH'][ch]+' — testable model exchange, no semantic admission.';
byId('policy').textContent=`Initial ${m.initial.repetition}×/${m.initial.decimals} dp; evolved ${m.evolved.repetition}×/${m.evolved.decimals} dp; guarded ${m.guarded.repetition}×/${m.guarded.decimals} dp.`;
byId('meshcaption').textContent=`Mode (${modeM},${modeN}), nodal contour proxy; normalized displacement. The source physical model and observed reality remain distinct.`;
const cv=byId('nodal');const ctx=cv.getContext('2d');ctx.fillStyle='#06192c';ctx.fillRect(0,0,cv.width,cv.height);const w=cv.width,h=cv.height;
for(let j=0;j<120;j++){for(let i=0;i<170;i++){const x=i/169,y=j/119,v=Math.sin(modeM*Math.PI*x)*Math.sin(modeN*Math.PI*y),a=Math.abs(v),px=i*w/170,py=j*h/120;ctx.fillStyle=(a<0.05)?'#f0d28f':(v>=0?`rgba(48,${Math.floor(120+120*a)},194,1)`:`rgba(${Math.floor(80+140*a)},67,132,1)`);ctx.fillRect(px,py,w/170+1,h/120+1)}}
ctx.strokeStyle='rgba(255,255,255,.25)';ctx.strokeRect(1,1,w-2,h-2);
}
q.addEventListener('input',refill);s.addEventListener('change',render);c.addEventListener('change',render);refill();
})();</script></main></body></html>'''
 final=template.replace('%%DATA%%',src)
 path=out/'GF9_ROSETTA_EXPLORER_PRIVATE.html';path.write_text(final,encoding='utf-8')
 return {'path':str(path),'size_bytes':path.stat().st_size,'html_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'modules':len(view),'chapters':12,'source_private':True}
if __name__=='__main__':
 p=Path(__file__).resolve().parents[1];print(json.dumps(build(p),indent=2))
