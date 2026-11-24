"""Run the source-pinned full 1728/144/12 local build; NO network calls or host writes."""
from __future__ import annotations
import argparse,json,pathlib,sys
from atlas1728 import Corpus,compile_build,benchmark_lookup
from atlas1728.engine import persist_sqlite
from atlas1728.source import canon,sha

def dump_lines(path,items):
    with open(path,'w',encoding='utf8') as f:
        for i in items:f.write(canon(i).decode('ascii')+'\n')

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--ariadne');p.add_argument('--openalex');p.add_argument('--out',required=True);p.add_argument('--bench-passes',type=int,default=31);p.add_argument('--synthetic',action='store_true')
    x=p.parse_args(argv)
    if not x.synthetic and not x.ariadne:raise ValueError('EXACT_OWNER_SOURCE_REQUIRED')
    corpus=Corpus.synthetic() if x.synthetic else Corpus.original(x.ariadne,x.openalex)
    dest=pathlib.Path(x.out);dest.mkdir(parents=True,exist_ok=True)
    results=compile_build(corpus)
    bench=benchmark_lookup(corpus,passes=x.bench_passes)
    receipt=persist_sqlite(results,dest/'atlas_1728_compiled.sqlite')
    for f,items in [('node_upgrades_1728.jsonl',results['nodes']),('sphere_pathways_144.jsonl',results['pathways']),('node_metrics_1728.jsonl',results['metrics'])]:dump_lines(dest/f,items)
    for name,obj in [('house_modules_12.json',results['modules']),('single_build_summary.json',results['summary']),('benchmark_lookup.json',bench),('sqlite_receipt.json',receipt)]:
        (dest/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'summary':results['summary'],'benchmark':bench,'sqlite_receipt':receipt},indent=2))
    return 0
if __name__=='__main__':raise SystemExit(main())
