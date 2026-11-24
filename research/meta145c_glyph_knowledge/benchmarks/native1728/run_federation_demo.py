"""Reproduce local federation delegates; caller selects all source/data paths."""
import argparse, hashlib, json, sys, time
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--repository-root',type=Path,required=True)
parser.add_argument('--excellence-root',type=Path,required=True)
parser.add_argument('--plan',type=Path,required=True)
parser.add_argument('--registry',type=Path)
parser.add_argument('--topics',type=Path)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
package=args.repository_root/'research/meta145c_glyph_knowledge'
sys.path.insert(0,str(package.resolve()))
from src.beast20.federation import PinnedFederation
inventory=json.loads((package/'docs/native1728/PUBLIC_COMPONENT_INVENTORY.json').read_text())
started=time.perf_counter()
with PinnedFederation.from_inventory(inventory,roots={'EXCELLENCE1728_CORE':str(args.excellence_root),'GF9_ROSETTA_R2':str(args.repository_root),'UNIFIED_ATLAS1728_PYTHON':str(args.repository_root)},plan_path=args.plan,expected_plan_sha256='47084b895a6317db16275a92c3878a340d31af15fb9ab479db7101953c18e49c',registry_path=args.registry,topics_path=args.topics) as federation:
    calls=[federation.call('excellence','plan_status'),federation.call('excellence','ready',{'total_units':36,'max_ready':12}),federation.call('excellence','query',{'text':'memory','limit':2}),federation.call('excellence','perspective',{'sphere_id':'H01.S01'}),federation.call('excellence','meta145'),federation.call('gf9','packet_roundtrip',{'module':143,'chapter':11,'repetition':3}),federation.call('unified','source_status'),federation.call('unified','node_reference',{'coordinate':'H01.S01.N01'}),federation.call('unified','build_summary')]
    receipt={'schema':'atlas.native.federation-execution/v1','status':'REAL_UPSTREAM_DELEGATES_EXECUTED_LOCALLY','mounts':federation.status(),'calls':calls,'network_requests':0,'model_calls':0,'work_messages_posted':0,'elapsed_seconds':round(time.perf_counter()-started,3),'original_source_bodies_returned':False,'source_sha256':hashlib.sha256((package/'src/beast20/federation.py').read_bytes()).hexdigest()}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'output':str(args.output),'calls':len(calls),'original_source_verified':calls[-1]['result']['original_source_bytes_verified'],'node_upgrades':calls[-1]['result']['node_upgrades'],'module_node_checks':calls[-1]['result']['module_node_checks'],'build_digest':calls[-1]['result']['build_digest_sha256'],'elapsed_seconds':receipt['elapsed_seconds']},indent=2))
