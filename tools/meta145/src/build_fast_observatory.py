#!/usr/bin/env python3
"""Transform the frozen owner-private Turbo12 viewer into a paging+index version.

Input stays private; output is static offline HTML and is NOT a hosted SwarmChat build.
Refuses unrecognized source; keeps original file byte-for-byte intact.
"""
from __future__ import annotations
from pathlib import Path
import argparse,hashlib,re

ANCHOR_START='function filter(){'
ANCHOR_END='for(let i=1;i<=12;i++)'

FAST_JS=r'''// META145: CPU-microbenchmarkable, accessible 48-result window.
// DOM windowing is a rendering optimization, not loss of source entries.
const RESULT_PAGE_SIZE=48;
const indexText=new Map();const byHouse=new Map(),bySphere=new Map();
for(const n of all){
  indexText.set(n.id,[n.id,n.name,n.sphere,...Object.values(n.projects)].join(' ').toLowerCase());
  if(!byHouse.has(n.house))byHouse.set(n.house,[]);
  if(!bySphere.has(n.sphere))bySphere.set(n.sphere,[]);
  byHouse.get(n.house).push(n);bySphere.get(n.sphere).push(n);
}
let matched=[],rendered=0,activeButton=null;
const more=el('more');
function renderNext(){
  const container=el('entries'),fragment=document.createDocumentFragment();
  const stop=Math.min(matched.length,rendered+RESULT_PAGE_SIZE);
  for(let i=rendered;i<stop;i++){
    const n=matched[i],b=create('button');b.className='entry';b.type='button';
    b.dataset.coord=n.id;b.setAttribute('role','option');
    b.setAttribute('aria-current',String(n.id===selected));
    b.append(create('b',n.id));b.append(document.createTextNode(' '+n.name));
    b.append(create('small',n.sphere+' · '+(n.reading?'reading-index candidate':'source discovery')));
    if(n.id===selected)activeButton=b;
    b.addEventListener('click',()=>{
      if(activeButton&&activeButton!==b)activeButton.setAttribute('aria-current','false');
      activeButton=b;selected=n.id;b.setAttribute('aria-current','true');renderNode();
    });
    fragment.appendChild(b);
  }
  container.appendChild(fragment);rendered=stop;
  more.hidden=rendered>=matched.length;
  more.textContent=more.hidden?'All matching nodes displayed':`Show next ${Math.min(RESULT_PAGE_SIZE,matched.length-rendered)} of ${matched.length-rendered} remaining`;
  more.setAttribute('aria-label',`Show additional matching nodes; ${rendered} of ${matched.length} displayed`);
}
function filter(){
  const q=el('search').value.trim().toLowerCase(),h=el('house').value,s=el('sphere').value,
    r=el('reading').value,k=el('role').value;
  const pool=s?(bySphere.get(s)||[]):h?(byHouse.get(h)||[]):all;
  // Exact-coordinate fast path: verify its scope like every other match.
  const exact=/^h(?:0[1-9]|1[0-2])\\.s(?:0[1-9]|1[0-2])\\.n(?:0[1-9]|1[0-2])$/.test(q);
  const candidate=exact?((byId.get(q.toUpperCase())&&[byId.get(q.toUpperCase())])||[]):pool;
  matched=candidate.filter(n=>(!h||n.house===h)&&(!s||n.sphere===s)&&(!k||n.role===k)
    &&(!r||(r==='with'?n.reading:!n.reading))&&(!q||indexText.get(n.id).includes(q)));
  el('count').textContent=`${matched.length} / 1,728 source nodes • ${Math.min(RESULT_PAGE_SIZE,matched.length)} rendered initially • all available through paging`;
  el('entries').replaceChildren();rendered=0;activeButton=null;renderNext();
}
more.addEventListener('click',renderNext);
'''
# Python raw string regex has two backslashes from literal; use one JS escape in actual regex.
FAST_JS=FAST_JS.replace('\\\\.','\\.')

def transform(raw:str)->str:
    if raw.count(ANCHOR_START)!=1 or raw.count(ANCHOR_END)!=1:
        raise ValueError('Unexpected original viewer JS anchors')
    a=raw.index(ANCHOR_START);b=raw.index(ANCHOR_END,a)
    if b<=a or 'xs.slice(0,650)' not in raw[a:b]:raise ValueError('Baseline UI has changed')
    raw=raw[:a]+FAST_JS+raw[b:]
    marker='<div class="entries" id="entries" role="listbox" aria-label="Filtered knowledge nodes"></div>'
    if raw.count(marker)!=1:raise ValueError('Baseline UI markup changed')
    raw=raw.replace(marker,marker+'<button type="button" id="more" hidden style="margin-top:8px" aria-label="Load more knowledge nodes"></button>')
    raw=raw.replace('<title>Atlas Turbo ×12 · 1,728 / 144 / 12 / 1</title>',
                    '<title>Atlas META145 · Fast Work Observatory</title>')
    raw=raw.replace('ATLAS TURBO ×12 · CIVILIZATION CIRCUIT','ATLAS META145 · RESPONSIVE KNOWLEDGE CIRCUIT')
    raw=raw.replace('Search all 1,728 nodes','Fast search of all 1,728 nodes')
    return raw

def main():
    a=argparse.ArgumentParser();a.add_argument('--input',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--expected-sha')
    args=a.parse_args();base=args.input.read_bytes()
    if args.expected_sha and hashlib.sha256(base).hexdigest()!=args.expected_sha:
        raise ValueError('Baseline bytes do not match pinned SHA')
    out=transform(base.decode('utf-8'))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(out,encoding='utf-8')
    print(args.output, 'bytes:',args.output.stat().st_size,'SHA256:',hashlib.sha256(args.output.read_bytes()).hexdigest())
if __name__=='__main__':main()
