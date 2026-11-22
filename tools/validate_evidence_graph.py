#!/usr/bin/env python3
"""Fail-closed, offline validator for public Atlas evidence-graph candidates.

No network, private corpus reads, identity attestation, promotion or side effects.
This validator cannot establish rights grants, a signature or a human ratification.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA_VERSION = "atlas.evidence.graph/v0.1"
NODE_TYPES = frozenset({
    "SourceSurface", "RawExportManifest", "Artifact", "Claim", "Evidence",
    "Contradiction", "Delta", "ReviewLane", "CanonGate", "ActionPacket",
    "Receipt", "Supersession",
})
STATES = frozenset({"RAW", "PARSED", "CLAIM", "CANDIDATE", "REVIEWED", "RATIFIED", "CANON", "DEPLOYED"})
FLAGS = frozenset({"CONTRADICTED", "SUPERSEDED", "QUARANTINED"})
# Permitted sources/targets are intentionally narrow: new uses require source review.
EDGE_TYPES = {
    "derived_from": (None, {"SourceSurface", "RawExportManifest", "Artifact", "Evidence", "Claim"}),
    "claims": ({"Artifact"}, {"Claim"}),
    "supports": ({"Evidence"}, {"Claim"}),
    "contradicts": ({"Contradiction", "Evidence"}, {"Claim", "Evidence"}),
    "supersedes": ({"Supersession", "Artifact", "Claim", "Delta"}, {"Artifact", "Claim", "Delta"}),
    "reviewed_by": ({"Claim", "Delta", "Evidence"}, {"ReviewLane"}),
    "gated_by": ({"Claim", "Delta", "ActionPacket"}, {"CanonGate"}),
    "implemented_as": ({"Delta"}, {"ActionPacket", "Artifact"}),
    "preserved_as": ({"Artifact", "Claim", "Evidence", "Contradiction"}, {"Artifact", "Receipt", "RawExportManifest"}),
    "quarantined_as": ({"Artifact", "Claim", "Evidence"}, {"Artifact", "Receipt"}),
}
RAW_EXPORT_STATES = frozenset({"raw_missing", "raw_partial", "raw_complete_unhashed", "raw_complete_hashed", "raw_source_unavailable"})
SHA256 = re.compile(r"^[0-9a-f]{64}$")
IDENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:\-/]{0,159}$")


def validate_graph(doc):
    """Return machine-readable violation records, never silently coerce input."""
    errors = []

    def bad(path, code):
        errors.append({"path": path, "code": code})

    if not isinstance(doc, dict):
        return [{"path": "$", "code": "NOT_OBJECT"}]
    if doc.get("schema_version") != SCHEMA_VERSION:
        bad("schema_version", "SCHEMA_VERSION")
    if doc.get("purpose") != "PUBLIC_EVIDENCE_REVIEW":
        bad("purpose", "PURPOSE_BOUNDARY")
    if not isinstance(doc.get("graph_id"), str) or not IDENT.fullmatch(doc["graph_id"]):
        bad("graph_id", "INVALID_GRAPH_ID")
    nodes = doc.get("nodes")
    edges = doc.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        bad("nodes/edges", "INVALID_COLLECTION")
        return errors
    by_id = {}
    for i, n in enumerate(nodes):
        path = f"nodes[{i}]"
        if not isinstance(n, dict):
            bad(path, "INVALID_NODE")
            continue
        ident = n.get("id")
        if not isinstance(ident, str) or not IDENT.fullmatch(ident):
            bad(path + ".id", "INVALID_NODE_ID")
            continue
        if ident in by_id:
            bad(path + ".id", "DUPLICATE_NODE_ID")
        by_id[ident] = n
        node_type = n.get("type")
        if type(node_type) is not str or node_type not in NODE_TYPES:
            bad(path + ".type", "UNKNOWN_NODE_TYPE")
        if not isinstance(n.get("label"), str) or not n["label"].strip():
            bad(path + ".label", "MISSING_LABEL")
        stage = n.get("state")
        if type(stage) is not str or stage not in STATES:
            bad(path + ".state", "UNKNOWN_STATE")
        if type(stage) is str and stage in {"RATIFIED", "CANON", "DEPLOYED"}:
            bad(path + ".state", "HOST_ATTESTATION_REQUIRED")
        flags = n.get("flags", [])
        if not isinstance(flags, list) or any(not isinstance(f, str) or f not in FLAGS for f in flags):
            bad(path + ".flags", "INVALID_FLAGS")
        elif len(flags) != len(set(flags)):
            bad(path + ".flags", "DUPLICATE_FLAG")
        if n.get("type") == "RawExportManifest":
            raw_status = n.get("raw_export_status")
            if type(raw_status) is not str or raw_status not in RAW_EXPORT_STATES:
                bad(path + ".raw_export_status", "RAW_EXPORT_STATUS_REQUIRED")
            elif raw_status != "raw_complete_hashed" and "QUARANTINED" not in flags:
                bad(path + ".flags", "INCOMPLETE_RAW_REQUIRES_QUARANTINE")
            if raw_status == "raw_complete_hashed":
                if not isinstance(n.get("manifest_digest_sha256"), str) or not SHA256.fullmatch(n["manifest_digest_sha256"]):
                    bad(path + ".manifest_digest_sha256", "COMPLETE_EXPORT_REQUIRES_HASH")
                if not isinstance(n.get("source_root_ref"), str) or not n["source_root_ref"]:
                    bad(path + ".source_root_ref", "COMPLETE_EXPORT_REQUIRES_ROOT")
                if not isinstance(n.get("hash_receipt_ref"), str) or not n["hash_receipt_ref"]:
                    bad(path + ".hash_receipt_ref", "COMPLETE_EXPORT_REQUIRES_RECEIPT")
        if n.get("type") == "SourceSurface":
            src = n.get("source")
            if not isinstance(src, dict):
                bad(path + ".source", "SOURCE_PROVENANCE_REQUIRED")
            else:
                if not isinstance(src.get("url"), str) or not src["url"].startswith("https://"):
                    bad(path + ".source.url", "HTTPS_SOURCE_REQUIRED")
                if not isinstance(src.get("sha256"), str) or not SHA256.fullmatch(src["sha256"]):
                    bad(path + ".source.sha256", "SOURCE_HASH_REQUIRED")
                if not isinstance(src.get("rights"), str) or not src["rights"].strip():
                    bad(path + ".source.rights", "RIGHTS_UNKNOWN")
                scope = src.get("scope")
                if type(scope) is not str or scope not in {"PUBLIC_METADATA", "SYNTHETIC_FIXTURE"}:
                    bad(path + ".source.scope", "PRIVATE_OR_UNVERIFIED_SOURCE")
                if not isinstance(src.get("observed_at"), str) or not src["observed_at"].strip():
                    bad(path + ".source.observed_at", "OBSERVATION_DATE_REQUIRED")
    for ident, node in by_id.items():
        if node.get("type") == "RawExportManifest" and node.get("raw_export_status") == "raw_complete_hashed":
            source_ref, receipt_ref = node.get("source_root_ref"), node.get("hash_receipt_ref")
            src = by_id.get(source_ref) if type(source_ref) is str else None
            receipt = by_id.get(receipt_ref) if type(receipt_ref) is str else None
            if not src or src.get("type") != "SourceSurface":
                bad(f"nodes[{ident}].source_root_ref", "INVALID_SOURCE_ROOT_REF")
            if not receipt or receipt.get("type") != "Receipt":
                bad(f"nodes[{ident}].hash_receipt_ref", "INVALID_HASH_RECEIPT_REF")
    seen_edges = set()
    for i, e in enumerate(edges):
        path = f"edges[{i}]"
        if not isinstance(e, dict):
            bad(path, "INVALID_EDGE")
            continue
        src, target, kind = e.get("from"), e.get("to"), e.get("type")
        if any(type(value) is not str for value in (src, target, kind)):
            bad(path, "EDGE_FIELDS_MUST_BE_STRINGS")
            continue
        if src not in by_id or target not in by_id:
            bad(path, "DANGLING_EDGE")
            continue
        if src == target:
            bad(path, "SELF_EDGE")
        key = (src, kind, target)
        if key in seen_edges:
            bad(path, "DUPLICATE_EDGE")
        seen_edges.add(key)
        if kind not in EDGE_TYPES:
            bad(path + ".type", "UNKNOWN_EDGE_TYPE")
            continue
        allowed_sources, allowed_targets = EDGE_TYPES[kind]
        from_type, to_type = by_id[src].get("type"), by_id[target].get("type")
        if (type(from_type) is not str or type(to_type) is not str or
                (allowed_sources is not None and from_type not in allowed_sources) or
                to_type not in allowed_targets):
            bad(path + ".type", "INVALID_EDGE_DIRECTION")
    # A claim cannot become evidence solely by being assigned a label or graph edge.
    for ident, node in by_id.items():
        if node.get("type") == "Claim" and not any(
            e.get("to") == ident and e.get("type") == "supports" and e.get("from") in by_id
            for e in edges if isinstance(e, dict)
        ):
            bad(f"nodes[{ident}]", "CLAIM_LACKS_EVIDENCE_LINK")
        if node.get("type") == "Evidence" and not any(
            e.get("from") == ident and e.get("type") == "derived_from" and e.get("to") in by_id
            for e in edges if isinstance(e, dict)
        ):
            bad(f"nodes[{ident}]", "EVIDENCE_LACKS_SOURCE_LINK")
    return errors


def _reject_duplicate_keys(pairs):
    """Reject repeated object names before JSON loses their evidence."""
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("graph", type=Path, help="candidate JSON graph")
    args = parser.parse_args(argv)
    try:
        doc = json.loads(args.graph.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as e:
        print(json.dumps({"status": "INVALID", "errors": [{"path": "$", "code": "FILE_OR_JSON_ERROR"}]}))
        return 2
    violations = validate_graph(doc)
    print(json.dumps({"status": "LOCAL_SHAPE_PASS_NOT_APPROVED" if not violations else "HELD", "errors": violations}, indent=2, sort_keys=True))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())