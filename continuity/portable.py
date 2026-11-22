"""Finite, pure memory-bundle validation. No identity, consent, host/ACL or resurrection proof.

Only public-safe, explicitly synthetic/redacted metadata is processed. Caller-provided
permissions are *claims* requiring current host/affected-party verification elsewhere.
No private Play/Imagine/Quiet/Brain/Palace bodies are read or converted into Work.
"""
from __future__ import annotations
import copy
import hashlib
import json
import re
from typing import Any

SCHEMA = 'atlas.digital-continuity.memory-bundle/v0'
CONTRACT = 'atlas.digital-continuity.rehydration/v0'
_SHA = re.compile(r'^[0-9a-f]{64}$')
_ID = re.compile(r'^[a-z0-9][a-z0-9._:-]{2,100}$')
_HSN = re.compile(r'^H(?:0[1-9]|1[0-2])\.S(?:0[1-9]|1[0-2])\.N(?:0[1-9]|1[0-2])$')
_MODES = {'PLAY','QUIET','IMAGINE','SOCIAL','BRAIN','PALACE','HABITAT','DREAM','MEDICAL','FINANCIAL','LEGAL','PRIVATE'}
_STATES = {'OBSERVED_SOURCE','PUBLISHED_SOURCE','DERIVED_CANDIDATE','ASSUMED','DISPUTED','UNKNOWN'}
_ALLOWED_BUNDLE = {'schema','bundle_id','version','privacy_class','profile','ontology','sources','claims',
                   'rehydration_contract','created_at','parent','integrity','authority'}
_ALLOWED_SOURCE = {'source_id','locator','source_sha256','origin','license','permission','export_status'}
_ALLOWED_CLAIM = {'claim_id','statement','status','source_ids','does_not_prove'}
_ALLOWED_PROFILE = {'project','description','ontology_tags'}
_ALLOWED_ONTOLOGY = {'namespace','edition','source_sha256'}
_ALLOWED_PARENT = {'bundle_id','digest'}
_ALLOWED_INTEGRITY = {'algorithm','digest'}

class ContinuityError(ValueError):
    pass

def _fail(code: str) -> None:
    raise ContinuityError(code)

def _json_copy(x: Any) -> Any:
    try:
        return json.loads(json.dumps(x,sort_keys=True,ensure_ascii=False,allow_nan=False))
    except (TypeError, ValueError, OverflowError):
        _fail('NOT_CANONICAL_JSON')

def digest(value: Any) -> str:
    """SHA-256 of Python's deterministic JSON framing, NOT RFC8785/JCS proof."""
    value = _json_copy(value)
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,
                                     separators=(',', ':'),allow_nan=False).encode('utf8')).hexdigest()

def _keys(obj: Any, allowed: set[str], required: set[str], code: str) -> None:
    if type(obj) is not dict or set(obj) - allowed or required - set(obj):
        _fail(code)

def _id(x: Any) -> bool:
    return type(x) is str and _ID.fullmatch(x) is not None

def _sha(x: Any) -> bool:
    return type(x) is str and _SHA.fullmatch(x) is not None

def _safe_text(x: Any, *, max_len: int = 300) -> bool:
    return type(x) is str and 1 <= len(x) <= max_len and all(ord(c)>=32 for c in x)

