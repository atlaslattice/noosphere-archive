"""Generate a single-file offline UI from already approved local output, never network.
The resulting HTML embeds owner-private node data: DO NOT commit it to public Git.
"""
from pathlib import Path
import argparse,json,html
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True)
a=p.parse_args()
root=Path(a.input)
summary=json.loads((root/'single_build_summary.json').read_text())
benchmark=json.loads((root/'benchmark_lookup.json').read_text())
records=[json.loads(line) for line in (root/'node_upgrades_1728.jsonl').read_text().splitlines()]
paths=[json.loads(line) for line in (root/'sphere_pathways_144.jsonl').read_text().splitlines()]
mods=json.loads((root/'house_modules_12.json').read_text())
if (len(records),len(paths),len(mods))!=(1728,144,12):raise ValueError('FULL_SOURCE_BOUND_INPUT_REQUIRED')
data={'summary':summary,'benchmark':benchmark,'nodes':[{'id':n['coordinate'],'name':n['source_node_name'],'kind':n['source_role'],
      'house':n['house'],'sphere':n['sphere'],'operator':n['chapter_operator'],'metric':int(n['chapter']) if False else 0,
      'digest':n['digest_sha256'],'modules':[{'name':m['result']['module'],'passed':m['result']['pass']} for m in n['module_outputs']],
      'topics':n['module_outputs'][4]['result']['topic_candidates'],'glyph':n['module_outputs'][7]['result']['axg1'],'gf7':n['module_outputs'][7]['result']['gf7_positional_analogy'],
      'modeled_ratio':n['module_outputs'][0]['result']['modeled_frequency_ratio']} for n in records],
      'spheres':[{'id':s['sphere'],'name':s['source_name'],'role':s['role'],'terms':s['compiled_query_terms']} for s in paths],
      'houses':[{'id':m['house'],'name':m['source_house_name'],'module':m['executable_house_gate']} for m in mods]}
