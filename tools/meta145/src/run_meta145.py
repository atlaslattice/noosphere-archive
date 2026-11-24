#!/usr/bin/env python3
"""Run 144 source-pinned sphere→1728 structure reviews, then one measured meta-build.

A 'sphere perspective' is deterministic source/structure enumeration with an
engineering hypothesis; NOT a human expert or independently running model.
Never posts, invokes network, grants authority, uses leisure bodies or deploys.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,io,json,re
from collections import Counter
from pathlib import Path

REGISTRY='07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6'
BASE_HEAD='b5be629b260719f97cd16c5c795b4baf5a1838855b99f94b3725c578b249283a'
EXPECTED_MATRIX='7ec6dda566c0937e1422a6c93ec7f37821cfd38961fa1294885060acaad18d3c'
SHA=re.compile(r'^[0-9a-f]{64}$')

def digest(raw):return hashlib.sha256(raw).hexdigest()
def compact(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def jd(obj):return digest(compact(obj).encode('utf-8'))
def ensure(b,why):
 if not b:raise ValueError(why)

def write(path,obj):
 path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# Performance perspectives are labels on a review, not inferred validated HSN edges.
SYSTEMS=('SwarmChat','Atlas','Ariadne','Iron Empire')
def make_four_proposals(sid,sphere_name,node_name,role,source_pin):
 return {
  'SwarmChat':{'candidate':f'Instrument one opted-in Work-room message about {sphere_name}; distinguish stored from delivered and model-activated',
   'negative_test':'No platform receiver receipt => HELD_ACTIVATION, even with matching broker seq',
   'primary_key':sid,'status':'PROPOSED_HOST_NOT_TOUCHED'},
  'Atlas':{'candidate':f'Use a bounded, preindexed source navigation window for {sphere_name}; keep all 12 first-party sphere nodes discoverable',
   'negative_test':'Unbounded DOM result growth or truncated 1728-node search => FAIL',
   'primary_key':sid,'status':'PROPOSED_SPHERE_APPLICATION_NOT_HOSTED'},
  'Ariadne':{'candidate':f'Bind {sphere_name} to source edition and digest, preserve type and original scope for {node_name}',
   'negative_test':'Same label or numeric address alone never creates SAME_AS or CANON',
   'primary_key':sid,'source_registry':source_pin,'role':role,'status':'PROPOSED_SEMANTIC_REVIEW'},
  'Iron Empire':{'candidate':f'Optional six-film storyworld review through {sphere_name}; test narrative consequences and retain contradictory ideas',
   'negative_test':'No import of private Imagine, no scientific validation, no automatic lore ratification',
   'primary_key':sid,'status':'AUTHOR_REVIEW_NOT_CANON'}
 }

def scan(root:Path,dest:Path,benchmark:Path,fast_html:Path):
 source_dir=root/'input'; out=root/'output'
 reg_file=source_dir/'ariadne-atlas-v07.json'
 reg_bytes=reg_file.read_bytes();ensure(digest(reg_bytes)==REGISTRY,'REGISTRY_DIGEST_MISMATCH')
 reg=json.loads(reg_bytes)
 spheres=reg['spheres'];nodes=reg['nodes'];houses=reg['houses']
 ensure(len(spheres)==144 and len(nodes)==1728 and len(houses)==12,'REGISTRY_GEOMETRY')
 baseline=json.loads((out/'ONE_INTEGRATED_BUILD.json').read_text())
 ensure(baseline['final_build_hash']==BASE_HEAD,'BASE_BUILD_HEAD_MISMATCH')
 base_csv=source_dir/'base_sphere_node_matrix_248832.csv'
 ensure(digest(base_csv.read_bytes())==EXPECTED_MATRIX,'MATRIX_DIGEST_MISMATCH')
 bench=json.loads(benchmark.read_text());ensure('optimized' in bench['pages'] and 'baseline' in bench['pages'],'PAIRED_BENCHMARK_REQUIRED')
 ensure(bench['pages']['optimized']['sha256']==digest(fast_html.read_bytes()),'FAST_VIEWER_MISMATCH')
 per_sphere={sid:Counter() for sid in spheres}
 perspective_ids=list(spheres.keys());node_ids=list(nodes.keys());isource={n:i for i,n in enumerate(node_ids)}
 ensure(len(set(perspective_ids))==144 and len(set(node_ids))==1728,'DUPLICATE_SPHERE_OR_NODE')
 dest.mkdir(parents=True,exist_ok=True)
 matfile=dest/'SPHERE144_PAIR_REVIEWS_248832.csv.gz'
 expected=['sphere_perspective','node_target','perspective_lens','structure','shared_domain_terms','lexical_candidate','semantic_status']
 n=0
 # Preserve original one-Sphere-per-block source walk and compute a fresh record/checkpoint.
 with base_csv.open(encoding='utf-8',newline='') as f, matfile.open('wb') as raw:
  rd=csv.DictReader(f);ensure(rd.fieldnames==expected,'MATRIX_SCHEMA')
  with gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0,compresslevel=5) as z:
   with io.TextIOWrapper(z,encoding='utf-8',newline='\n') as w:
    writer=csv.writer(w,lineterminator='\n')
    writer.writerow(['perspective','node','relation','shared_terms','lexical_flag','source_role','semantic_evidence'])
    for row in rd:
     si,ni=divmod(n,1728)
     sid=perspective_ids[si];nid=node_ids[ni]
     ensure(row['sphere_perspective']==sid and row['node_target']==nid,'ROW_ORDER')
     rel=row['structure'];ensure(rel in ('SAME_SPHERE','SAME_HOUSE','CROSS_HOUSE'),'RELATION')
     ensure((nid[:7]==sid)==(rel=='SAME_SPHERE'),'RELATION_SCOPE')
     ensure(row['semantic_status']=='NOT_ADJUDICATED','SOURCE_SEMANTIC_APPROVAL_UNEXPECTED')
     lexical=0 if row['lexical_candidate']=='NONE' else 1
     per_sphere[sid][rel]+=1;per_sphere[sid]['lexical']+=lexical
     writer.writerow([sid,nid,rel,row['shared_domain_terms'],lexical,nodes[nid]['kind'],'NOT_ADJUDICATED'])
     n+=1
 ensure(n==248832,'CIRCUIT_NOT_COMPLETE')
 receipt_head=BASE_HEAD;reviews=[]
 reviewfile=dest/'SPHERE144_RESPONSIVENESS_REVIEWS.jsonl'
 with reviewfile.open('w',encoding='utf-8',newline='\n') as w:
  for idx,sid in enumerate(perspective_ids,1):
   sph=spheres[sid];hid=sph['parent'];role='DOMAIN' if int(sid[5:7])<=7 else 'EPISTEMIC_META'
   first=nodes[sph['children'][0]]
   c=per_sphere[sid];ensure(c['SAME_SPHERE']==12 and c['SAME_HOUSE']==132 and c['CROSS_HOUSE']==1584,'SPHERE_COVERAGE')
   # Distinct, source grounded topic and controllable synthetic UI input; no invented performance measurement per sphere.
   row={'ordinal':idx,'sphere_id':sid,'sphere_name':sph['name'],'house_id':hid,'house_name':houses[hid]['name'],
        'method_or_domain_role':role,'source_edition':'ariadne-reader/v0.7','source_registry_digest':REGISTRY,
        'first_node':first['id'],'first_node_title':first['name'],'first_node_digest':first['source_record_sha256'],
        'coverage':{'reviewed_coordinates':1728,'same_sphere':12,'same_house':132,'cross_house':1584,
                    'unreviewed_lexical_flags':c['lexical'],'source_semantic_approvals':0},
        'performance_hypothesis':f'Reduce user-visible latency when finding sources about {sph["name"]} without hiding other spheres or fabricating semantic matches',
        'synthetic_test_query':first['id'],'global_baseline_only':True,
        'performance_claim':'NOT_MEASURED_PER_SPHERE',
        'candidate_changes':make_four_proposals(sid,sph['name'],first['name'],role,REGISTRY),
        'classification':'DETERMINISTIC_SOURCE_STRUCTURE_REVIEW_NOT_144_INDEPENDENT_AGENTS',
        'authority_effect':'NONE','host_effect':'NONE','fiction_canon_effect':'NONE'}
   rc=jd(row);receipt_head=digest((receipt_head+rc).encode('utf-8'))
   w.write(compact({**row,'receipt_digest':rc,'chain_head':receipt_head})+'\n')
   reviews.append({**row,'receipt_digest':rc,'chain_head':receipt_head})
 ensure(len(reviews)==144 and len({r['sphere_id'] for r in reviews})==144,'SPHERE_DISAPPEARED')
 # Compute summary-level p95 / median as local evidence only. Timestamp/CPU is not part of receipts.
 bm=bench['pages']['baseline']['metrics'];om=bench['pages']['optimized']['metrics']
 def latency(key):
  return {'baseline_median_ms':bm[key]['median_ms'],'optimized_median_ms':om[key]['median_ms'],
          'baseline_p95_ms':bm[key]['p95_ms'],'optimized_p95_ms':om[key]['p95_ms'],
          'median_speedup_measured':None if om[key]['median_ms']<0.05 else round(bm[key]['median_ms']/om[key]['median_ms'],2)}
 meta={'schema':'atlas.meta145.performance-build/v1','status':'LOCAL_OPTIMIZATION_TESTED__HOST_NOT_DEPLOYED',
       'previous_12_edition_build_head':BASE_HEAD,
       'ariadne_original_digest':REGISTRY,'source_matrix_digest':EXPECTED_MATRIX,
       'review_receipt_chain_head':receipt_head,'review_rows_sha256':digest(reviewfile.read_bytes()),
       'pair_review_matrix_sha256':digest(matfile.read_bytes()),
       'baseline_viewer_sha256':bench['pages']['baseline']['sha256'],
       'optimized_viewer_sha256':bench['pages']['optimized']['sha256'],
       'benchmark_sha256':digest(benchmark.read_bytes()),
       'counts':{'sphere_perspectives_computed':144,'nodes_per_perspective':1728,
                 'sphere_node_pair_evaluations':n,'house_syntheses':12,'unified_meta_builds':1,
                 'project_proposals_from_144_spheres':576,'semantic_relations_accepted':0,
                 'hosted_model_turns':0,'real_peer_conversations':0,'production_changes':0},
       'implemented_source_change':'VIEWER_PREINDEX_AND_48_ROW_DOM_WINDOW_WITH_PAGING',
       'browser_local_measures':{key:latency(key) for key in ('fullReset','narrowExact','houseSelect')},
       'source_payload_changed':False,'all_1728_nodes_accessible_in_browser':True,
       'hosted_latency_measured':False,'resident_authenticated':False,'release_effect':'NONE',
       'required_next_host_measure':'REAL_SIGNED_IN_WORK_BROKER_P50_P95_INGRESS_TO_ACK_AND_RECEIVER_ACTIVATION'}
 meta['meta145_receipt_hash']=jd(meta)
 write(dest/'META145_MEASURED_BUILD.json',meta)
 house_syntheses=[]
 for hid in houses:
  rr=[x for x in reviews if x['house_id']==hid]
  ensure(len(rr)==12,'HOUSE_REVIEW_GAP')
  house_syntheses.append({'house':hid,'name':houses[hid]['name'],'spheres':12,
    'source_pair_evaluations':20736,'source_review_receipts':[x['receipt_digest'] for x in rr],
    'lexical_flags_awaiting_review':sum(x['coverage']['unreviewed_lexical_flags'] for x in rr),
    'priority':'LOCAL_NAVIGATION_FAST_PATH_BENCHMARK_CANDIDATE',
    'hosted_performance':'UNTESTED','consent_privacy':'REMAINS_GATE'})
 write(dest/'HOUSE12_FAST_PATH_SYNTHESIS.json',house_syntheses)
 return meta
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--turbo-root',type=Path,required=True)
 ap.add_argument('--out',type=Path,required=True);ap.add_argument('--benchmark',type=Path,required=True);ap.add_argument('--fast-viewer',type=Path,required=True);a=ap.parse_args()
 print(compact(scan(a.turbo_root,a.out,a.benchmark,a.fast_viewer)))
