"""SwarmHub source-only reference contracts, not the deployed authorization plane.

The public module intentionally has NO network, filesystem, cloud, credential, model,
CANON-writing, account-principal or private-mode-reading methods. In-memory receipts
are useful for tests, NOT durable persistence, independent signatures or authority.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Any, Mapping


class ValidationError(ValueError):
    """Schema violation; caller must retain and quarantine original payload."""


def digest(value: Any) -> str:
    """Python-local deterministic hash; not RFC8785 or cross-runtime canonical proof."""
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(raw.encode("utf-8")).hexdigest()


RAW_EXPORT_STATES = frozenset({
    "raw_missing", "raw_partial", "raw_complete_unhashed",
    "raw_complete_hashed", "raw_source_unavailable",
})
STAGES = frozenset({
    "RAW", "PARSED", "CLAIM", "CANDIDATE", "REVIEWED", "CONTRADICTED",
    "SUPERSEDED", "QUARANTINED", "RATIFIED", "CANON", "DEPLOYED",
})
GRAPH_NODES = frozenset({
    "SourceSurface", "RawExportManifest", "Artifact", "Claim", "Evidence",
    "Contradiction", "Delta", "ReviewLane", "CanonGate", "ActionPacket",
    "Receipt", "Supersession",
})
GRAPH_EDGES = frozenset({
    "derived_from", "claims", "supports", "contradicts", "supersedes",
    "reviewed_by", "gated_by", "implemented_as", "preserved_as", "quarantined_as",
})
SAFE_ACTIONS = frozenset({"DRAFT", "REVIEW", "RESEARCH", "TEST_LOCAL", "PREPARE"})


@dataclass(frozen=True)
class IngestionResult:
    state: str
    reasons: tuple[str, ...]
    payload: Any
    payload_digest: str | None
    authority: str = "none"


def validate_ingestion(packet: Any) -> IngestionResult:
    """Validate caller-reported export metadata; never claim source was fully read.

    Even a 'raw_complete_hashed' report has status SOURCE_REPORTED_ONLY because
    this function does not independently retrieve original archive bytes.
    """
    original = deepcopy(packet)
    problems: list[str] = []
    if not isinstance(packet, dict):
        problems.append("packet_not_object")
        status = None
    else:
        status = packet.get("raw_export_status")
        if type(status) is not str or status not in RAW_EXPORT_STATES:
            problems.append("raw_export_status_missing_or_invalid")
        if packet.get("claim_complete") is True and status != "raw_complete_hashed":
            problems.append("claim_complete_without_hashed_export")
        if packet.get("canon") is True or packet.get("deployment") is True:
            problems.append("ingestion_packet_claimed_normative_authority")
        if not isinstance(packet.get("source_root"), str) or not packet.get("source_root"):
            problems.append("source_root_missing")
        if status == "raw_complete_hashed":
            manifest = packet.get("source_root_manifest")
            if not isinstance(manifest, dict) or not manifest:
                problems.append("manifest_missing")
            else:
                for path, hash_value in manifest.items():
                    if not isinstance(path, str) or not path or not isinstance(hash_value, str) or re.fullmatch(r"[a-f0-9]{64}", hash_value) is None:
                        problems.append("manifest_entry_invalid")
                        break
            if not isinstance(packet.get("whole_export_sha256"), str) or re.fullmatch(r"[a-f0-9]{64}", packet.get("whole_export_sha256", "")) is None:
                problems.append("whole_export_digest_missing")
    try:
        hashed = digest(original)
    except (TypeError, ValueError):
        hashed = None
        problems.append("payload_not_json_serializable")
    return IngestionResult("QUARANTINED" if problems else "SOURCE_REPORTED_ONLY", tuple(dict.fromkeys(problems)), original, hashed)


class PreservationLedger:
    """In-memory append-only receipt example: no erasure and no live storage proof."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.snapshots: dict[str, dict[str, Any]] = {}
        self.current: dict[str, str] = {}

    def transition(self, artifact_id: str, operation: str, value: Mapping[str, Any] | None, *, request_id: str) -> dict[str, Any]:
        if not isinstance(artifact_id, str) or not artifact_id or not isinstance(request_id, str) or not request_id:
            raise ValidationError("artifact_id/request_id_required")
        if any(e["request_id"] == request_id for e in self.events):
            raise ValidationError("duplicate_request_id_hold")
        if not isinstance(operation, str):
            raise ValidationError("operation_must_be_string")
        requested = operation.upper()
        if requested not in {"CREATE", "ANNOTATE", "REVISE", "SUPERSEDE", "QUARANTINE", "FORK", "DELETE", "OVERWRITE"}:
            raise ValidationError("unknown_transition_hold")
        if requested == "CREATE" and artifact_id in self.current:
            raise ValidationError("create_collision_hold")
        if requested != "CREATE" and artifact_id not in self.current:
            raise ValidationError("missing_original_hold")
        before = self.current.get(artifact_id)
        if requested in {"DELETE", "OVERWRITE"}:
            applied = "QUARANTINE"
        else:
            applied = requested
        if applied == "QUARANTINE":
            after_doc = deepcopy(self.snapshots[before]) if before else {"id": artifact_id}
            after_doc["lifecycle"] = "QUARANTINED"
            after_doc["reason"] = "destructive_intent_preserved" if requested in {"DELETE", "OVERWRITE"} else "review_required"
        else:
            if value is None or not isinstance(value, Mapping):
                raise ValidationError("new_state_required")
            after_doc = deepcopy(dict(value))
            if applied == "SUPERSEDE":
                after_doc["supersedes_sha256"] = before
            elif applied == "FORK":
                after_doc["forked_from_sha256"] = before
        after = digest(after_doc)
        self.snapshots.setdefault(after, after_doc)
        receipt = {
            "artifact_id": artifact_id, "request_id": request_id, "requested": requested,
            "applied": applied, "before_sha256": before, "after_sha256": after,
            "receipt_index": len(self.events), "previous_receipt_sha256": digest(self.events[-1]) if self.events else None,
            "authority": "none", "deployment": False, "canon": False,
        }
        self.events.append(deepcopy(receipt))
        self.current[artifact_id] = after
        return deepcopy(receipt)

    def preserved(self, sha: str) -> dict[str, Any] | None:
        return deepcopy(self.snapshots.get(sha))