js=json.dumps(data,ensure_ascii=True,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
page=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Atlas 1728 Unified Workboard · offline source-typed build</title>
<style>
:root{font-family:system-ui,Segoe UI,Arial,sans-serif;color-scheme:dark;background:#091723;color:#f2f4f8}
*{box-sizing:border-box}body{margin:0;line-height:1.45}header{padding:28px 4%;background:linear-gradient(115deg,#102c3e,#243459);border-bottom:1px solid #587386}h1{margin:.2em 0;font-size:clamp(1.6rem,4vw,2.6rem)}main{padding:18px 4%;max-width:1600px;margin:auto}.overline{color:#b8ddd1;text-transform:uppercase;letter-spacing:.13em;font-size:.74rem;font-weight:700}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;margin:16px 0 24px}.kpis div,.panel{background:#142b3a;border:1px solid #395267;border-radius:12px;padding:15px}.kpis b{font-size:1.7rem;color:#b7f8dc}.kpis small{color:#a9c3cd;display:block}
.grid{display:grid;grid-template-columns:minmax(300px,2fr) minmax(300px,1fr);gap:14px}.panel h2{margin:0 0 .7em;font-size:1.12rem}label{font-weight:700;font-size:.88rem}input,select,button{font:inherit;border:1px solid #627f8f;background:#0c2431;color:#f3f8fc;border-radius:6px;padding:10px;max-width:100%;}input{width:100%;}button{cursor:pointer;background:#294d62}button:hover,button:focus-visible{outline:2px solid #b9f4dd}
.controls{display:grid;grid-template-columns:2fr 1fr 1fr;gap:7px;margin-bottom:10px}.nodeList{height:52vh;overflow:auto;border:1px solid #395267;border-radius:8px}.node{display:block;text-align:left;width:100%;border:0;border-bottom:1px solid #2d4657;border-radius:0;background:transparent;padding:9px 11px;color:#d9eef4}.node strong{color:#ddf7e3;margin-right:12px}.node[aria-current=true]{background:#2b5267}.muted{color:#afc8cf}.tag{display:inline-block;color:#e6f7ec;background:#315b58;border-radius:4px;padding:2px 6px;font-size:.72rem;margin:3px 4px 3px 0}.warn{color:#ffd69e}.detail{overflow-wrap:anywhere;min-height:52vh}#checks li{margin:5px 0;border-bottom:1px solid #284457;padding-bottom:5px}a{color:#c5f6d8}.status{font-weight:700;color:#acd9e4}small{font-size:.78rem}code{word-break:break-word}
@media(max-width:950px){.grid{grid-template-columns:1fr}.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.controls{grid-template-columns:1fr 1fr}.controls input{grid-column:1 / -1}.nodeList{height:38vh}.detail{min-height:0}}
</style></head><body><header><div class="overline">Atlas ONE / GF9 / Ariadne · owner-private offline Workboard</div>
<h1>Unified 1,728-node executable review build</h1><div>12 executable House modules · 144 compiled Sphere pathways · 1,728 source-specific node records · all local and reversible</div>
<p class="warn"><b>NOT HOSTED · NO AUTHENTICATED RESIDENTS · NO CANON OR MODEL-WEIGHT CHANGE.</b> Original source names are private. Lexical hits and OpenAlex candidates are not verified semantic equivalence.</p></header>
<main><div class="kpis" id="kpis"></div><div class="grid">
<section class="panel"><h2>Find a node upgrade</h2><div class="controls"><input id="query" type="search" placeholder="Search HSN, title, or chapter operator" aria-label="Search nodes"><select id="house" aria-label="House"><option value="">All 12 Houses</option></select><select id="sphere" aria-label="Sphere"><option value="">All 144 Spheres</option></select></div><div id="count" aria-live="polite" class="muted"></div><div class="nodeList" id="list"></div><p class="muted" id="more"></p><button type="button" id="next">Show next 48</button></section>
<section class="panel detail"><h2 id="title">Choose an HSN node</h2><div id="detail"></div><h3>12 module checks</h3><ol id="checks"></ol></section></div>
<section class="panel" style="margin-top:14px"><h2>Measurements and truth boundaries</h2><p id="bench"></p><p><b>The 1,728 per-node metrics are exact-lookup comparison counts.</b> They do not establish 1,728 separate empirical welfare or AI-cognition gains. This build compiles source-typed GF9 reference data; real graph, hosting and semantic performance still require independent acceptance tests.</p></section></main>
<script type="application/json" id="dataset">__DATA__</script><script>
'use strict';const x=JSON.parse(document.getElementById('dataset').textContent);const $=id=>document.getElementById(id);
const n=x.nodes, hs=x.houses, ss=x.spheres;const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
$('kpis').innerHTML=[['House modules',12],['Sphere pathways',144],['Node upgrades',1728],['Module checks',x.summary.module_node_checks]].map(([k,v])=>`<div><small>${k}</small><b>${v.toLocaleString()}</b></div>`).join('');
$('house').innerHTML+=[...hs].map(h=>`<option value="${h.id}">${esc(h.id)} · ${esc(h.name)}</option>`).join('');
$('sphere').innerHTML+=[...ss].map(h=>`<option value="${h.id}">${esc(h.id)} · ${esc(h.name)}</option>`).join('');
$('bench').textContent=`Local paired benchmark (${x.benchmark.passes} passes, ${x.benchmark.query_count_per_pass} exact requests/pass): linear median ${x.benchmark.linear_median_ms} ms; indexed median ${x.benchmark.indexed_median_ms} ms; ratio ${x.benchmark.median_speedup}×. This compares the compiled source index with a fair early-exit linear lookup, not current hosted Atlas or model reasoning.`;
let matches=n,shown=0,active='';const list=$('list');
function draw(reset=false){if(reset){shown=0;list.replaceChildren();}let count=0;const limit=Math.min(matches.length,shown+48);const frag=document.createDocumentFragment();while(shown<limit){const a=matches[shown++];const b=document.createElement('button');b.className='node';b.type='button';b.dataset.id=a.id;b.setAttribute('aria-current',String(a.id===active));const strong=document.createElement('strong');strong.textContent=a.id;b.append(strong,document.createTextNode(`${a.name} · ${a.operator}`));b.onclick=()=>select(a);frag.appendChild(b);}list.appendChild(frag);$('count').textContent=`${matches.length} of 1,728 nodes match`; $('more').textContent=`${shown} of ${matches.length} shown`; $('next').hidden=shown>=matches.length;}
function search(){const q=$('query').value.toLocaleLowerCase().trim(),h=$('house').value,s=$('sphere').value;matches=n.filter(a=>(!h||a.house===h)&&(!s||a.sphere===s)&&(!q||(`${a.id} ${a.name} ${a.operator} ${a.kind}`).toLocaleLowerCase().includes(q)));draw(true);}
function select(a){active=a.id;for(const b of list.children)b.setAttribute('aria-current',String(b.dataset.id===active));$('title').textContent=`${a.id} · ${a.name}`;const d=$('detail');d.replaceChildren();let x2=document.createElement('div');x2.innerHTML=`<span class="tag">${esc(a.kind)}</span><span class="tag">${esc(a.operator)}</span><p><b>Pathway:</b> ${esc(a.sphere)} · ${esc(a.house)}</p><p><b>GF9 nominal frequency ratio:</b> ${esc(a.modeled_ratio)} (simulated, not measured)</p><p><b>Historical OpenAlex candidates:</b> ${a.topics}; unreviewed, including alternate links</p><p><b>Reversible authored glyph:</b> <code>${esc(a.glyph)}</code></p><p><b>GF7 positional analogy:</b> <code>${esc(a.gf7)}</code> (not physics equivalence)</p><p class="muted"><b>Source-bound record digest:</b> <code>${esc(a.digest)}</code></p>`;d.append(x2);$('checks').replaceChildren(...a.modules.map(m=>{const l=document.createElement('li');l.textContent=`${m.name} — ${m.passed?'local check passed':'HELD'}`;return l;}));}
$('next').onclick=()=>draw();for(const id of ['query','house','sphere'])$(id).addEventListener('input',search);search();select(n[0]);
</script></body></html>'''
page=page.replace('__DATA__',js)
Path(a.output).write_text(page,encoding='utf8')
print('Created',a.output,'bytes',len(page.encode('utf8')))
