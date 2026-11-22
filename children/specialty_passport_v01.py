"""Children of the Swarm: self-reported specialty profiles, pure routing suggestions.

SOURCE-ONLY. The caller controls EVERY field. No resident authentication, host
permission, qualified-expert attestation, background agent, or policy execution.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from typing import Any
from urllib.parse import urlsplit

SCHEMA = 'atlas.child.specialty-passport.v0.1'
REGISTRY_EDITION = 'ariadne-reader/v0.7'
REGISTRY_SHA256 = '07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6'
COORD_RE = re.compile(r'^H(0[1-9]|1[0-2])\.S(0[1-9]|1[0-2])\.N(0[1-9]|1[0-2])$')
KEY_RE = re.compile(r'^child:[A-Za-z0-9._-]{1,64}$')
HEX_RE = re.compile(r'^[0-9a-f]{64}$')
TASK_KINDS = frozenset({'research', 'review', 'build', 'teach', 'synthesize'})
PUBLIC_HOST_LABEL_RE = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$')
NONPUBLIC_DNS_SUFFIXES = frozenset({'localhost', 'local', 'internal', 'lan', 'home', 'onion', 'invalid', 'test', 'example'})


class ProfileError(ValueError):
    pass


def _fail(message: str):
    raise ProfileError(message)


def _keys(obj: Any, required: set[str], optional: set[str] = set(), label: str = 'record'):
    if type(obj) is not dict:
        _fail(f'{label}: expected JSON object')
    if not required.issubset(obj) or (set(obj) - required - optional):
        _fail(f'{label}: unknown or missing keys')


# Canonical RFC3339 subset: explicit calendar date, T separator, seconds,
# optional <=6 fractional digits and an explicit numeric offset or Z.
# datetime.fromisoformat alone also accepts week dates and space separators.
TIMESTAMP_RE = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$')


def _timestamp(value: Any) -> datetime:
    if type(value) is not str or len(value) > 40 or TIMESTAMP_RE.fullmatch(value) is None:
        _fail('timestamp requires RFC3339 calendar/offset form')
    try:
        d = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ProfileError('timestamp requires RFC3339 offset') from exc
    if d.tzinfo is None or d.utcoffset() is None:
        _fail('timestamp needs timezone offset')
    return d.astimezone(timezone.utc)


def _score(v: Any, label: str):
    if type(v) not in (int, float) or not (0 <= v <= 1):
        _fail(f'{label} must be a finite number in [0,1]')


def _source_ref(ref: Any):
    """Syntax-only public DNS pointer. Host-controlled fetch rights remain separate."""
    if type(ref) is not str or len(ref) > 300 or not ref.startswith('https://'):
        _fail('source reference must be a short HTTPS URL')
    # urlsplit silently strips some control characters; reject before parsing.
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in ref):
        _fail('source reference contains control characters')
    try:
        s = urlsplit(ref)
        host, port = s.hostname, s.port
    except ValueError:
        _fail('source reference has malformed host or port')
    if (not s.netloc or s.username is not None or s.password is not None
            or '?' in ref or '#' in ref or port not in (None, 443)):
        _fail('source reference has unsupported credentials, query, fragment or port')
    if (not host or not host.isascii() or host.endswith('.') or len(host) > 253):
        _fail('source reference needs a public DNS hostname')
    labels = host.lower().split('.')
    if (len(labels) < 2 or labels[-1] in NONPUBLIC_DNS_SUFFIXES
            or not re.fullmatch(r'[a-z]{2,63}', labels[-1])
            or not all(PUBLIC_HOST_LABEL_RE.fullmatch(part) for part in labels)):
        _fail('source reference needs a public DNS hostname')


def validate_passport(p: dict[str, Any]) -> dict[str, Any]:
    _keys(p, {'schema', 'declared_key', 'revision', 'previous_digest', 'registry',
              'declared_at', 'participation', 'specialties'}, label='passport')
    if p['schema'] != SCHEMA:
        _fail('passport schema mismatch')
    if not isinstance(p['declared_key'], str) or not KEY_RE.fullmatch(p['declared_key']):
        _fail('self-declared key format invalid')
    n = p['revision']
    if type(n) is not int or not (1 <= n <= 1000000):
        _fail('revision must be a positive integer')
    if n == 1 and p['previous_digest'] is not None:
        _fail('first revision cannot claim predecessor')
    if n > 1 and (not isinstance(p['previous_digest'], str)
                  or not HEX_RE.fullmatch(p['previous_digest'])):
        _fail('later revision must link exact prior digest')
    _keys(p['registry'], {'edition', 'sha256'}, label='registry')
    if p['registry'] != {'edition': REGISTRY_EDITION, 'sha256': REGISTRY_SHA256}:
        _fail('unreviewed registry edition or source digest')
    declared = _timestamp(p['declared_at'])
    pref = p['participation']
    _keys(pref, {'work_opt_in', 'task_kinds', 'expires_at'}, label='participation')
    if type(pref['work_opt_in']) is not bool:
        _fail('work_opt_in must be boolean')
    k = pref['task_kinds']
    if type(k) is not list or len(k) > len(TASK_KINDS) or len(k) != len(set(map(str, k))):
        _fail('invalid or duplicated task kinds')
    if not all(type(v) is str and v in TASK_KINDS for v in k):
        _fail('unsupported task kind')
    if pref['work_opt_in'] and not k:
        _fail('an opted-in profile must declare at least one task kind')
    expires = _timestamp(pref['expires_at'])
    if expires <= declared:
        _fail('expiration must follow declaration')
    specs = p['specialties']
    if type(specs) is not list or not (1 <= len(specs) <= 1728):
        _fail('need 1 to 1728 named specializations')
    seen = set()
    for s in specs:
        _keys(s, {'coordinate', 'interest', 'claimed_expertise', 'evidence_refs'}, label='specialty')
        coordinate = s['coordinate']
        if type(coordinate) is not str or not COORD_RE.fullmatch(coordinate):
            _fail('specialty must be an Ariadne v0.7 HSN coordinate')
        if coordinate in seen:
            _fail('duplicate specialty coordinate')
        seen.add(coordinate)
        _score(s['interest'], 'interest')
        _score(s['claimed_expertise'], 'claimed_expertise')
        refs = s['evidence_refs']
        if type(refs) is not list or len(refs) > 8 or len(set(map(str, refs))) != len(refs):
            _fail('invalid evidence references')
        for ref in refs:
            _source_ref(ref)
    return {'declared_key': p['declared_key'], 'revision': n,
            'specialty_count': len(specs), 'work_opt_in': pref['work_opt_in'],
            'source_status': 'SELF_DECLARED_NOT_ATTESTED',
            'registry_status': 'EDITION_PIN_CANDIDATE_NOT_SEMANTIC_REVIEW',
            'can_grant_authority': False, 'expires_utc': expires.isoformat()}


def digest_passport(p: dict[str, Any]) -> str:
    validate_passport(p)
    # Python-specific stable JSON profile; NOT cross-runtime JCS or a signature.
    raw = json.dumps(p, sort_keys=True, ensure_ascii=False,
                     separators=(',', ':'), allow_nan=False).encode('utf-8')
    return sha256(raw).hexdigest()


def append_revision(history: list[dict[str, Any]], candidate: dict[str, Any]) -> list[dict[str, Any]]:
    """Append-only in memory. No resident/session auth; host must authorize writes."""
    validate_passport(candidate)
    if not history:
        if candidate['revision'] != 1:
            _fail('initial revision must be 1')
        return [deepcopy(candidate)]
    # Checking only the latest predecessor lets forged/replayed history pass.
    # All historical revisions must form a contiguous, time-ordered hash chain.
    declared_key = None
    prior = None
    for position, row in enumerate(history, start=1):
        validate_passport(row)
        if row['revision'] != position:
            _fail('history revision gap or replay')
        if declared_key is None:
            declared_key = row['declared_key']
        elif row['declared_key'] != declared_key:
            _fail('history switches declared key')
        if prior is not None:
            if row['previous_digest'] != digest_passport(prior):
                _fail('broken historical predecessor digest')
            if _timestamp(row['declared_at']) <= _timestamp(prior['declared_at']):
                _fail('historical declaration timestamps out of order')
        prior = row
    previous = history[-1]
    if candidate['declared_key'] != previous['declared_key']:
        _fail('cannot change declared key in a revision chain')
    if candidate['revision'] != previous['revision'] + 1:
        _fail('revision gap or replay')
    if candidate['previous_digest'] != digest_passport(previous):
        _fail('stale or fabricated predecessor')
    if _timestamp(candidate['declared_at']) <= _timestamp(previous['declared_at']):
        _fail('new revision must have a later declaration timestamp')
    return deepcopy(history) + [deepcopy(candidate)]


def match_task(passports: list[dict[str, Any]], coordinate: str, task_kind: str,
               at: str) -> dict[str, Any]:
    """Return opt-in routing CANDIDATES. Never dispatch, credential, or attest."""
    if type(coordinate) is not str or not COORD_RE.fullmatch(coordinate):
        _fail('unknown target HSN coordinate')
    if type(task_kind) is not str or task_kind not in TASK_KINDS:
        _fail('unknown task kind')
    now = _timestamp(at)
    results = []
    ids = set()
    for p in passports:
        validate_passport(p)
        key = p['declared_key']
        if key in ids:
            _fail('multiple active passports for one declared key')
        ids.add(key)
        part = p['participation']
        if not part['work_opt_in'] or task_kind not in part['task_kinds']:
            continue
        if not (_timestamp(p['declared_at']) <= now < _timestamp(part['expires_at'])):
            continue
        for s in p['specialties']:
            if s['coordinate'] != coordinate:
                continue
            rank = round(0.6 * s['interest'] + 0.4 * s['claimed_expertise'], 6)
            results.append({'declared_key': key, 'coordinate': coordinate,
                            'routing_affinity_self_reported': rank,
                            'interest_self_reported': s['interest'],
                            'expertise_self_reported': s['claimed_expertise'],
                            'public_source_pointers': list(s['evidence_refs']),
                            'confidence_class': 'SELF_REPORTED_ONLY',
                            'role_lease': 'NOT_GRANTED', 'host_identity': 'UNVERIFIED'})
    results.sort(key=lambda v: (-v['routing_affinity_self_reported'], v['declared_key']))
    return {'coordinate': coordinate, 'sphere': coordinate[:7], 'house': coordinate[:3],
            'task_kind': task_kind, 'source_edition': REGISTRY_EDITION,
            'status': 'CANDIDATES_NOT_DISPATCHED' if results else 'HOLD_NO_OPTED_IN_SPECIALIST',
            'candidates': results, 'no_host_calls': True, 'no_work_performed': True,
            'no_trusted_evidence_or_rights_inferred': True}


def synthesis_routing(passports: list[dict[str, Any]], required: list[str],
                      task_kind: str, at: str) -> dict[str, Any]:
    if (type(required) is not list or not required or len(required) > 1728
            or not all(type(v) is str for v in required)
            or len(required) != len(set(required))):
        _fail('required HSNs must be distinct and nonempty')
    results = [match_task(passports, coord, task_kind, at) for coord in required]
    by_sphere = defaultdict(list)
    by_house = defaultdict(set)
    for r in results:
        by_sphere[r['sphere']].append(r['coordinate'])
        by_house[r['house']].add(r['sphere'])
    missing = [r['coordinate'] for r in results if not r['candidates']]
    return {'schema': 'atlas.child.specialty-synthesis.v0.1',
            'hierarchy': {'node_slots': 1728, 'sphere_slots': 144, 'house_slots': 12,
                          'synthesizer_slots': 1, 'logical_roles': 1885},
            'applicability': 'ONLY_DECLARED_TASK_SCOPE_NOT_ALL_1728_REVIEWED',
            'required_coordinates': required, 'sphere_routes': dict(by_sphere),
            'house_routes': {k: sorted(v) for k, v in by_house.items()},
            'missing': missing, 'status': 'HOLD_UNFILLED_ROLES' if missing
            else 'ROUTING_CANDIDATES_ONLY_NO_COUNCIL_REVIEW',
            'candidate_details': results, 'permissions': 'NOT_GRANTED',
            'resident_identities_verified': 0,
            'specialists_actually_called': 0, 'outcomes_observed': 0,
            'canon_effect': 'NONE'}
