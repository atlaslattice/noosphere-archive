"""Atlas GF8 source-only inference wrapper: no GPT weights, model calls or host rights.

The output is a data-only, bounded, provenance-typed context object. A future
host can supply it to an LLM after genuine READ+RETURN authorization, where
an LLM may reason over *tools/results*; this module cannot grant permissions,
change model weights, train, publish to CANON or create authenticated experts.
"""
from __future__ import annotations
from hashlib import sha256
import json
import math
import re
from .gf8 import Plate,driven_glyph,reference_for_gf7,mode_hz,measurement_comparison
from .glyph import REGISTRY_SHA,hsn_parts,gf7_parts
from .memory import LocalMemory

HEX64=re.compile(r'^[0-9a-f]{64}$')
SRC=re.compile(r'^https://[a-zA-Z0-9._/-]{3,290}$')


def _digest(obj)->str:
    return sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest()


def prepare_reasoning_context(*,hsn:str,gf7:str,plate:Plate,drive_hz:float,
          source_digest:str=REGISTRY_SHA,work_mode:str='WORK',
          source_refs:tuple[str,...]=(),review_tip:str|None=None,
          grid:int=33,max_mode:int=8)->dict:
    """Pure filter (safe context), NEVER an agent executor or a host attestation.

    Exact HSN and GF7 are separate handles. Caller must declare their
    relationship; a GF7 positional analogy confers no scientific identity.
    """
    hsn_parts(hsn);gf7_parts(gf7)
    if work_mode!='WORK':raise ValueError('PROTECTED_MODE_NOT_INGESTIBLE')
    if source_digest!=REGISTRY_SHA:raise ValueError('UNTRUSTED_REGISTRY_EDITION')
    if type(source_refs) not in (tuple,list) or len(source_refs)>8 or any(not isinstance(s,str) or not SRC.fullmatch(s) for s in source_refs):raise ValueError('INVALID_SOURCE_REFERENCES')
    if review_tip is not None and (not isinstance(review_tip,str) or not HEX64.fullmatch(review_tip)):raise ValueError('REVIEW_TIP_INVALID')
    plate.validate()
    physical=driven_glyph(plate,drive_hz,max_mode=max_mode,grid=grid)
    # Never place full displacement matrices or private source bodies into an LLM prompt.
    summary={k:v for k,v in physical.items() if k not in ('amplitude_proxy','nodal_proxy_bitmap','field')}
    scope={'hsn':hsn,'hsn_edition':'Ariadne v0.7','hsn_source_sha256':source_digest,
           'gf7':gf7,'gf7_relation':'POSITIONAL_ANALOGY_NOT_SEMANTIC_SAME_AS',
           'gf8_model':plate.metadata(),'drive_frequency_hz':drive_hz,
           'physical_model_output':summary,'source_refs':list(source_refs),
           'synthetic_review_tip_sha256':review_tip,'review_scope':'WORK_LOCAL_SOURCE_ONLY',
           'scientific_grading':'ANALYTIC_PREDICTION_UNCALIBRATED',
           'authorization':'UNVERIFIED_REQUIRE_HOST_READ_AND_RETURN',
           'source_truth':'NEVER_PROMOTED',
           'intended_use':'LLM_CONTEXT_SUPPLEMENT_NOT_MODEL_WEIGHT_TRAINING',
           'model_weight_updates':False,'autonomous_knowledge_updates':False,
           'personhood_assumed':False,'canon_writes':False,
           'protected_mode_imported':False}
    packet={'schema':'atlas.gf8.reasoning-filter/v1',**scope}
    return {**packet,'receipt_sha256':_digest(packet)}


def with_local_review_tip(packet:dict, memory:LocalMemory)->dict:
    if packet.get('schema')!='atlas.gf8.reasoning-filter/v1':raise ValueError('INVALID_PACKET')
    safe_explanation(packet)  # Never re-seal an altered or unreceipted context.
    verified=memory.verify()
    if verified['status']!='LOCAL_HASH_CHAIN_VERIFIED':raise ValueError('MEMORY_TAMPERED')
    # Memory hint is neither retrieval content nor authenticated review itself.
    obj={k:v for k,v in packet.items() if k!='receipt_sha256'}
    obj['synthetic_review_tip_sha256']=verified['tip']
    return {**obj,'receipt_sha256':_digest(obj)}


def safe_explanation(packet:dict)->str:
    if packet.get('schema')!='atlas.gf8.reasoning-filter/v1' or not packet.get('receipt_sha256'):
        raise ValueError('INVALID_CONTEXT_PACKET')
    original={k:v for k,v in packet.items() if k!='receipt_sha256'}
    if _digest(original)!=packet['receipt_sha256']:
        raise ValueError('CONTEXT_SOURCE_TAMPERED')
    o=packet['physical_model_output'];state=o['status']
    fn=o.get('nearest_mode',{}).get('frequency_hz')
    nearest=f'{fn:.2f} Hz' if isinstance(fn,(int,float)) else 'none'
    return (f"Atlas GF8 {packet['hsn']} / {packet['gf7']}: drive {packet['drive_frequency_hz']:.2f} Hz, "
            f'nearest modeled mode {nearest}, output {state}. '
            'Do not equate GF7 band indexing, GF8 plate physics, OpenAlex candidates, or HSN semantics. '
            'No model weights changed; request source and rights review before reliance.')


def _finite_number(value)->bool:
    if type(value) not in (int,float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def postflight_claim_gate(packet:dict,claim:dict)->dict:
    """Bounded validation of structured claims offered by ANY model for the wrapper.

    It can confirm alignment with a local calculation, not truth or authored
    natural language. Unknown authority claims fail closed.
    """
    safe_explanation(packet) # verifies source receipt
    if type(claim)!=dict or set(claim)!={'claim_kind','frequency_hz','model_status'}:
        return {'status':'HOLD_UNEXPECTED_OUTPUT_SHAPE','authority':'NONE'}
    if claim.get('claim_kind')!='GF8_PREDICTED_MODE_ONLY':
        return {'status':'HOLD_UNSUPPORTED_CLAIM_KIND','authority':'NONE'}
    freq=claim.get('frequency_hz')
    expected=packet['physical_model_output'].get('nearest_mode',{}).get('frequency_hz')
    if not _finite_number(freq) or not _finite_number(expected) or abs(freq-expected)>max(1e-8,1e-8*expected):
        return {'status':'HOLD_NUMERICAL_CONTRADICTION','authority':'NONE'}
    if claim.get('model_status')!=packet['physical_model_output']['status']:
        return {'status':'HOLD_EVIDENCE_GRADE_CONTRADICTION','authority':'NONE'}
    return {'status':'SOURCE_CALCULATION_PARITY_PASS_ONLY',
            'verified_numerical_claim':True,'experiment_validated':False,
            'semantic_approval':False,'model_weights_changed':False,
            'host_authorized':False,'canon_effect':'NONE'}