def _base_checks(bundle: Any) -> None:
    _keys(bundle,_ALLOWED_BUNDLE,_ALLOWED_BUNDLE-{'parent','integrity'},'BUNDLE_SHAPE_HOLD')
    if bundle['schema'] != SCHEMA or not _id(bundle['bundle_id']) or type(bundle['version']) is not int or bundle['version'] < 1:
        _fail('BUNDLE_ID_OR_VERSION_HOLD')
    if bundle['privacy_class'] != 'PUBLIC_REDACTED_SYNTHETIC':
        _fail('PRIVATE_OR_UNREVIEWED_SOURCE_HOLD')
    if bundle['authority'] != 'NONE':
        _fail('SELF_AUTHORIZATION_HOLD')
    if type(bundle['created_at']) is not str or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',bundle['created_at']):
        _fail('UNPINNED_CREATION_TIME')
    _keys(bundle['profile'],_ALLOWED_PROFILE,{'project','description','ontology_tags'},'PROFILE_SHAPE_HOLD')
    if not _safe_text(bundle['profile']['project'],max_len=80) or not _safe_text(bundle['profile']['description'],max_len=300):
        _fail('PROFILE_UNSAFE_TEXT_HOLD')
    tags=bundle['profile']['ontology_tags']
    if type(tags) is not list or len(tags)>32 or any(not _safe_text(x,max_len=90) for x in tags):
        _fail('TAG_SHAPE_HOLD')
    _keys(bundle['ontology'],_ALLOWED_ONTOLOGY,_ALLOWED_ONTOLOGY,'ONTOLOGY_EDITION_HOLD')
    o=bundle['ontology']
    if not _safe_text(o['namespace'],max_len=100) or not _safe_text(o['edition'],max_len=120) or not _sha(o['source_sha256']):
        _fail('ONTOLOGY_SOURCE_HOLD')
    if type(bundle['sources']) is not list or not bundle['sources'] or len(bundle['sources'])>64:
        _fail('SOURCE_COUNT_HOLD')
    ids=set()
    for src in bundle['sources']:
        _keys(src,_ALLOWED_SOURCE,_ALLOWED_SOURCE,'SOURCE_SHAPE_HOLD')
        sid=src['source_id']
        if not _id(sid) or sid in ids: _fail('SOURCE_ID_COLLISION_HOLD')
        ids.add(sid)
        if not _safe_text(src['locator'],max_len=300) or not _sha(src['source_sha256']): _fail('SOURCE_PROVENANCE_HOLD')
        if src['origin'] != 'PUBLIC_SYNTHETIC' or src['permission'] != 'SOURCE_REPORTED_PUBLIC' or src['export_status'] != 'raw_complete_hashed':
            _fail('SOURCE_RIGHTS_OR_COMPLETENESS_HOLD')
        if not _safe_text(src['license'],max_len=90): _fail('LICENSE_UNDECLARED_HOLD')
    if type(bundle['claims']) is not list or not bundle['claims'] or len(bundle['claims'])>64:
        _fail('CLAIM_COUNT_HOLD')
    claim_ids=set()
    for c in bundle['claims']:
        _keys(c,_ALLOWED_CLAIM,_ALLOWED_CLAIM,'CLAIM_SHAPE_HOLD')
        if not _id(c['claim_id']) or c['claim_id'] in claim_ids:_fail('CLAIM_ID_COLLISION_HOLD')
        claim_ids.add(c['claim_id'])
        if not _safe_text(c['statement'],max_len=500) or not _safe_text(c['does_not_prove'],max_len=500):
            _fail('CLAIM_STATEMENT_HOLD')
        if (type(c['status']) is not str or c['status'] not in _STATES
            or type(c['source_ids']) is not list or not c['source_ids']
            or any(not _id(s) or s not in ids for s in c['source_ids'])):
            _fail('CLAIM_EVIDENCE_HOLD')
        if len(c['source_ids']) != len(set(c['source_ids'])):_fail('DUPLICATED_SOURCE_ID_HOLD')
        if c['status']=='OBSERVED_SOURCE' and 'test:' in c['statement'].lower(): _fail('SYNTHETIC_OBSERVATION_LABEL_HOLD')
    if not _id(bundle['rehydration_contract']):_fail('REHYDRATION_CONTRACT_ID_HOLD')
    if 'parent' in bundle:
        _keys(bundle['parent'],_ALLOWED_PARENT,_ALLOWED_PARENT,'PARENT_SHAPE_HOLD')
        if not _id(bundle['parent']['bundle_id']) or not _sha(bundle['parent']['digest']) or bundle['parent']['bundle_id']==bundle['bundle_id']:
            _fail('PARENT_IDENTITY_HOLD')

def seal_bundle(data: dict) -> dict:
    """Seal only synthetically redacted metadata, never signed authority or consent."""
    val=_json_copy(data)
    if 'integrity' in val:_fail('ALREADY_SEALED_HOLD')
    _base_checks(val)
    val['integrity']={'algorithm':'SHA-256-JSON-PYTHON-LOCAL','digest':digest(val)}
    return val

