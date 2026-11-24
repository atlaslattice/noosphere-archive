"""Independent offline audit over saved outputs; no source or compiler imports."""
from __future__ import annotations
import json,sqlite3,hashlib,argparse
from pathlib import Path

def digest(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')).hexdigest()

def loadlines(p):return [json.loads(line) for line in Path(p).read_text().splitlines() if line.strip()]

def verify(root):
    root=Path(root)
    nodes=loadlines(root/'node_upgrades_1728.jsonl');paths=loadlines(root/'sphere_pathways_144.jsonl');metrics=loadlines(root/'node_metrics_1728.jsonl')
    houses=json.loads((root/'house_modules_12.json').read_text());summary=json.loads((root/'single_build_summary.json').read_text())
    if tuple(map(len,(nodes,paths,houses,metrics)))!=(1728,144,12,1728):raise ValueError('FULL_CARDINALITY_REQUIRED')
    if len({n['coordinate'] for n in nodes})!=1728 or len({p['sphere'] for p in paths})!=144 or len({m['coordinate'] for m in metrics})!=1728:raise ValueError('UNIQUE_IDENTITIES_REQUIRED')
    for collection in (nodes,paths,houses,metrics):
        for v in collection:
            if v['digest_sha256']!=digest({k:x for k,x in v.items() if k!='digest_sha256'}):raise ValueError('RECORD_SHA_MISMATCH')
    for n in nodes:
        if len(n['module_outputs'])!=12 or len(n['module_output_digests'])!=12:raise ValueError('TWELVE_MODULES_REQUIRED')
        if not all(m['result_sha256']==digest(m['result']) for m in n['module_outputs']):raise ValueError('MODULE_RESULT_SHA_MISMATCH')
        if not all(m['result'].get('pass') is True for m in n['module_outputs']):raise ValueError('MODULE_NOT_PASSED')
    reference={n['coordinate']:n['digest_sha256'] for n in nodes}
    prev='0'*64
    for p in paths:
        if p['previous_path_digest']!=prev or p['node_upgrade_digests']!=[reference[n] for n in p['node_coordinates']]:raise ValueError('SPHERE_CHAIN_OR_MEMBERSHIP')
        prev=p['digest_sha256']
    if summary['terminal_sphere_digest']!=prev:raise ValueError('SYNTHESIS_TIP_DRIFT')
    if sum(x['baseline_linear_comparisons'] for x in metrics)!=1493856 or sum(x['optimized_indexed_comparisons'] for x in metrics)!=1728:raise ValueError('METRICS_DRIFT')
    db=sqlite3.connect(root/'atlas_1728_compiled.sqlite')
    try:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('SQLITE_BAD')
        for table,count in [('nodes',1728),('metrics',1728),('pathways',144),('house_modules',12),('ledger',1728)]:
            if db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]!=count:raise ValueError('SQLITE_COUNT_'+table)
        chain='0'*64
        for seq,nid,prev_s,receipt in db.execute('SELECT seq,coordinate,previous_sha,receipt_sha FROM ledger ORDER BY seq'):
            if prev_s!=chain or receipt!=digest({'seq':seq,'previous':chain,'coordinate':nid,'node_receipt':reference[nid]}):raise ValueError('SQLITE_LEDGER_TAMPER')
            chain=receipt
    finally:db.close()
    return {'schema':'atlas.1728.independent-archive-audit/v1','status':'PASS','original_source_status':summary['original_source_bytes_verified'],
     'node_records':len(nodes),'sphere_pathways':len(paths),'house_modules':len(houses),'module_results':len(nodes)*12,
     'metric_records':len(metrics),'strict_comparison_reductions':sum(m['strict_improvement'] for m in metrics),
     'unchanged_comparison_metrics':sum(not m['strict_improvement'] for m in metrics),
     'house_sphere_chain_tip':prev,'node_ledger_tip':chain,'semantic_gains_independently_established':0,
     'can_deploy':False,'independent_host_rights_verified':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out');a=p.parse_args()
    audit=verify(a.root)
    if a.out:Path(a.out).write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(audit,indent=2))
