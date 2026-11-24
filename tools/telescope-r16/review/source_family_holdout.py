"""Strict source-family holdout PREPARATION gate for Atlas R16/R17.

It assesses declared PUBLIC_WORK metadata only. It is deliberately incapable of
host source attestation, independent review, authorization, release, or sending.
Do not interpret PREPARED as accepted evidence or an independent data split.
"""
from __future__ import annotations
from collections import defaultdict
import re

SCHEMA = 'atlas.r17.source-family-holdout/v1'
COORD = re.compile(r'^H(0[1-9]|1[0-2])\.S(0[1-9]|1[0-2])\.N(0[1-9]|1[0-2])$')
SHA = re.compile(r'^[0-9a-f]{64}$')
TEXT = re.compile(r'^[A-Za-z0-9._:-]{1,96}$')
REQUIRED = frozenset({'id','coord','split','family','prior','shock','series','tick','sourceSha','scope'})
LINK_KEYS = frozenset({'from','to','relation'})
RELATIONS = frozenset({'SOURCE_ALIAS','SHARED_SOURCE','SHARED_PRIOR','SHARED_SHOCK'})


def _hold(reason='INVALID_OR_UNVERIFIED_SOURCE'):
    return {'schema':SCHEMA,'status':'HOLD','reason':reason,
            'hostAuthenticated':False,'independentHoldoutVerified':False,
            'modelCalls':0,'externalEffects':0,'releaseEligible':False}


def prepare_holdout(records, links, *, lineage_complete=False, embargo=12):
    """Return a no-authority aggregate review pointer or a generic HOLD.

    Equality of caller-supplied family/prior/shock IDs and declared transitive
    links is a NEGATIVE check, not trusted proof that omitted links do not exist.
    """
    if type(lineage_complete) is not bool or not lineage_complete:
        return _hold('LINEAGE_NOT_DECLARED_COMPLETE')
    if type(embargo) is not int or not (1 <= embargo <= 10000):
        return _hold()
    if type(records) is not list or not (2 <= len(records) <= 5000):
        return _hold()
    if type(links) is not list or len(links) > 10000:
        return _hold()
    by_id = {}
    for rec in records:
        if type(rec) is not dict or frozenset(rec) != REQUIRED:
            return _hold()
        if (type(rec['scope']) is not str or rec['scope'] != 'PUBLIC_WORK' or
            type(rec['split']) is not str or rec['split'] not in ('TRAIN','HOLDOUT')):
            return _hold()
        if not (type(rec['id']) is str and TEXT.fullmatch(rec['id']) and
                type(rec['coord']) is str and COORD.fullmatch(rec['coord']) and
                type(rec['sourceSha']) is str and SHA.fullmatch(rec['sourceSha']) and
                type(rec['tick']) is int and 0 <= rec['tick'] <= 10000000):
            return _hold()
        if any(type(rec[k]) is not str or not TEXT.fullmatch(rec[k])
               for k in ('family','prior','shock','series')):
            return _hold()
        if rec['id'] in by_id:
            return _hold()
        by_id[rec['id']] = rec
    splits = {r['split'] for r in records}
    if splits != {'TRAIN','HOLDOUT'}:
        return _hold('TWO_SPLITS_REQUIRED')
    # Stable connected-component unions: direct and indirect lineage cannot be
    # laundered by a fresh intermediate alias. This is a conservative check.
    parent = {k:k for k in by_id}
    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a,b):
        pa,pb = root(a),root(b)
        if pa != pb:
            parent[max(pa,pb)] = min(pa,pb)
    for key in ('family','prior','shock'):
        groups = {}
        for rec in records:
            if rec[key] in groups:
                union(groups[rec[key]],rec['id'])
            else:
                groups[rec[key]] = rec['id']
    for link in links:
        if (type(link) is not dict or frozenset(link) != LINK_KEYS or
            type(link['from']) is not str or type(link['to']) is not str or
            link['from'] not in by_id or link['to'] not in by_id or
            type(link['relation']) is not str or link['relation'] not in RELATIONS or
            link['from'] == link['to']):
            return _hold()
        union(link['from'],link['to'])
    component_splits = defaultdict(set)
    for rec in records:
        component_splits[root(rec['id'])].add(rec['split'])
    if any(len(xs) > 1 for xs in component_splits.values()):
        return _hold('CROSS_SPLIT_SOURCE_DEPENDENCE')
    # Embargo across the same observation series even if declared family IDs
    # differ. Equal exact ticks are always banned; cutoff is inclusive.
    series = defaultdict(lambda: {'TRAIN': [], 'HOLDOUT': []})
    for rec in records:
        series[rec['series']][rec['split']].append(rec['tick'])
    for by_split in series.values():
        a=sorted(by_split['TRAIN']); b=sorted(by_split['HOLDOUT'])
        i=j=0
        while i < len(a) and j < len(b):
            if abs(a[i]-b[j]) <= embargo:
                return _hold('TEMPORAL_EMBARGO_OVERLAP')
            if a[i] < b[j]: i+=1
            else: j+=1
    return {'schema':SCHEMA,'status':'PREPARED_NOT_AUTHORIZED',
            'lineageMode':'DECLARED_METADATA_ONLY_UNTRUSTED',
            'trainCount':sum(r['split']=='TRAIN' for r in records),
            'holdoutCount':sum(r['split']=='HOLDOUT' for r in records),
            'declaredComponents':len(component_splits),'embargo':embargo,
            'hostAuthenticated':False,'independentHoldoutVerified':False,
            'modelCalls':0,'externalEffects':0,'releaseEligible':False}
