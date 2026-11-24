"""Offline metadata-only review helpers inspired by public specifications.

Traceparent layout: W3C Trace Context (no tracestate or live propagation).
Provenance declaration: unsigned LOCAL statement only; NOT a SLSA attestation.
Pareto review: no welfare inference, no CANON or source rights grants.
"""
from __future__ import annotations
import hashlib, json, math, re

ALLOWED_FIELDS=frozenset({'id','cost','risk','evidence','rights','physicalFloor','communityFloor','sourceDigest','originMode'})
HASH=re.compile(r'[a-f0-9]{64}\Z')
TP=re.compile(r'([a-f0-9]{2})-([a-f0-9]{32})-([a-f0-9]{16})-([a-f0-9]{2})\Z')

def valid_traceparent(value):
    if type(value) is not str: return False
    m=TP.fullmatch(value)
    return bool(m and m.group(1)!='ff' and int(m.group(2),16)>0 and int(m.group(3),16)>0)

def synthetic_traceparent(run_id,coordinate):
    if not isinstance(run_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{4,80}',run_id):raise ValueError('INVALID_RUN_ID')
    if not isinstance(coordinate,str) or not re.fullmatch(r'H(?:0[1-9]|1[0-2])\.S(?:0[1-9]|1[0-2])\.N(?:0[1-9]|1[0-2])',coordinate):raise ValueError('INVALID_NODE')
    b=hashlib.sha256(('synthetic\0'+run_id+'\0'+coordinate).encode()).hexdigest()
    out='00-'+b[:32]+'-'+b[32:48]+'-00'
    if not valid_traceparent(out):raise ValueError('INVALID_TRACE')
    return out

def offline_provenance(source_digest,artifact_digest):
    if any(type(x) is not str or not HASH.fullmatch(x) for x in (source_digest,artifact_digest)):
        raise ValueError('INVALID_PROVENANCE_SHA')
    return {'schema':'atlas.source-review.provenance.v1','scope':'UNSIGNED_LOCAL_STATEMENT',
            'sourceDigestSha256':source_digest,'artifactDigestSha256':artifact_digest,
            'predicateTypeReference':'https://slsa.dev/provenance/v1',
            'realSlsaAttestation':False,'signedByTrustedBuildPlatform':False,
            'productionPromotionAllowed':False,'privateSourceContentsIncluded':False}

def pareto_front(options):
    """Finite same-budget counterexamples; no offsetting nonnegotiable floors."""
    HOLD={'state':'HOLD','reason':'NO_TRUSTED_REVIEW','authorityEffect':'NONE','selected':[]}
    if type(options) is not list or not (1<=len(options)<=16):return HOLD
    clean=[]
    for row in options:
        if type(row) is not dict or set(row)!=ALLOWED_FIELDS:return HOLD
        if any(type(row[k]) is not str for k in ('id','rights','physicalFloor','communityFloor','sourceDigest','originMode')):return HOLD
        if row['originMode']!='WORK' or row['rights']!='PASS' or row['physicalFloor']!='PASS' or row['communityFloor']!='PASS':return HOLD
        if not re.fullmatch('[A-Za-z0-9_-]{1,32}',row['id']) or not HASH.fullmatch(row['sourceDigest']):return HOLD
        if any(type(row[k]) not in (int,float) or not math.isfinite(row[k]) or row[k]<0 for k in ('cost','risk','evidence')):return HOLD
        clean.append(row)
    if len({r['id'] for r in clean})!=len(clean):return HOLD
    # Cost and risk are minimized, independent evidence proxy maximized.
    surviving=[]
    for a in clean:
        dominated=any(b is not a and b['cost']<=a['cost'] and b['risk']<=a['risk'] and b['evidence']>=a['evidence']
                      and (b['cost']<a['cost'] or b['risk']<a['risk'] or b['evidence']>a['evidence']) for b in clean)
        if not dominated:surviving.append(a['id'])
    return {'state':'LOCAL_PARETO_CANDIDATES_UNVERIFIED','selected':sorted(surviving),
            'dominated':sorted(r['id'] for r in clean if r['id'] not in surviving),
            'independentlyReviewed':False,'authorityEffect':'NONE','hostRightsAttested':False,
            'welfareGainVerified':False}


def refusal_report(_private_context=None):
    """Same result for any protected context including existence/size/timing labels."""
    return {'state':'HOLD','authorityEffect':'NONE','privateContentRead':False,'countDisclosed':False,
            'nextAction':'CURRENT_HOST_READ_AND_RETURN_REQUIRED'}
