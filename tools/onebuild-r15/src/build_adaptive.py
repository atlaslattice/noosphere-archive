#!/usr/bin/env python3
"""Source-pinned, reversible R15 optimization of offline OneBuild viewer.

Avoid precomputing all 1728 detail profiles on startup; cache bounded working set.
Do not rewrite 8 stable DOM fields on every node navigation, only when edition changes.
Preserve eager search-index behavior (deferred indexing regressed first search).
No network, permissions or mode reads.
"""
from pathlib import Path
from hashlib import sha256
import argparse

EXPECTED_R14_SHA256='b750e56445e0dd05c7a5b6a1294e9df84bf01577128a586f938289b85bf9b3ac'
TARGET='const stableProfiles=new Map();\nfor(const n of all){'
END='// META145: CPU-microbenchmarkable, accessible 48-result window.'
INDEX='''  indexText.set(n.id,[n.id,n.name,n.sphere,...Object.values(n.projects)].join(' ').toLowerCase());'''
CALL='''&&(!r||(r==='with'?n.reading:!n.reading))&&(!q||indexText.get(n.id).includes(q)));'''
ORIGINAL_END='''// Read-only, local benchmark and same-HTML correctness hooks. These do NOT'''

STABLE_R15=r'''// R15: bounded on-demand detail profile cache; no 1728 profile warm-up.
// Cache content and search are completely WORK-safe authored source fields.
const stableProfiles=new Map(),MAX_STABLE_PROFILES=96;
const NO_READING='No directly indexed reading — discovery required';
const YES_READING='Direct reading index entry exists (NOT independently adjudicated)';
function getStableProfile(id){
  const old=stableProfiles.get(id);
  if(old)return old; // FIFO bounded cache: no mutation on hot hit
  const n=byId.get(id);if(!n)return null;
  const projects=new Map();
  for(const [key,value] of Object.entries(n.projects))projects.set(key,'Baseline: '+value);
  const p={title:n.id+' · '+n.name,scope:n.sphere+' · '+n.role,
    reading:n.reading?YES_READING:NO_READING,source:'Node source: '+n.source,projects};
  stableProfiles.set(id,p);
  if(stableProfiles.size>MAX_STABLE_PROFILES){
    stableProfiles.delete(stableProfiles.keys().next().value);
  }
  return p;
}
const stableEdition=meta.editions.map(e=>'This edition: '+e.implementation);
const stableProjectNotes=new Map([
  ['Iron Empire','Fiction concept only, author review required'],
  ...[...stableSections.keys()].filter(k=>k!=='Iron Empire').map(k=>[k,'Work design candidate, host rights and implementation not established'])
]);
for(const [p,x] of stableSections)x.note.textContent=stableProjectNotes.get(p);
let lastRenderedEdition=0;
function renderNode(){
  const n=getStableProfile(selected);if(!n)return;
  stableTitle.textContent=n.title;
  stableScope.textContent=n.scope;
  stableReading.textContent=n.reading;
  stableSource.textContent=n.source;
  if(lastRenderedEdition!==round){
    const edition=stableEdition[round-1];
    for(const x of stableSections.values())x.edition.textContent=edition;
    lastRenderedEdition=round;
  }
  for(const [p,line] of n.projects)stableSections.get(p).baseline.textContent=line;
}
'''


def transform(source: str) -> str:
    if source.count(TARGET)!=1 or source.count(END)!=1:raise ValueError('R14_SOURCE_STRUCTURE_MISSING')
    start=source.index(TARGET);stop=source.index(END,start)
    old=source[start:stop]
    if 'const stableEdition' not in old or 'function renderNode()' not in old:raise ValueError('R14_RENDERER_CONTRACT_CHANGED')
    if 'stableTitle.textContent=n.title;' not in old or 'x.baseline.textContent=line;' not in old:raise ValueError('R14_RENDERER_CONTRACT_CHANGED')
    out=source[:start]+STABLE_R15+source[stop:]
    if out.count(INDEX)!=1 or out.count(CALL)!=1:raise ValueError('R14_SEARCH_CONTRACT_CHANGED')
    # Keep indexed first-search responsiveness; lazy keyword indexing was tested
    # and rejected because it regressed first query (separate benchmark included).
    # Correctly label the retained R14 historical measurements.
    out=out.replace('>Inspect measured node latency</button>','>Inspect historical R14 node latency</button>')
    out=out.replace(' (local Chromium; not hosted)',' (historical R14 local Chromium; not R15 or hosted)')
    if out.count(ORIGINAL_END)!=1 or out.count('function getStableProfile(id)')!=1:raise ValueError('R15_OUTPUT_STRUCTURE_MISSING')
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    raw=a.input.read_bytes()
    if sha256(raw).hexdigest()!=EXPECTED_R14_SHA256:raise ValueError('R14_SOURCE_DIGEST_MISMATCH')
    v=transform(raw.decode('utf-8'))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(v,encoding='utf-8')
    print('source_sha256',sha256(raw).hexdigest());print('output_sha256',sha256(a.output.read_bytes()).hexdigest())
    print('size_change_bytes',len(a.output.read_bytes())-len(raw))

if __name__=='__main__':main()
