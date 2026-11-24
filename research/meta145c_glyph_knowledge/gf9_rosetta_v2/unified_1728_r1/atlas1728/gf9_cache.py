"""Source- and generator-pinned, read-only reuse of existing GF9 reference packets.

This does NOT implement a second GF9 compiler. The original, verified GF9
make_message module is an injected dependency. It saves CPU on unchanged
mathematical reference packets. It never caches host authorizations, rights,
private creative state, or semantic adjudications.
"""
from __future__ import annotations
import hashlib,json,re,statistics,time
from collections.abc import Callable
from .source import ARIADNE_SHA,canon,sha
from .shared import CHAPTER_OPS

class CompiledGF9Packets:
    def __init__(self, *, factory:Callable[[int,int],dict], root_sha:str, generator_sha:str):
        if root_sha!=ARIADNE_SHA or not re.fullmatch(r'[a-f0-9]{64}',generator_sha):raise ValueError('GF9_EXACT_SOURCE_REQUIRED')
        if not callable(factory):raise ValueError('ORIGINAL_FACTORY_REQUIRED')
        self.source=(root_sha,generator_sha)
        self.packets={}
        self.packet_digests={}
        for module in range(144):
            for chapter in range(12):
                k=f'H{module//12+1:02d}.S{module%12+1:02d}.N{chapter+1:02d}'
                msg=factory(module,chapter)
                if not isinstance(msg,dict) or msg.get('m')!=k[:7] or msg.get('c')!=chapter+1 or msg.get('op')!=CHAPTER_OPS[chapter] or msg.get('a')!=root_sha[:12] or msg.get('scope')!='SYNTHETIC_WORK':raise ValueError('GF9_PARENT_PACKET_MISMATCH')
                raw=canon(msg)
                if len(raw)>4096:raise ValueError('UNBOUNDED_GF9_PACKET')
                self.packets[k]=raw
                self.packet_digests[k]=sha(raw)
        if len(self.packets)!=1728:raise AssertionError('GF9_CACHE_CARDINALITY')
    def get(self,nid,*,root_sha,generator_sha,request_mode='WORK',host_rights=None):
        if root_sha!=self.source[0] or generator_sha!=self.source[1]:raise ValueError('STALE_SOURCE_OR_CODE')
        if request_mode!='WORK' or host_rights is not None:raise ValueError('HOST_AUTH_NOT_A_CACHED_PROPERTY')
        raw=self.packets.get(nid)
        if raw is None:raise ValueError('UNKNOWN_COORDINATE')
        if sha(raw)!=self.packet_digests[nid]:raise ValueError('MEMORY_CACHE_TAMPER')
        return json.loads(raw)


def benchmark_existing_gf9(factory,cache,source_sha,code_sha,passes=21):
    """Paired dynamic-GF9 generator vs compiled immutable cache; complete parity.
    This is CPU time for SOURCE-ONLY generation, not model inference/transport.
    """
    if not 5<=passes<=101:raise ValueError('BENCH_PASSES')
    ids=tuple(sorted(cache.packets))
    def old():
        return [factory(((int(nid[1:3])-1)*12+int(nid[5:7])-1),int(nid[9:11])-1) for nid in ids]
    def fast():
        return [cache.get(nid,root_sha=source_sha,generator_sha=code_sha) for nid in ids]
    if old()!=fast():raise AssertionError('GF9_PACKET_SEMANTICS_CHANGED')
    for _ in range(3):old();fast()
    measurements={'dynamic':[],'compiled':[]}
    for i in range(passes):
        for kind in (('dynamic','compiled') if i%2==0 else ('compiled','dynamic')):
            t=time.perf_counter_ns();result=(old() if kind=='dynamic' else fast())
            if len(result)!=1728 or result!=fast():raise AssertionError('GF9_CACHE_PARITY')
            measurements[kind].append((time.perf_counter_ns()-t)/1e6)
    a=statistics.median(measurements['dynamic']);b=statistics.median(measurements['compiled'])
    return {'schema':'atlas.gf9.current-generator-cache-benchmark/v1','sourceSha256':source_sha,
      'generatorSha256':code_sha,'pairedRuns':passes,'packetsPerRun':1728,
      'original_gf9_dynamic_median_ms':round(a,6),'compiled_cached_median_ms':round(b,6),
      'median_speedup':round(a/b,3),'exact_packet_parity':True,
      'cache_build_cost_excluded':True,'scope':'LOCAL_GF9_MATH_REFERENCE_ONLY_NOT_HOSTED',
      'current_host_algorithm_compared':False,'gpt_weight_changes':False}
