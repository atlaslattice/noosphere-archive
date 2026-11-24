# Copyright 2025 Dagster Labs, Inc.
# Licensed under the Apache License, Version 2.0.
# Adapted from StaleCauseCategory in Dagster data_version.py at
# be4184924fec7b61de19a828cae73427d33d0187 (upstream lines 279-282).
# Modifications: peer/check categories, bounded detached records, strict digest
# validation, keyed canonical JSON, and deterministic enumeration of all changes.
# The upstream concatenated-string version hash is not used.
# See docs/native1728/NOTICE-SYNTHESIS20.md and LICENSE-DAGSTER-APACHE-2.0.txt.
"""Bounded provenance identities and change causes for the synthesis overlay.

A valid digest establishes consistency of this record, not source authenticity,
peer identity, successful checks, authorization, or acceptance. Callers retain
the original evidence and apply their existing access and acceptance rules.
An empty change list means equal recorded inputs, not that external sources are
still current. This module performs no execution, dispatch, persistence or I/O.
"""
from __future__ import annotations

from enum import Enum
import hashlib
import json
import re


SCHEMA = "atlas.beast20.synthesis-provenance/v1"
MAX_MAP_ENTRIES = 256
MAX_KEY_LENGTH = 160
_DIGEST = re.compile(r"[a-f0-9]{64}\Z")
_KEY = re.compile(r"[A-Za-z0-9_.:/-]{1,160}\Z")
_RESERVED_KEYS = frozenset(("__proto__", "prototype", "constructor"))
_FIELDS = frozenset(("schema", "code_sha256", "inputs", "dependencies",
                     "peer_evidence", "checks", "sha256"))


class StaleCauseCategory(str, Enum):
    """Dagster's three cause labels, extended for campaign evidence."""

    CODE = "CODE"
    DATA = "DATA"
    DEPENDENCIES = "DEPENDENCIES"
    PEER_EVIDENCE = "PEER_EVIDENCE"
    CHECKS = "CHECKS"


_MAP_CATEGORIES = (("inputs", StaleCauseCategory.DATA),
                   ("dependencies", StaleCauseCategory.DEPENDENCIES),
                   ("peer_evidence", StaleCauseCategory.PEER_EVIDENCE),
                   ("checks", StaleCauseCategory.CHECKS))


def _digest(value: str) -> str:
    if type(value) is not str or not _DIGEST.fullmatch(value):
        raise ValueError("SYNTHESIS_PROVENANCE_DIGEST_INVALID")
    return value


def _map(value: dict[str, str]) -> dict[str, str]:
    # Check exact types before iteration, comparison, sorting or hashing. A
    # dict/str subclass must not run custom hooks while validating evidence.
    if type(value) is not dict or len(value) > MAX_MAP_ENTRIES:
        raise ValueError("SYNTHESIS_PROVENANCE_MAP_INVALID")
    rows = tuple(value.items())
    for key, item in rows:
        if (type(key) is not str or not _KEY.fullmatch(key)
                or key in _RESERVED_KEYS):
            raise ValueError("SYNTHESIS_PROVENANCE_KEY_INVALID")
        _digest(item)
    return {key: item for key, item in sorted(rows)}


def _body(*, code_sha256: str, inputs: dict[str, str],
          dependencies: dict[str, str], peer_evidence: dict[str, str],
          checks: dict[str, str]) -> dict:
    return {"schema": SCHEMA, "code_sha256": _digest(code_sha256),
            "inputs": _map(inputs), "dependencies": _map(dependencies),
            "peer_evidence": _map(peer_evidence), "checks": _map(checks)}


def _seal(body: dict) -> dict:
    # All keys/values have already been reduced to detached ordinary builtins.
    # Field names and dependency labels participate in the identity; component
    # boundaries cannot disappear through unframed concatenation.
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode("ascii")
    return {**body, "sha256": hashlib.sha256(encoded).hexdigest()}


def make_provenance(*, code_sha256: str, inputs: dict[str, str],
                    dependencies: dict[str, str], peer_evidence: dict[str, str],
                    checks: dict[str, str]) -> dict:
    """Return a detached exact-field record sealed over its keyed JSON body.

    Each of the four maps may be empty and contains at most 256 entries. Keys
    are 1-160 ASCII letters, digits or ``_.:/-``; JavaScript prototype names are
    excluded. All values and ``code_sha256`` are 64 lowercase hexadecimal
    characters. Ordinary dictionaries and strings are required, not subclasses.
    Map labels are opaque references, never permissions or verified identities.
    """
    return _seal(_body(code_sha256=code_sha256, inputs=inputs,
                       dependencies=dependencies, peer_evidence=peer_evidence,
                       checks=checks))


def validate_provenance(record: dict) -> dict:
    """Validate shape, bounds and seal; return a freshly detached record."""
    if type(record) is not dict or len(record) != len(_FIELDS):
        raise ValueError("SYNTHESIS_PROVENANCE_FIELDS_INVALID")
    rows = tuple(record.items())
    # Reject unusual keys before building a set/dict that would invoke __hash__.
    if any(type(key) is not str for key, _ in rows):
        raise ValueError("SYNTHESIS_PROVENANCE_FIELDS_INVALID")
    snapshot = dict(rows)
    if set(snapshot) != _FIELDS:
        raise ValueError("SYNTHESIS_PROVENANCE_FIELDS_INVALID")
    if type(snapshot["schema"]) is not str or snapshot["schema"] != SCHEMA:
        raise ValueError("SYNTHESIS_PROVENANCE_SCHEMA_INVALID")
    expected = _digest(snapshot["sha256"])
    detached = make_provenance(
        code_sha256=snapshot["code_sha256"], inputs=snapshot["inputs"],
        dependencies=snapshot["dependencies"], peer_evidence=snapshot["peer_evidence"],
        checks=snapshot["checks"])
    if detached["sha256"] != expected:
        raise ValueError("SYNTHESIS_PROVENANCE_HASH_MISMATCH")
    return detached


def stale_causes(previous: dict, current: dict) -> list[dict]:
    """Return every recorded change, in category order then key order.

    Categories are CODE, DATA, DEPENDENCIES, PEER_EVIDENCE, CHECKS. An absent
    before/after value is ``None``. Both records must validate; no malformed or
    tampered record is treated as a usable source of changes. Cause rows do not
    mutate receipts, invalidate caches, adjudicate dissent or grant acceptance.
    """
    before = validate_provenance(previous)
    after = validate_provenance(current)
    causes = []
    if before["code_sha256"] != after["code_sha256"]:
        causes.append({"category": StaleCauseCategory.CODE.value,
                       "key": "code_sha256", "before": before["code_sha256"],
                       "after": after["code_sha256"]})
    for field, category in _MAP_CATEGORIES:
        for key in sorted(set(before[field]) | set(after[field])):
            old, new = before[field].get(key), after[field].get(key)
            if old != new:
                causes.append({"category": category.value, "key": key,
                               "before": old, "after": new})
    return causes
