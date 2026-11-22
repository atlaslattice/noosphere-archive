#!/usr/bin/env python3
"""Offline review-only validator for Noosphere evidence packets.

CANDIDATE ONLY: structure is not authority, truth, signed canon or deployment.
No external calls, no automatic Play/Imagine ingestion, no default writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "noosphere_evidence_packet_v0_1.schema.json"
RESTRICTED_SOURCE_MODES = {"play", "social", "imagine", "dream", "quiet"}
REQUIRES_SOURCE_REF = {"SourceSurface", "RawExportManifest", "Artifact", "Claim", "Evidence"}
EDGE_TYPES = {
    "derived_from": (
        {"RawExportManifest", "Artifact", "Claim", "Evidence", "Contradiction", "Delta", "ActionPacket", "Receipt", "Supersession"},
        {"SourceSurface", "RawExportManifest", "Artifact", "Claim", "Evidence", "Contradiction", "Delta"},
    ),
    "claims": ({"Artifact"}, {"Claim"}),
    "supports": ({"Evidence"}, {"Claim"}),
    "contradicts": ({"Evidence", "Contradiction"}, {"Claim", "Evidence"}),
    "reviewed_by": ({"Claim", "Delta", "Artifact"}, {"ReviewLane"}),
    "gated_by": ({"Claim", "ActionPacket", "Delta", "Artifact"}, {"CanonGate"}),
    "preserved_as": ({"Receipt", "Artifact", "Supersession"}, {"Artifact", "RawExportManifest"}),
    "quarantined_as": ({"Artifact", "Claim", "RawExportManifest"}, {"Receipt", "Artifact"}),
    "implemented_as": ({"Delta", "ActionPacket", "Claim"}, {"Artifact"}),
    "supersedes": ({"Delta", "Supersession", "Artifact"}, {"Artifact", "Claim", "Delta"}),
}


def load_unique_json(raw: bytes) -> Any:
    """Reject duplicate object keys, including nested duplicate authority keys."""
    def pairs_hook(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError(f"Duplicate JSON key: {key}")
            out[key] = value
        return out
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs_hook)


def inspect_packet(raw: bytes) -> dict[str, Any]:
    """Return an offline structural verdict. REVIEWABLE never means authorized."""
    digest = hashlib.sha256(raw).hexdigest()
    errors: list[str] = []
    try:
        packet = load_unique_json(raw)
    except (UnicodeError, ValueError) as exc:
        return {"disposition": "HOLD", "sha256": digest, "errors": [f"invalid JSON: {exc}"], "can_promote": False}

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errors.extend(
        f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
        for e in sorted(Draft202012Validator(schema).iter_errors(packet), key=lambda e: str(list(e.absolute_path)))
    )

    if isinstance(packet, dict):
        mode = packet.get("source_mode")
        if isinstance(mode, str) and mode.lower() in RESTRICTED_SOURCE_MODES:
            errors.append("Play/Social/Imagine/Dream/Quiet cannot be ingested as Work by declaration")
        nodes = packet.get("nodes")
        edges = packet.get("edges")
        if isinstance(nodes, list):
            ids: dict[str, str] = {}
            for i, node in enumerate(nodes):
                if not isinstance(node, dict):
                    continue
                node_id, kind = node.get("id"), node.get("type")
                if isinstance(node_id, str):
                    if node_id in ids:
                        errors.append(f"nodes[{i}]: duplicate node id {node_id}")
                    else:
                        ids[node_id] = kind
                if isinstance(kind, str) and kind in REQUIRES_SOURCE_REF and not node.get("source_ref"):
                    errors.append(f"nodes[{i}] ({kind}): source_ref is required")
            if isinstance(edges, list):
                seen = set()
                for i, edge in enumerate(edges):
                    if not isinstance(edge, dict):
                        continue
                    a, b, relation = edge.get("from"), edge.get("to"), edge.get("type")
                    if isinstance(a, str) and a not in ids:
                        errors.append(f"edges[{i}]: missing from node {a}")
                    if isinstance(b, str) and b not in ids:
                        errors.append(f"edges[{i}]: missing to node {b}")
                    if not all(isinstance(value, str) for value in (a, b, relation)):
                        continue  # JSON Schema already records malformed values
                    fingerprint = (a, b, relation)
                    if fingerprint in seen:
                        errors.append(f"edges[{i}]: duplicate edge")
                    seen.add(fingerprint)
                    allowed = EDGE_TYPES.get(relation)
                    if allowed and a in ids and b in ids:
                        src, dst = allowed
                        if not isinstance(ids[a], str) or not isinstance(ids[b], str) or ids[a] not in src or ids[b] not in dst:
                            errors.append(f"edges[{i}]: invalid node types for {relation}: {ids[a]} -> {ids[b]}")

    return {
        "disposition": "HOLD" if errors else "CANDIDATE_ONLY",
        "sha256": digest,
        "errors": errors,
        "can_promote": False,
        "can_claim_completeness": False,  # structural hashes do not prove remote bytes
        "source_mode_verified": False,
    }


def _write_once_or_identical(path: Path, payload: bytes) -> None:
    """Owner-controlled local preservation: never silently overwrite a review file.

    Exclusive creation prevents a second writer from replacing a preexisting file.
    This does not establish protection against a malicious directory owner or
    supply remote host authenticity/transactional durability.
    """
    if path.is_symlink():
        raise RuntimeError("refuse symlink in quarantine destination")
    try:
        with path.open("xb") as destination:
            destination.write(payload)
    except FileExistsError:
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise RuntimeError("existing quarantine record differs; preserve prior review")


def validate_file(path: Path, quarantine_dir: Path | None = None) -> dict[str, Any]:
    raw = path.read_bytes()
    verdict = inspect_packet(raw)
    if verdict["disposition"] == "HOLD" and quarantine_dir is not None:
        if quarantine_dir.is_symlink():
            raise RuntimeError("refuse symlink quarantine directory")
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        digest = verdict["sha256"]
        preserved = quarantine_dir / (digest + ".source")
        receipt = quarantine_dir / (digest + ".hold.json")
        _write_once_or_identical(preserved, raw)
        record = {
            "disposition": "HOLD",
            "sha256": digest,
            "byte_length": len(raw),
            "original_preserved": True,
            "review_required": True,
            "errors": verdict["errors"],
            "source_mode_verified": False,
            "canon": False,
            "deployed": False,
        }
        _write_once_or_identical(receipt, (json.dumps(record, indent=2) + "\n").encode("utf-8"))
        verdict["quarantine"] = {"source": str(preserved), "receipt": str(receipt)}
    return verdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("--quarantine-dir", type=Path, help="Optional owner-controlled local review destination")
    args = parser.parse_args(argv)
    verdict = validate_file(args.packet, args.quarantine_dir)
    print(json.dumps(verdict, indent=2))
    return 0 if verdict["disposition"] == "CANDIDATE_ONLY" else 2


if __name__ == "__main__":
    sys.exit(main())
