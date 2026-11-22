"""Noosphere PR14/PR17 source-only compatibility probe.

This detects incompatible wire shapes, not semantic equivalence. It never
performs migrations, host permission checks, CANON updates, or private ingestion.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

SCHEMA = 'atlas.noosphere.contract-crosswalk/v0.1'
VARIANTS = frozenset({'PR14_GRAPH', 'PR17_PACKET'})
PR14_SCHEMA = 'atlas.evidence.graph/v0.1'


def _unique(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise ValueError('DUPLICATE_JSON_KEY')
        out[k]=v
    return out

def _reject(c):raise ValueError('NONFINITE_JSON:'+c)

def load_raw(raw:bytes)->dict:
    if type(raw) is not bytes:raise TypeError('EXACT_BYTES_REQUIRED')
    if len(raw)>1024*1024:raise ValueError('SOURCE_TOO_LARGE')
    p=json.loads(raw.decode('utf-8'),object_pairs_hook=_unique,parse_constant=_reject)
    if type(p) is not dict:raise ValueError('OBJECT_REQUIRED')
    return p


def _safe_list(x):return type(x) is list

def inspect(raw:bytes,variant:str)->dict[str,Any]:
    if variant not in VARIANTS:raise ValueError('EXPLICIT_SOURCE_VARIANT_REQUIRED')
    digest=sha256(raw).hexdigest()
    try: p=load_raw(raw)
    except (UnicodeError,ValueError,TypeError) as e:
        return {'schema':SCHEMA,'source_variant':variant,'source_sha256':digest,
                'status':'HOLD_INVALID_SOURCE','reasons':[type(e).__name__],
                'authority_effect':'NONE','semantic_equal':False,'migration_authorized':False}
    if variant=='PR17_PACKET' and isinstance(p.get('source_mode'), str) and p['source_mode'].lower() in {'play','social','imagine','dream','quiet','brain','palace','habitat','no_harvest'}:
        return {'schema':SCHEMA,'source_variant':variant,'source_sha256':digest,
                'status':'HOLD_PRIVATE_BOUNDARY','reasons':['PRIVATE_MODE_NOT_WORK_SOURCE'],
                'authority_effect':'NONE','semantic_equal':False,'migration_authorized':False}
    problems=[]
    if variant=='PR14_GRAPH':
        if p.get('schema_version')!=PR14_SCHEMA:problems.append('WRONG_PR14_EDITION')
        if p.get('purpose')!='PUBLIC_EVIDENCE_REVIEW':problems.append('PURPOSE_NOT_PUBLIC_REVIEW')
        if type(p.get('graph_id')) is not str or not p['graph_id']:problems.append('GRAPH_ID_MISSING')
        fields={'graph_id','purpose','nodes','edges'}
        extra={'export_root_status':'NOT_DEFINED_AT_GRAPH_ROOT','rights_field':'NOT_DEFINED_AT_GRAPH_ROOT',
               'lifecycle_style':'NODE_STAGES_AND_ADVERSE_FLAGS'}
    else:
        if p.get('schema_version')!='0.1.0':
            problems.append('WRONG_PR17_EDITION')
        if p.get('source_mode') not in {'public','consented_work','synthetic'}:problems.append('SOURCE_MODE_NOT_PERMITTED')
        if p.get('raw_export_status')!='raw_complete_hashed':problems.append('RAW_EXPORT_NOT_COMPLETE_HASHED')
        fields={'source_mode','raw_export_status','source_roots','lifecycle','nodes','edges'}
        extra={'export_root_status':p.get('raw_export_status','UNKNOWN'),
               'rights_field':'DECLARED_NOT_HOST_VERIFIED',
               'lifecycle_style':'PACKET_LIFECYCLE_OBJECT'}
    if not fields.issubset(p):problems.append('MISSING_VARIANT_FIELDS')
    if not _safe_list(p.get('nodes')) or not _safe_list(p.get('edges')):
        problems.append('MISSING_NODE_OR_EDGE_LIST')
    node_count=len(p['nodes']) if _safe_list(p.get('nodes')) else None
    edge_count=len(p['edges']) if _safe_list(p.get('edges')) else None
    # Root counts are only shape hints; they do NOT establish graph identity.
    return {'schema':SCHEMA,'source_variant':variant,'source_sha256':digest,
            'source_shape_valid':not problems,
            'status':'HOLD_CONTRACT_RECONCILIATION' if not problems else 'HOLD_SOURCE_SHAPE',
            'reasons':sorted(set(problems)) or ['DIFFERENT_WIRE_SHAPES_REVIEW_REQUIRED'],
            'observed_node_count':node_count,'observed_edge_count':edge_count,
            'variant_fields':sorted(fields),'boundary_notes':extra,
            'authority_effect':'NONE','semantic_equal':False,'migration_authorized':False,
            'source_content_exported':False,'host_rights_verified':False}


def compare(a:bytes,b:bytes)->dict:
    """Cannot auto-convert two different schemas or turn cardinality into meaning."""
    ga=inspect(a,'PR14_GRAPH');pb=inspect(b,'PR17_PACKET')
    holds=[]
    if not ga.get('source_shape_valid') or not pb.get('source_shape_valid'):
        holds.append('AT_LEAST_ONE_SOURCE_SHAPE_INCOMPLETE')
    if ga.get('observed_node_count')!=pb.get('observed_node_count'):
        holds.append('NODE_CARDINALITY_DIVERGES')
    if ga.get('observed_edge_count')!=pb.get('observed_edge_count'):
        holds.append('EDGE_CARDINALITY_DIVERGES')
    holds.extend(['NO_COMMON_VALIDATED_SOURCE_ROOT','EDGE_PREDICATE_DIRECTION_UNREVIEWED',
                  'LIFECYCLE_STAGE_FLAG_SEMANTICS_UNREVIEWED',
                  'HOST_RIGHTS_AND_ORIGINAL_CONTENT_NOT_VERIFIED'])
    return {'schema':SCHEMA,'status':'HOLD_WIRE_RECONCILIATION',
            'variant_digests':{'PR14_GRAPH':ga['source_sha256'],'PR17_PACKET':pb['source_sha256']},
            'holds':holds,'source_records_preserved':2,'semantic_equal':False,
            'migration_authorized':False,'publishable':False,'canon':False,
            'deployment':False,'authority_effect':'NONE'}


def main():
    cli=argparse.ArgumentParser()
    cli.add_argument('--pr14',required=True);cli.add_argument('--pr17',required=True)
    a=cli.parse_args()
    print(json.dumps(compare(Path(a.pr14).read_bytes(),Path(a.pr17).read_bytes()),indent=2))

if __name__=='__main__':main()