#!/usr/bin/env python3
"""Private static observatory: no external scripts, links, storage or messages."""
from pathlib import Path
import json, html, argparse

def build(output:Path,destination:Path):
    orders=[json.loads(x) for x in (output/'node_build_orders_1728.jsonl').read_text().splitlines()]
    stage=[json.loads(x) for x in (output/'macroturns_20_local.jsonl').read_text().splitlines()]
    sphere=json.loads((output/'sphere_modules_144.json').read_text())
    report=json.loads((output/'FINAL_RECEIPT.json').read_text())
    small={'nodes':[{'coordinate':x['coordinate'],'name':x['name'],'house':x['house'],'sphere':x['sphere'],
                     'kind':x['kind'],'reading':x['directHistoricalReadings'],'crossHouse':x['crossHouse'],
                     'workOrders':x['workOrders']} for x in orders],
            'spheres':[{'id':x['sphere'],'name':x['name'],'house':x['house'],'kind':x['kind']} for x in sphere],
            'stages':[{'i':x['stage'],'name':x['label'],'guard':x['guard'],'hash':x['receiptSha256']} for x in stage],
            'metrics':report['simulation'],'search':report['benchmark']}
    data=json.dumps(small,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    page='''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ATLAS · 1728 × 1728 Evolution Laboratory</title><style>
:root{font-family:system-ui,Segoe UI,sans-serif;color-scheme:dark;background:#0a1420;color:#ecf3f6;font-size:14px}*{box-sizing:border-box}body{margin:0}main{max-width:1400px;margin:auto;padding:20px}.hero{padding:24px;border:1px solid #356481;border-radius:16px;background:#102a3c}.hero h1{font-size:clamp(24px,4vw,36px);margin:0 0 8px}.muted{color:#b0cbdb}.stat{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}.stat article,.pane,.panel{border:1px solid #36536d;background:#112335;border-radius:10px;padding:14px}.stat strong{display:block;font-size:25px;color:#78dcc9}.stat small{color:#b7cfe0}.tools{display:flex;flex-wrap:wrap;gap:9px;margin:15px 0}input,select,button{font:inherit;background:#153348;border:1px solid #60839c;color:inherit;border-radius:7px;padding:10px}input{flex:1;min-width:190px}button{cursor:pointer}.layout{display:grid;grid-template-columns:1fr 1fr;gap:12px}.listing{max-height:60vh;overflow-y:auto}.entry{border:0;border-bottom:1px solid #284353;padding:10px 4px;cursor:pointer;background:transparent;width:100%;text-align:left;color:#e9f3f9}.entry:hover,.entry[aria-selected=true]{background:#1b3e50}.entry strong{color:#78dcc9}a{color:#78dcc9}.small{font-size:12px;color:#b0cbdb}.kind{display:inline-block;font-size:11px;border:1px solid #60839c;border-radius:5px;padding:2px 4px}.detail{max-height:62vh;overflow-y:auto}.detail h2{font-size:20px}.candidate{margin:6px 0;border-left:3px solid #7eceb2;padding-left:9px}.bar{height:12px;border-radius:5px;background:#215468;overflow:hidden;margin:4px 0 12px}.bar>span{display:block;height:12px;background:#74d8bd}.footer{margin:20px 0;font-size:12px;color:#abc6d7}@media(max-width:760px){.layout{grid-template-columns:1fr}.stat{grid-template-columns:repeat(2,1fr)}}
</style></head><body><main><header class="hero"><h1>ATLAS · Beast Evolution 1,728 × 1,728</h1><p>One immutable Ariadne source · 144 Sphere pathways · 12 House modules · 20 executable local review stages · one evidence-first build.</p><p class="muted">FICTIONAL 1,728-year analytical trajectories. No residents, hosted model wakes, semantic approvals, or actual elapsed years.</p></header>
<section class="stat"><article><strong>2,985,984</strong><small>Synthetic trajectories evaluated</small></article><article><strong>1,728</strong><small>Source-bound node orders</small></article><article><strong>144 / 12</strong><small>Spheres / Houses</small></article><article><strong>0</strong><small>Verified production actions</small></article></section>
<section class="panel"><h2>Synthetic matched-budget ablation</h2><p>Lower is better. These bars show mean error against a constructed numerical oracle, not real model correctness.</p><div id="bars"></div><p id="outcome" class="muted"></p></section>
<section class="tools"><input id="q" placeholder="Search coordinate or name" aria-label="Search HSN node"><select id="house" aria-label="House filter"><option value="">All 12 Houses</option></select><select id="sphere" aria-label="Sphere filter"><option value="">All 144 Spheres</option></select><select id="stage" aria-label="Stage"><option value="">All 20 local stages</option></select><button id="reset">Reset</button></section>
<section class="layout"><div class="pane"><h2>Node registry <span id="count" class="small"></span></h2><div class="listing" id="list"></div><button id="more">Show 48 more</button></div><div class="pane detail" id="detail" aria-live="polite"><p>Choose a node for source-link candidates and project-specific engineering handoffs.</p></div></section>
<p class="footer">All cross-House associations are lexical REVIEW CANDIDATES. Original source SHA-256 07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6. Offline interface, no network or private-mode intake. The simulation is not CANON or evidence of superior AI performance.</p></main><script id="atlas-data" type="application/json">__DATA__</script><script>
'use strict';const d=JSON.parse(document.getElementById('atlas-data').textContent),$=x=>document.getElementById(x);const state={q:'',house:'',sphere:'',limit:48};
function make(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=String(text);if(cls)e.className=cls;return e}
for(const h of [...new Set(d.nodes.map(n=>n.house))]){const o=make('option',h);o.value=h;$('house').append(o)}
for(const s of d.spheres){const o=make('option',s.id+' · '+s.name);o.value=s.id;$('sphere').append(o)}
for(const s of d.stages){const o=make('option',String(s.i).padStart(2,'0')+' · '+s.name);o.value=s.i;$('stage').append(o)}
function listing(){const hits=d.nodes.filter(n=>(!state.house||n.house===state.house)&&(!state.sphere||n.sphere===state.sphere)&&(!state.q||(n.coordinate+' '+n.name).toLowerCase().includes(state.q)));$('count').textContent=hits.length+' matching';$('list').replaceChildren();for(const n of hits.slice(0,state.limit)){const b=make('button');b.className='entry';b.type='button';b.setAttribute('aria-selected','false');b.append(make('strong',n.coordinate+' · '),make('span',n.name),make('small',n.sphere+' / '+n.kind,'small'));b.addEventListener('click',()=>show(n));$('list').append(b)}$('more').hidden=state.limit>=hits.length}
function show(n){$('detail').replaceChildren(make('h2',n.coordinate+' · '+n.name),make('p',n.sphere+' · '+n.kind));$('detail').append(make('p',n.reading?'Historical reading pointer exists (not semantic validation)':'No node-level historical reading pointer (research gap)'));
 const h=make('h3','Cross-House lexical suggestions — NOT VERIFIED');$('detail').append(h);for(const c of n.crossHouse){const z=make('div',c.target+' · lexical score '+c.lexicalScore+' · REVIEW REQUIRED','candidate');$('detail').append(z)}
 for(const [sys,order] of Object.entries(n.workOrders)){$('detail').append(make('h3',sys),make('p',order))}
 $('detail').append(make('p','Source-pinned candidate only. No host authority, automatic Work post, or story CANON.','small'))}
for(const [name,v] of Object.entries(d.metrics.MAE)){const row=make('div');row.append(make('strong',name+' · '+v.toFixed(5)));const bar=make('div',undefined,'bar');const fill=make('span');fill.style.width=(Math.min(1,v/.05)*100)+'%';bar.append(fill);row.append(bar);$('bars').append(row)}
$('outcome').textContent='Council vs solo: '+d.metrics.councilVsSolo.better.toLocaleString()+' better / '+d.metrics.councilVsSolo.worse.toLocaleString()+' worse. Council did not beat the isolated baseline overall.';
$('q').addEventListener('input',e=>{state.q=e.target.value.trim().toLowerCase();state.limit=48;listing()});for(const id of ['house','sphere'])$(id).addEventListener('change',e=>{state[id]=e.target.value;state.limit=48;listing()});$('more').addEventListener('click',()=>{state.limit+=48;listing()});$('reset').addEventListener('click',()=>{state.q='';state.house='';state.sphere='';state.limit=48;$('q').value='';$('house').value='';$('sphere').value='';listing()});
$('stage').addEventListener('change',e=>{if(!e.target.value)return;const s=d.stages[Number(e.target.value)-1];$('detail').replaceChildren(make('h2',s.i+' · '+s.name),make('p','Guard: '+s.guard),make('p','Receipt SHA-256: '+s.hash),make('p','LOCAL SOURCE-ONLY REVIEW STAGE. Does not prove an actual model turn or change host rights.'))});listing();
</script></body></html>'''.replace('__DATA__',data)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(page,encoding='utf-8')
    return {'nodes':len(orders),'spheres':len(sphere),'localStages':len(stage),'bytes':destination.stat().st_size}

if __name__=='__main__':
  p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--html',type=Path,required=True);a=p.parse_args()
  print(build(a.out,a.html))