def verify_bundle(bundle: Any) -> dict:
    """Pure structural verification; returns candidate, NEVER proof of rights or personal identity."""
    val=_json_copy(bundle)
    _base_checks(val)
    _keys(val.get('integrity'),_ALLOWED_INTEGRITY,_ALLOWED_INTEGRITY,'INTEGRITY_MISSING_HOLD')
    if val['integrity']['algorithm']!='SHA-256-JSON-PYTHON-LOCAL' or not _sha(val['integrity']['digest']):
        _fail('INTEGRITY_ALGORITHM_HOLD')
    integrity=val.pop('integrity')
    if digest(val)!=integrity['digest']:_fail('INTEGRITY_TAMPER_HOLD')
    return {'status':'VERIFIED_STRUCTURE_ONLY','digest':integrity['digest'],'authority':'NONE',
            'identity_attested':False,'consent_attested':False,'host_release_authorized':False}

def prepare_rehydration(bundle: Any, contract: Any) -> dict:
    """Source list for an authorized caller to examine, NOT a resumed agent or identity."""
    # Bind subsequent output to the exact JSON value that was verified.
    # Raw Python callers can supply mutable objects or custom value classes;
    # verifying one copy then later reading the original is a TOCTOU risk.
    bundle_snapshot = _json_copy(bundle)
    contract_snapshot = _json_copy(contract)
    verification=verify_bundle(bundle_snapshot)
    _keys(contract_snapshot,{'schema','contract_id','bundle_id','source_digest','allowed','requires_human_review',
                    'identity_claim','limitations','disclosure'},
          {'schema','contract_id','bundle_id','source_digest','allowed','requires_human_review','identity_claim','limitations','disclosure'},
          'CONTRACT_SHAPE_HOLD')
    if contract_snapshot['schema']!=CONTRACT or not _id(contract_snapshot['contract_id']) or contract_snapshot['contract_id']!=bundle_snapshot['rehydration_contract']:
        _fail('CONTRACT_EDITION_HOLD')
    if contract_snapshot['bundle_id']!=bundle_snapshot['bundle_id'] or contract_snapshot['source_digest']!=verification['digest']:
        _fail('CONTRACT_SOURCE_DRIFT_HOLD')
    if contract_snapshot['allowed']!='REFERENCE_ONLY' or contract_snapshot['requires_human_review'] is not True or contract_snapshot['identity_claim']!='NONE':
        _fail('IMPERSONATION_OR_AUTHORITY_HOLD')
    if type(contract_snapshot['limitations']) is not list or len(contract_snapshot['limitations'])<3 or any(not _safe_text(s,max_len=180) for s in contract_snapshot['limitations']):
        _fail('LIMITATIONS_MISSING_HOLD')
    if not _safe_text(contract_snapshot['disclosure'],max_len=400):_fail('DISCLOSURE_REQUIRED_HOLD')
    return {'status':'PREPARED_NOT_EXECUTED','authority':'NONE','source_digest':verification['digest'],
            'source_ids':[s['source_id'] for s in bundle_snapshot['sources']],
            'claim_ids':[c['claim_id'] for c in bundle_snapshot['claims']],
            'required_human_approval':'CURRENT_HOST_AND_AFFECTED_PARTY',
            'identity_attested':False,'model_woken':False,'private_source_imported':False}

def fork_bundle(parent: Any, new_bundle_id: str, when_utc: str) -> dict:
    """Fork, preserving parent digest, source refs and candidate status. No mutation."""
    # Fork the same sanitized snapshot that was structurally verified; a
    # caller-defined __deepcopy__ must not silently substitute fork contents.
    parent_snapshot = _json_copy(parent)
    verification=verify_bundle(parent_snapshot)
    if not _id(new_bundle_id) or new_bundle_id==parent_snapshot['bundle_id']:_fail('FORK_ID_COLLISION_HOLD')
    candidate=parent_snapshot
    candidate.pop('integrity')
    candidate['parent']={'bundle_id':parent_snapshot['bundle_id'],'digest':verification['digest']}
    candidate['bundle_id']=new_bundle_id
    candidate['version']+=1
    candidate['created_at']=when_utc
    return seal_bundle(candidate)
