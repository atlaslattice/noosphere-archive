"""Bounded read-only adapters for existing R10 evidence and Iron Empire fiction.

Never republish/private-import bodies, rewrite upstream, infer a Wikipedia QID,
accept CANON, or promote historical candidate links to knowledge truth.
"""
from __future__ import annotations
from pathlib import Path
import hashlib,json,sqlite3,re
from .glyph import REGISTRY_SHA
from .core import OPENALEX_SHA


def _sha_file(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def inspect_r10_evidence_db(path)->dict:
    db=sqlite3.connect(f'file:{Path(path).resolve().as_posix()}?mode=ro',uri=True)
    try:
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        needed={'edition_pins','hsn_nodes','openalex_topics','topic_hsn_candidates','sources','wikidata_statements','candidates','decisions'}
        if not needed.issubset(tables):raise ValueError('R10_DATABASE_SCHEMA_INCOMPATIBLE')
        pins={name:digest for name,digest,*_ in db.execute('SELECT namespace,sha256,source_status FROM edition_pins')}
        if REGISTRY_SHA not in pins.values() or OPENALEX_SHA not in pins.values():raise ValueError('R10_EDITION_PIN_MISMATCH')
        counts={t:db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in needed}
        if counts['hsn_nodes']!=1728 or counts['openalex_topics']!=4516 or counts['topic_hsn_candidates']!=22580:raise ValueError('R10_COVERAGE_MISMATCH')
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('R10_SQLITE_INTEGRITY_FAIL')
        return {'schema':'atlas.meta145.r10-readonly/v1','source_db_sha256':_sha_file(path),
          'source_count':counts,'source_edition_pins_verified':True,
          'actual_wikimedia_pages_ingested':counts['sources'],
          'wikidata_claim_count':counts['wikidata_statements'],
          'candidate_review_count':counts['decisions'],
          'observed_wikimedia_source_existence':counts['sources']>0,
          'upstream_db_changed':False,'new_verified_semantic_links':0,
          'authority_effect':'NONE','canon_effect':'NONE'}
    finally:db.close()


def inspect_iron_empire_overlay(path)->dict:
    raw=Path(path).read_bytes();j=json.loads(raw)
    if j.get('schema')!='iron-empire.ariadne-house-review-overlay/v0.9' or j.get('registryDigest')!=REGISTRY_SHA:raise ValueError('FICTION_EDITION_MISMATCH')
    if tuple(j.get(k) for k in ('totalHouseSlots','totalSphereSlots','totalNodePositions'))!=(12,144,1728):raise ValueError('FICTION_DIMENSION_MISMATCH')
    if j.get('canonChanged') is not False or j.get('status')!='AUTHOR_REVIEW_REQUIRED' or j.get('completedFilmEdits')!=0 or j.get('approvedTopicLinks')!=0:raise ValueError('FICTION_AUTHORITY_PROMOTION_DENIED')
    houses=j.get('houses',[])
    if len(houses)!=12 or {v.get('house') for v in houses}!={f'H{x:02d}' for x in range(1,13)}:raise ValueError('FICTION_HOUSE_COUNT')
    if any(v.get('editorialAuthority')!='NONE' or v.get('reviewStatus')!='PROPOSED_ONLY' for v in houses):raise ValueError('FICTION_ROLE_CLAIM_DENIED')
    return {'schema':'atlas.meta145.iron-empire-review/v1', 'source_sha256':hashlib.sha256(raw).hexdigest(),
       'house_review_lenses':[{'house':x['house'],'lens':x['reviewLens'],'status':'FICTION_EDITORIAL_CANDIDATE_ONLY'} for x in houses],
       'actual_film_edits':0,'fiction_canon_approved':False,'original_private_fiction_imported':False,'authority_effect':'NONE'}