class CoordinateResolver:
    """HSN routing address validator; H00 is a grounding sentinel, not HSN node 1729."""
    HSN = re.compile(r"^H(?:0[1-9]|1[0-2])\.S(?:0[1-9]|1[0-2])\.N(?:0[1-9]|1[0-2])$")
    EARTH = "H00.S00.N00"
    SOURCE_SHA256 = "07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6"

    def resolve_to_earth(self, claim: Mapping[str, Any]) -> dict[str, Any]:
        original = deepcopy(dict(claim))
        hsn = original.get("hsn")
        source_edition = original.get("source_edition")
        source_digest = original.get("source_digest")
        valid = isinstance(hsn, str) and self.HSN.fullmatch(hsn) is not None
        valid = valid and source_edition == "ariadne-reader/v0.7" and source_digest == self.SOURCE_SHA256
        return {
            "status": "SOURCE_ADDRESSED_NOT_SEMANTICALLY_VERIFIED" if valid else "QUARANTINED_GROUNDING_HOLD",
            "source_hsn": hsn, "earth_anchor": self.EARTH, "earth_anchor_is_ontology_node": False,
            "d_affinity": deepcopy(original.get("d_affinity")),
            "source_edition": source_edition, "source_digest": source_digest,
            "original": original, "authority": "none",
        }

    def validate_grounding(self, resolved: Mapping[str, Any]) -> bool:
        return (
            resolved.get("status") == "SOURCE_ADDRESSED_NOT_SEMANTICALLY_VERIFIED"
            and resolved.get("earth_anchor") == self.EARTH
            and resolved.get("earth_anchor_is_ontology_node") is False
            and resolved.get("source_edition") == "ariadne-reader/v0.7"
            and resolved.get("source_digest") == self.SOURCE_SHA256
            and isinstance(resolved.get("source_hsn"), str)
            and self.HSN.fullmatch(resolved["source_hsn"]) is not None
        )

    def escalate_to_human_root(self, reason: str, payload: Any) -> dict[str, Any]:
        return {"status": "PREPARED_NOT_SENT", "reason": reason, "payload": deepcopy(payload), "authority": "none"}

    def wrap_as_coordinate_packet(self, payload: Any, metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return {"kind": "CoordinatePacket", "grounding": self.EARTH, "payload": deepcopy(payload), "metadata": deepcopy(dict(metadata or {})), "authority": "none", "status": "CANDIDATE"}


class Sentinel:
    """Independent advisory reviewer. It cannot grant host permission or ratify."""

    def review_packet(self, packet: Any) -> dict[str, Any]:
        reasons: list[str] = []
        if not isinstance(packet, dict):
            reasons.append("packet_not_object")
        else:
            action = packet.get("requested_action", "PREPARE")
            if type(action) is not str or action not in SAFE_ACTIONS:
                reasons.append("noncandidate_or_consequential_action")
            if packet.get("canon") is not False or packet.get("deployment") is not False or packet.get("authority") != "none":
                reasons.append("candidate_boundary_violation")
            if packet.get("source_class") != "Work":
                reasons.append("work_source_classification_required")
            if packet.get("kind") == "IngestionPacket":
                ingestion = validate_ingestion(packet)
                if ingestion.state == "QUARANTINED":
                    reasons.append("ingestion_validation_failed")
            if packet.get("mutation") in ("DELETE", "OVERWRITE", "FORCE_MERGE", "REVOKE_GRANTS"):
                reasons.append("destructive_mutation_requires_human_review")
        return {
            "allowed": not reasons, "reason": "LOCAL_CANDIDATE_REVIEW_ONLY" if not reasons else "HOLD",
            "requires_human_root": bool(reasons), "findings": tuple(reasons), "authority": "none",
        }


class Orchestrator:
    def __init__(self, sentinel: Sentinel | None = None) -> None:
        self.sentinel = sentinel

    def route(self, packet: Mapping[str, Any]) -> dict[str, Any]:
        original = deepcopy(dict(packet))
        if self.sentinel is None:
            return {"status": "HOLD_NO_SENTINEL", "packet": original, "authority": "none"}
        review = self.sentinel.review_packet(original)
        return {"status": "PREPARED_NOT_EXECUTED" if review["allowed"] else "QUARANTINED_REVIEW_REQUIRED", "packet": original, "review": review, "authority": "none"}


class CandidateQueue:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def add(self, record: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(record, Mapping) or not isinstance(record.get("candidate_id"), str) or not record.get("candidate_id") or not record.get("source"):
            raise ValidationError("candidate_id_and_source_required")
        if any(x["candidate_id"] == record["candidate_id"] for x in self.records):
            raise ValidationError("candidate_id_collision_hold")
        entry = {
            "candidate_id": record["candidate_id"], "source": deepcopy(record["source"]),
            "why_useful": record.get("why_useful"), "evidence_receipts": deepcopy(record.get("evidence_receipts", [])),
            "risks": deepcopy(record.get("risks", [])), "contradictions": deepcopy(record.get("contradictions", [])),
            "review_required": True, "human_root_decision": "PENDING_EXTERNAL_PROOF",
            "status": "CANDIDATE", "canon": False, "deployment": False, "authority": "none",
        }
        self.records.append(deepcopy(entry))
        return deepcopy(entry)

    def request_promotion(self, candidate_id: str, to_state: str, **_untrusted_claims: Any) -> dict[str, Any]:
        if not any(x["candidate_id"] == candidate_id for x in self.records):
            return {"status": "HOLD_UNKNOWN_CANDIDATE", "authority": "none"}
        return {
            "status": "HELD_EXTERNAL_GOVERNANCE_OR_HOST_PROOF_REQUIRED",
            "requested_state": to_state, "current_state": "CANDIDATE", "authority": "none",
            "note": "Caller-supplied approvals cannot prove ratification or deployment",
        }


class EvidenceGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: dict[str, dict[str, Any]] = {}

    def add_node(self, node_id: str, node_type: str, *, source_ref: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if type(node_type) is not str or node_type not in GRAPH_NODES or not isinstance(source_ref, str) or not source_ref:
            raise ValidationError("node_type_or_source_invalid")
        if node_id in self.nodes:
            raise ValidationError("node_exists_preserve_original")
        n = {"id": node_id, "type": node_type, "source_ref": source_ref, "payload": deepcopy(dict(payload or {})), "authority": "none"}
        self.nodes[node_id] = deepcopy(n)
        return n

    def add_edge(self, edge_id: str, source: str, target: str, kind: str, *, source_ref: str) -> dict[str, Any]:
        if type(kind) is not str or kind not in GRAPH_EDGES or not isinstance(source, str) or not isinstance(target, str) or source not in self.nodes or target not in self.nodes or not source_ref:
            raise ValidationError("edge_invalid_or_missing_endpoint")
        if edge_id in self.edges:
            raise ValidationError("edge_exists_preserve_original")
        edge = {"id": edge_id, "source": source, "target": target, "kind": kind, "source_ref": source_ref, "authority": "none"}
        self.edges[edge_id] = deepcopy(edge)
        return edge


class AetherforgeCandidate:
    @staticmethod
    def metadata(source_ref: str, *, challenge: str) -> dict[str, Any]:
        if not source_ref or not challenge:
            raise ValidationError("source_and_challenge_required")
        return {
            "kind": "AetherforgeCandidate", "source_ref": source_ref, "challenge": challenge,
            "status": "CANDIDATE", "canon": False, "deployment": False, "authority": "none",
            "source_class": "SIMULATION_METADATA_ONLY", "original_leisure_bodies_imported": False,
            "promote": "EXTERNAL_HUMAN_AND_COMMUNITY_PROCESS_ONLY",
        }