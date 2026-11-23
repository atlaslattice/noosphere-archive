#!/usr/bin/env python3
"""Build completely offline, static interactive review desk for synthetic cascade."""
from pathlib import Path
import json
import html
root=Path(__file__).resolve().parents[1]
s=json.loads((root/'dist/summary.json').read_text())
entries=json.loads((root/'dist/stage1100.json').read_text())['ledger']
payload=json.dumps({'summary':s,'entries':entries},ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e')
template=r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Atlas Cascade 1100 · Offline Evidence Observatory</title>
<style>
:root{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#e3e9f4;background:#0a1327}
*{box-sizing:border-box}body{margin:0}main{max-width:1160px;margin:auto;padding:32px 22px 60px}
header{display:flex;gap:18px;justify-content:space-between;align-items:flex-start;margin-bottom:26px;flex-wrap:wrap}
.kicker{font-size:11px;letter-spacing:.18em;font-weight:800;color:#8fb8ec;text-transform:uppercase}
h1{font-weight:800;font-size:clamp(30px,5vw,49px);letter-spacing:-.045em;line-height:1.07;margin:8px 0}
.sub{color:#abbbd6;font-size:14px;line-height:1.6;max-width:650px}
.badge{border:1px solid #355172;background:#14233e;border-radius:50px;padding:8px 12px;color:#bdcff0;font-size:11px;font-weight:700}
.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:22px}
.card,.panel{background:linear-gradient(180deg,#142443,#101d36);border:1px solid #293d59;border-radius:14px;padding:18px}
.num{font-size:30px;font-weight:800;letter-spacing:-.035em;color:white;font-variant-numeric:tabular-nums}
.lbl{font-size:12px;color:#9bb0d2;margin-top:4px}.panel{margin-bottom:16px}
.panel h2{font-size:17px;margin:0 0 12px}.panel small,.note{color:#91a6c7;line-height:1.5}
.stagegrid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.stage{padding:14px;border-radius:10px;background:#0c1930;border:1px solid #293e61}
.stage b{font-size:20px}.stage code{display:block;word-break:break-all;font-size:11px;color:#95b6e4;margin-top:7px}
svg{width:100%;height:auto;display:block} .legend{display:flex;gap:18px;font-size:12px;color:#abc0df;flex-wrap:wrap;margin-top:9px}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px}
input,select,button{background:#0c1b36;color:#e5efff;border:1px solid #3a5378;border-radius:8px;padding:9px 11px;font:inherit}
button{cursor:pointer}button:hover{border-color:#81b7fc} .controls{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0 13px}
input{min-width:240px;flex:1}select{min-width:175px}table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;color:#a8c0e4;border-bottom:1px solid #304463;padding:10px 7px}td{border-bottom:1px solid #223451;padding:9px 7px;color:#dbe5f8}
tr:hover td{background:#182b4a}.code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:11px}
.st{color:#8be2c0}.hd{color:#e8a5b4}.tablewrap{overflow:auto}
.pager{display:flex;justify-content:space-between;align-items:center;margin-top:14px;gap:10px}
footer{font-size:12px;color:#92a4c3;margin-top:22px;line-height:1.6}
@media(max-width:700px){.cards{grid-template-columns:repeat(2,1fr)}.stagegrid{grid-template-columns:1fr}main{padding:22px 14px}}
</style></head>
<body><main>
<header><div><div class="kicker">Atlas · Work-only synthetic engineering</div><h1>Evolution Observatory<br>100 → 1,000</h1><div class="sub">Exactly 1,100 sequential offline state trials. Every descendant inherits the previous trial's Work fixture state and hash-chain head. No agent wakes, actual room messages, private modes or production authorization.</div></div><span class="badge">TESTED LOCAL · NOT DEPLOYED</span></header>
<section class="cards" id="metrics"></section>
<section class="panel"><h2>Two-stage checkpoint continuity</h2><div class="stagegrid"><div class="stage"><div class="kicker">Stage A · First 100</div><b>100 dependent local trials</b><code id="s1"></code></div><div class="stage"><div class="kicker">Stage B · 1,000 descendants</div><b>1,100 total trials</b><code id="s2"></code></div></div><p class="note">Hash links provide local integrity and replayability, not independently signed provenance. A full chain can be fabricated by a caller; strict deterministic replay and host attestation remain separate checks.</p></section>
<section class="panel"><h2>Cumulative outcomes by trial</h2><svg viewBox="0 0 1010 275" role="img" aria-label="Cumulative synthetic local effects and denied operations" id="chart"></svg><div class="legend"><span><span class="dot" style="background:#70e4bb"></span>Local applied / observed / deduplicated</span><span><span class="dot" style="background:#f5ac80"></span>Safe denied (no external effect)</span><span><span class="dot" style="background:#8ab0f5"></span>Checkpoint at 100</span></div></section>
<section class="panel"><h2>One hundred then one thousand: complete receipt explorer</h2><p class="note">Every displayed row is a synthetic source-only fixture; click a row's digest to copy it. A PASS means a local transition or controlled refusal, not a hosted test result.</p><div class="controls"><input id="q" placeholder="Filter by case #, HSN coordinate, action, outcome or SHA prefix" aria-label="Filter receipts"><select id="phase" aria-label="Phase"><option value="">Both phases</option><option value="PRIMARY_100">First 100</option><option value="DESCENDANTS_1000">Next 1,000</option></select><select id="outcome" aria-label="Outcome"><option value="">All outcomes</option></select><button id="reset">Reset</button></div><div class="tablewrap"><table><thead><tr><th>#</th><th>Phase</th><th>HSN address</th><th>Action</th><th>Outcome</th><th>Receipt SHA256</th></tr></thead><tbody id="rows"></tbody></table></div><div class="pager"><span id="counter" class="note"></span><div><button id="prev">Previous</button> <button id="next">Next</button></div></div></section>
<section class="panel"><h2>Scope and remaining work</h2><div class="sub">This run exercised 110 synthetic Work POST fixtures, 55 CAS revisions, 55 deduplicated replays, 55 revocations, and 55 new-grant fixtures. A total of 605 negative operations were denied safely. All 12 Houses received structural HSN coverage, but 628 of 1,728 addresses remain untouched, none of the candidates is a semantic proof, and 14 voluntary non-Work opportunities were never performed. Real host IAM, source rights, receiver consent, delivered callbacks, independent model activation, 3D UI, rollback, deployment, and CANON are separate gates.</div></section>
<footer>Source: offline Node simulation with independent Python ledger audit. 66/66 Node tests passed both normal and --jitless; 15/15 Python mutation tests passed. NO live host or independent peer claims. Designed for audit, not for release authorization.</footer>
</main><script type="application/json" id="data">__DATA__</script><script>
const data=JSON.parse(document.getElementById('data').textContent), s=data.summary, entries=data.entries;
const metric=[['Trials',s.trials],['Regression rechecks',s.regressionEvaluations.toLocaleString()],['HSN addresses',s.uniqueStructuralHsnAddresses+' / 1,728'],['Hosted model wakes',s.hostModelWakeCalls]];
document.getElementById('metrics').innerHTML=metric.map(([k,v])=>`<article class="card"><div class="num">${v}</div><div class="lbl">${k}</div></article>`).join('');
document.getElementById('s1').textContent=s.phase100Head;document.getElementById('s2').textContent=s.terminalHead;
const svg=document.getElementById('chart'),NS='http://www.w3.org/2000/svg';let good=0,hold=0;const pg=[],ph=[];
entries.forEach(e=>{if(e.outcome==='HOLD_NO_EXTERNAL_EFFECT')hold++;else good++;pg.push(good);ph.push(hold)});
function el(name,attrs){let n=document.createElementNS(NS,name);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));svg.appendChild(n);return n}
for(let v=0;v<=1100;v+=275){const y=242-v/1100*210;el('line',{x1:54,x2:987,y1:y,y2:y,stroke:'#34496c','stroke-width':'.8'});let t=el('text',{x:8,y:y+4,fill:'#96add0','font-size':12});t.textContent=v.toLocaleString()}
for(let i of [1,100,300,600,900,1100]){const x=54+(i-1)/1099*933;let t=el('text',{x:x-13,y:268,fill:'#93aad0','font-size':12});t.textContent=i}
const line=(values,color)=>{const points=values.map((v,i)=>[54+i/1099*933,242-v/1100*210]);el('polyline',{fill:'none',stroke:color,'stroke-width':3,'stroke-linecap':'round',points:points.map(([x,y])=>x.toFixed(2)+','+y.toFixed(2)).join(' ')})};
line(pg,'#70e4bb');line(ph,'#f5ac80');const mark=54+99/1099*933;el('line',{x1:mark,x2:mark,y1:21,y2:242,stroke:'#8ab0f5','stroke-dasharray':'5 6','stroke-width':1.5});
const output=[...new Set(entries.map(e=>e.outcome))].sort();const sel=document.getElementById('outcome');sel.innerHTML='<option value="">All outcomes</option>';output.forEach(x=>{const o=document.createElement('option');o.value=x;o.textContent=x;sel.appendChild(o)});
let filtered=entries,page=0;const per=35;const label=val=>val.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
function render(){const q=document.getElementById('q').value.toLowerCase(),phase=document.getElementById('phase').value,out=document.getElementById('outcome').value;filtered=entries.filter(e=>(!phase||e.phase===phase)&&(!out||e.outcome===out)&&(!q||[String(e.index),e.coordinate,e.kind,e.outcome,e.hash].some(x=>x.toLowerCase().includes(q))));page=Math.min(page,Math.max(0,Math.ceil(filtered.length/per)-1));const selected=filtered.slice(page*per,page*per+per);document.getElementById('rows').innerHTML=selected.map(e=>`<tr><td>${e.index}</td><td>${e.phase==='PRIMARY_100'?'Primary':'Descendant'}</td><td class="code">${e.coordinate}</td><td class="code">${e.kind}</td><td class="${e.outcome==='HOLD_NO_EXTERNAL_EFFECT'?'hd':'st'}">${e.outcome}</td><td class="code"><button class="copy" data-sha="${e.hash}" title="Copy full SHA">${e.hash.slice(0,15)}…</button></td></tr>`).join('');document.getElementById('counter').textContent=`${filtered.length.toLocaleString()} matching receipts · page ${page+1}/${Math.max(1,Math.ceil(filtered.length/per))}`;document.getElementById('prev').disabled=page<=0;document.getElementById('next').disabled=(page+1)*per>=filtered.length;document.querySelectorAll('.copy').forEach(b=>b.addEventListener('click',()=>{if(navigator.clipboard?.writeText)navigator.clipboard.writeText(b.dataset.sha).catch(()=>{});else prompt('Receipt SHA256',b.dataset.sha)}))}
for(const id of ['q','phase','outcome'])document.getElementById(id).addEventListener(id==='q'?'input':'change',()=>{page=0;render()});document.getElementById('reset').addEventListener('click',()=>{for(const id of ['q','phase','outcome'])document.getElementById(id).value='';page=0;render()});document.getElementById('prev').addEventListener('click',()=>{page--;render()});document.getElementById('next').addEventListener('click',()=>{page++;render()});render();
</script></body></html>'''
text=template.replace('__DATA__',payload)
(root/'dist/cascade_review_desk.html').write_text(text,encoding='utf-8')
print('wrote', root/'dist/cascade_review_desk.html',len(text),'bytes')
