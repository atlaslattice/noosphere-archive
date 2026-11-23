#!/usr/bin/env python3
"""Independently audit a source-only Atlas cascade ledger.

No imports from Node implementation, no network, accounts, model calls or host claims.
SHA-256 chains are NOT identity signatures or live-platform receipts.
"""
from __future__ import annotations
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

SCHEMA = "atlas.cascade.synthetic-work.v1"
ZERO = "0" * 64
ACTIONS = (
    "POST", "READ", "WRONG_MODE", "WRONG_TENANT", "REVOKE", "READ_REVOKED",
    "REGRANT", "POST", "REPLAY", "CAS", "STALE_CAS", "WRONG_DIGEST",
    "WRONG_ACCOUNT", "STALE_EPOCH", "FAKE_WAKE", "EXPIRED_CALLBACK",
    "SOURCE_ALIAS", "RETURN", "UNTRUSTED_SIGNER", "PRIVATE_ORIGIN"
)
EXPECTED_ENTRY_FIELDS = frozenset((
    "schema", "index", "phase", "kind", "coordinate", "parent", "caseDigest",
    "outcome", "effect", "stateDigest", "regressions", "hostVerified",
    "modelWakeVerified", "canonAccepted", "hash"
))


def canon(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      allow_nan=False, separators=(",", ":")).encode("utf-8")


def sha(value):
    return hashlib.sha256(canon(value)).hexdigest()


def hsn(index):
    j = ((index - 1) * 613 + 193) % 1728
    return f"H{j // 144 + 1:02d}.S{j % 144 // 12 + 1:02d}.N{j % 12 + 1:02d}"


def audit(stage100, full, summary):
    assert isinstance(stage100, dict) and isinstance(full, dict) and isinstance(summary, dict)
    a = stage100["ledger"]
    rows = full["ledger"]
    if len(a) != 100 or len(rows) != 1100 or rows[:100] != a:
        raise ValueError("phases not continuous or not 100+1000")
    if full["state"]["trial"] != 1100 or stage100["state"]["trial"] != 100:
        raise ValueError("state and source trial count diverge")
    prev = ZERO
    seen = set()
    outcomes = Counter()
    houses = Counter()
    for i, e in enumerate(rows, start=1):
        if type(e) is not dict or frozenset(e) != EXPECTED_ENTRY_FIELDS:
            raise ValueError("unrecognized receipt fields at %d" % i)
        phase = "PRIMARY_100" if i <= 100 else "DESCENDANTS_1000"
        if (e["schema"] != SCHEMA or e["index"] != i or e["parent"] != prev
                or e["phase"] != phase or e["kind"] != ACTIONS[(i-1) % len(ACTIONS)]
                or e["coordinate"] != hsn(i) or e["regressions"] != i):
            raise ValueError("source/phase/parent mismatch at %d" % i)
        if (e["hostVerified"] is not False or e["modelWakeVerified"] is not False
                or e["canonAccepted"] is not False
                or e["effect"] not in ("LOCAL_SYNTHETIC_ONLY", "NONE")):
            raise ValueError("fabricated authority or effects at %d" % i)
        if e["coordinate"] in seen:
            raise ValueError("duplicate HSN address")
        seen.add(e["coordinate"])
        houses[e["coordinate"][:3]] += 1
        obj = dict(e)
        obj.pop("hash")
        expected = sha(obj)
        if expected != e["hash"]:
            raise ValueError("invalid receipt SHA at %d" % i)
        prev = e["hash"]
        outcomes[e["outcome"]] += 1
        if i == 100 and (e["hash"] != stage100["head"]
                         or e["hash"] != full["phase100"]["head"]):
            raise ValueError("stage100 checkpoint mismatch")
    if (prev != full["head"] or full["regressionEvaluations"] != 1100 * 1101 // 2
            or len(full["regressions"]) != 1100
            or len(full["observedAddresses"]) != 1100
            or len(set(full["observedAddresses"])) != 1100):
        raise ValueError("terminal state mismatch")
    work = full["state"]["workPosts"]
    if len(work) != 110 or len({p["requestId"] for p in work}) != len(work):
        raise ValueError("Work fixture post index conflict")
    for i, p in enumerate(work, start=1):
        if (p["seq"] != i or p["mode"] != "WORK" or p["origin"] != "LOCAL_FIXTURE"
                or "body" in p or "privatePayload" in p):
            raise ValueError("private or reordered Work fixture")
    if full["state"]["boardRevision"] != 55 or len(full["state"]["boardHistory"]) != 55:
        raise ValueError("CAS history mismatch")
    old = ZERO
    for i, x in enumerate(full["state"]["boardHistory"], start=1):
        if x["revision"] != i or x["prior"] != old or x["authority"] != "NONE":
            raise ValueError("invalid Workboard lineage")
        old = x["head"]
    if old != full["state"]["boardHead"]:
        raise ValueError("invalid Workboard tip")
    if any(x["relation"] != "CANDIDATE_NOT_SAME_AS" or x["authority"] != "NONE"
           for x in full["state"]["candidateLinks"]):
        raise ValueError("semantic edge upgraded without review")
    if (summary["trials"] != 1100 or summary["phase1"] != 100 or summary["phase2"] != 1000
            or summary["regressionEvaluations"] != 605550 or summary["terminalHead"] != prev
            or summary["phase100Head"] != stage100["head"]
            or summary["uniqueStructuralHsnAddresses"] != 1100
            or summary["productionPromotionAllowed"] is not False
            or summary["hostModelWakeCalls"] != 0 or summary["realIndependentWorkTurns"] != 0
            or summary["verifiedPeerMessages"] != 0 or summary["privateModeBodiesConsumed"] != 0
            or summary["sourceOnlyOutcomes"] != dict(outcomes)
            or summary["houses"] != dict(houses)):
        raise ValueError("summary overclaim or mismatch")
    return {"status": "INDEPENDENT_PYTHON_SOURCE_AUDIT_PASS_NOT_HOST_PROOF",
            "trials": len(rows), "stage100": stage100["head"], "terminal": prev,
            "distinct_hsn": len(seen), "houses": len(houses),
            "regression_evaluations": 605550,
            "authority": "NONE", "model_wakes": 0, "deployed": False}


def main():
    if len(sys.argv) != 4:
        raise SystemExit("Usage: python tools/audit_atlas_cascade.py dist/stage100.json dist/stage1100.json dist/summary.json")
    with Path(sys.argv[1]).open(encoding="utf-8") as f: p = json.load(f)
    with Path(sys.argv[2]).open(encoding="utf-8") as f: e = json.load(f)
    with Path(sys.argv[3]).open(encoding="utf-8") as f: s = json.load(f)
    print(json.dumps(audit(p,e,s), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
