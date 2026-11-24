#!/usr/bin/env python3
"""Independent full 144×1728 matrix, chain and meta145 integrity verifier."""
from __future__ import annotations
import argparse,csv,gzip,hashlib,json,re
from collections import Counter
from pathlib import Path

BASE_HEAD='b5be629b260719f97cd16c5c795b4baf5a1838855b99f94b3725c578b249283a'
REGISTRY='07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6'
SCOPE=('SwarmChat','Atlas','Ariadne','Iron Empire')
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sha(b):return hashlib.sha256(b).hexdigest()
def d(x):return sha(canon(x).encode('utf-8'))
def check(v,msg):
 if not v:raise ValueError('HOLD_'+msg)

def verify(source_root:Path,output:Path,benchmark:Path,fast_viewer:Path,ui_sweep:Path|None=None)->dict:
 reg_bytes=(source_root/'input/ariadne-atlas-v07.json').read_bytes()
 check(sha(reg_bytes)==REGISTRY,'SOURCE_SHA')
 reg=json.loads(reg_bytes);all_spheres=list(reg['spheres'].keys());all_nodes=list(reg['nodes'].keys())
 check(len(all_spheres)==144 and len(all_nodes)==1728,'GEOMETRY')
 meta=json.loads((output/'META145_MEASURED_BUILD.json').read_text())
 digest_meta=meta.pop('meta145_receipt_hash',None)
 check(digest_meta==d(meta),'META_HASH');meta['meta145_receipt_hash']=digest_meta
 check(meta['ariadne_original_digest']==REGISTRY and meta['previous_12_edition_build_head']==BASE_HEAD,'SOURCE_BINDING')
 with (output/'SPHERE144_RESPONSIVENESS_REVIEWS.jsonl').open(encoding='utf-8') as f:rows=[json.loads(line) for line in f]
 check(len(rows)==144,'SPHERE_REVIEW_CARDINALITY');head=BASE_HEAD;lex={}
 for i,row in enumerate(rows):
  expected=all_spheres[i];check(row['sphere_id']==expected and row['ordinal']==i+1,'SPHERE_REVIEW_ORDER')
  check(row['first_node']==reg['spheres'][expected]['children'][0],'FIRST_NODE_SOURCE')
  check(row['first_node_digest']==reg['nodes'][row['first_node']]['source_record_sha256'],'NODE_DIGEST')
  check(set(row['candidate_changes'])==set(SCOPE),'FOUR_PROJECTS')
  check(row['coverage']['reviewed_coordinates']==1728,'PERSPECTIVE_COVERAGE')
  check([row['coverage'][k] for k in ['same_sphere','same_house','cross_house']]==[12,132,1584],'RELATION_COVERAGE')
  check(row['coverage']['source_semantic_approvals']==0,'SEMANTIC_PROMOTION')
  expected_hash=row.pop('receipt_digest',None);expected_head=row.pop('chain_head',None)
  check(expected_hash==d(row),'RECEIPT_SHA');head=sha((head+expected_hash).encode())
  check(expected_head==head,'RECEIPT_CHAIN')
  lex[expected]=row['coverage']['unreviewed_lexical_flags'];row['receipt_digest']=expected_hash;row['chain_head']=expected_head
 check(meta['review_receipt_chain_head']==head,'TERMINAL_REVIEW_HEAD')
 check(meta['review_rows_sha256']==sha((output/'SPHERE144_RESPONSIVENESS_REVIEWS.jsonl').read_bytes()),'REVIEW_FILE_PIN')
 # Verify original matrix projection, not just totals/length; do not materialize 248832 in memory.
 actual=Counter();n=0
 with gzip.open(output/'SPHERE144_PAIR_REVIEWS_248832.csv.gz','rt',encoding='utf-8',newline='') as f:
  rd=csv.DictReader(f)
  check(rd.fieldnames==['perspective','node','relation','shared_terms','lexical_flag','source_role','semantic_evidence'],'MATRIX_HEADER')
  for x in rd:
   si,ni=divmod(n,1728)
   check(si<144,'MATRIX_TOO_LONG')
   sid=all_spheres[si];nid=all_nodes[ni]
   check(x['perspective']==sid and x['node']==nid,'MATRIX_ORDER')
   check(x['source_role']==reg['nodes'][nid]['kind'],'MATRIX_SOURCE_ROLE')
   rel='SAME_SPHERE' if nid[:7]==sid else 'SAME_HOUSE' if nid[:3]==sid[:3] else 'CROSS_HOUSE'
   check(x['relation']==rel,'MATRIX_SCOPE')
   check(x['semantic_evidence']=='NOT_ADJUDICATED','MATRIX_APPROVAL')
   check(x['lexical_flag'] in ('0','1'),'LEXICAL_FLAG')
   actual[sid]+=int(x['lexical_flag']);n+=1
 check(n==248832,'MATRIX_TRUNCATED')
 check(all(actual[s]==lex[s] for s in all_spheres),'LEXICAL_DRIFT')
 check(sha((output/'SPHERE144_PAIR_REVIEWS_248832.csv.gz').read_bytes())==meta['pair_review_matrix_sha256'],'MATRIX_PIN')
 houses=json.loads((output/'HOUSE12_FAST_PATH_SYNTHESIS.json').read_text())
 check(len(houses)==12 and len({h['house'] for h in houses})==12,'HOUSE_COUNT')
 for h in houses:
  r=[x for x in rows if x['house_id']==h['house']]
  check(len(r)==12 and len(h['source_review_receipts'])==12,'HOUSE_SPHERES')
  check(h['source_review_receipts']==[x['receipt_digest'] for x in r],'HOUSE_REVISION_LINK')
 check(sha(benchmark.read_bytes())==meta['benchmark_sha256'],'BENCHMARK_PIN')
 check(sha(fast_viewer.read_bytes())==meta['optimized_viewer_sha256'],'VIEWER_PIN')
 benchmarkdata=json.loads(benchmark.read_text())
 check(benchmarkdata['pages']['optimized']['sha256']==meta['optimized_viewer_sha256'],'BENCHMARK_VIEWER')
 check(meta['counts']['sphere_node_pair_evaluations']==n and meta['counts']['sphere_perspectives_computed']==144,'META_COUNTS')
 check(meta['counts']['hosted_model_turns']==0 and meta['counts']['semantic_relations_accepted']==0 and not meta['hosted_latency_measured'],'NONCLAIMS')
 if ui_sweep:
  sweep=json.loads(ui_sweep.read_text())
  check(sweep['spheres_checked']==144,'UI_SWEEP_COUNT')
  check(all(x['sourceValid'] and x['found']==12 for x in sweep['variants']['optimized']['rows']),'UI_SWEEP_RESULTS')
  check(sweep['variants']['optimized']['viewer_sha256']==meta['optimized_viewer_sha256'],'UI_SWEEP_SOURCE')
 return {'schema':'atlas.meta145.independent-audit/v1','status':'ALL_SOURCE_ONLY_AUDITS_PASS',
         'sphere_perspectives':len(rows),'structural_pair_evaluations':n,'house_followups':12,
         'node_lookup_compatibility':1728,'local_browser_sphere_checks':144 if ui_sweep else 0,
         'receipt_chain_head':head,'meta145_hash':meta['meta145_receipt_hash'],
         'hosted_performance':'UNVERIFIED','releaseAuthority':'NONE'}

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--turbo-root',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
 a.add_argument('--benchmark',type=Path,required=True);a.add_argument('--fast-viewer',type=Path,required=True);a.add_argument('--ui-sweep',type=Path);args=a.parse_args()
 print(json.dumps(verify(args.turbo_root,args.out,args.benchmark,args.fast_viewer,args.ui_sweep),indent=2))
