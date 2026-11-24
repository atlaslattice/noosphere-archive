"""Optional standalone benchmark AGAINST the existing GF9-R2 source as actually supplied.

No editable model weights, network, host rights or scheduled execution. The
source package is an explicit CLI argument and remains unchanged.
"""
from pathlib import Path
import sys,hashlib,argparse,json,time
p=argparse.ArgumentParser()
p.add_argument('--existing-gf9-root',required=True)
p.add_argument('--out',required=True)
p.add_argument('--passes',type=int,default=21)
a=p.parse_args()
root=Path(a.existing_gf9_root)
protocol=root/'src/protocol.py'
if not protocol.is_file():raise ValueError('EXACT_GF9_SOURCE_PATH_MISSING')
code_sha=hashlib.sha256(protocol.read_bytes()).hexdigest()
sys.path.insert(0,str(root))
from src.protocol import make_message,Policy,ANCHOR
from atlas1728.gf9_cache import CompiledGF9Packets,benchmark_existing_gf9
if ANCHOR!='07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6':raise ValueError('SOURCE_DRIFT')
factory=lambda mod,ch:make_message(mod,ch,Policy(3,6))
t=time.perf_counter_ns();cache=CompiledGF9Packets(factory=factory,root_sha=ANCHOR,generator_sha=code_sha)
build_ms=(time.perf_counter_ns()-t)/1e6
bench=benchmark_existing_gf9(factory,cache,ANCHOR,code_sha,passes=a.passes)
bench['cold_cache_build_ms']=round(build_ms,5)
bench['source_original_semantics_compared']=True
bench['packet_count']=len(cache.packets)
bench['source_role']='OPTIONAL_ORIGINAL_GF9_MODULE_BOUND_WITH_CODE_DIGEST'
Path(a.out).write_text(json.dumps(bench,indent=2)+'\n')
print(json.dumps(bench,indent=2))
