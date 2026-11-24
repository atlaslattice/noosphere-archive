#!/usr/bin/env python3
"""Independent bounded source-safe verifier; enforces completeness and provenance."""
from pathlib import Path
from hashlib import sha256
import json, argparse, re
import numpy as np
from telescope_engine import read_registry,digest,STAGES,REGISTRY_SHA,ROUNDS,N

def verify(root:Path,registry:Path):
    src=read_registry(registry)
    out=root/'output' if (root/'output').exists() else root
    receipt=json.loads((out/'FINAL_RECEIPT.json').read_text())
    if receipt['nodeCount']!=N or receipt['spheres']!=144 or receipt['houses']!=12:return False,'SHAPE'
    if receipt['originalSourceDigest']!=REGISTRY_SHA:return False,'SOURCE'
    plans=[json.loads(s) for s in (out/'node_build_orders_1728.jsonl').read_text().splitlines()]
    if len(plans)!=N:return False,'NODE_TRUNCATED'
    for i,(row,source) in enumerate(zip(plans,src),1):
        if row['id']!=f'UPG-{i:04}' or row['coordinate']!=source['id'] or row['sourceSha']!=source['sourceSha']:return False,'NODE_LINEAGE'
        if sorted(row['workOrders'])!=sorted(('SwarmChat','Atlas','Ariadne','Iron Empire')):return False,'SYSTEM_MISSING'
        if row['authority']!='NONE':return False,'AUTHORITY'
    spheres=json.loads((out/'sphere_modules_144.json').read_text())
    houses=json.loads((out/'house_modules_12.json').read_text())
    if len(spheres)!=144 or len(houses)!=12:return False,'AGGREGATES'
    if [node for sp in spheres for node in sp['nodes']]!=[x['id'] for x in src]:return False,'SPHERE_LINEAGE'
    if [sp['sphere'] for h in houses for sp in h['spheres']]!=[sp['sphere'] for sp in spheres]:return False,'HOUSE_LINEAGE'
    stages=[json.loads(s) for s in (out/'macroturns_20_local.jsonl').read_text().splitlines()]
    if len(stages)!=20:return False,'STAGE_TRUNCATED'
    head=digest({'genesis':'ATLAS-20-STAGES','source':REGISTRY_SHA})
    for i,stage in enumerate(stages,1):
        if stage['stage']!=i or stage['guard']!=STAGES[i-1][2] or stage['priorReceipt']!=head:return False,'STAGE_LINEAGE'
        if stage['inheritedGuards']!=[s[2] for s in STAGES[:i]]:return False,'INHERITED_GUARDS'
        state={k:v for k,v in stage.items() if k!='receiptSha256'}
        if digest(state)!=stage['receiptSha256']:return False,'STAGE_SHA'
        head=stage['receiptSha256']
    if receipt['macroturnReceiptHead']!=head:return False,'FINAL_STAGE_SHA'
    with np.load(out/'closed_form_1728x1728.npz') as d:
        if d['error'].shape!=(1728,1728,3) or len(d['coordinate'])!=1728:return False,'MATRIX_TRUNCATED'
        if (d['coordinate']!=[x['id'] for x in src]).any():return False,'MATRIX_COORD'
        if not np.isfinite(d['error']).all():return False,'MATRIX_NAN'
        sim=receipt['simulation']
        if any(abs(float(d['error'][:,:,i].mean())-sim['MAE'][k])>1e-7 for i,k in enumerate(('solo','isolated','council'))):return False,'MATRIX_STATS'
    return True,'SOURCE_AND_CHAINS_PASS_NOT_HOST_VERIFIED'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('source',type=Path);a=p.parse_args()
    ok,msg=verify(a.root,a.source);print(json.dumps({'ok':ok,'status':msg,'hostVerified':False}));raise SystemExit(0 if ok else 1)
