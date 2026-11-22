"""Issue #5: HSN grounding, no implied authority or 1728 namespace equivalence."""
import re
from .types import digest, nonempty_string, snapshot

HSN = re.compile(r"^H(0[1-9]|1[0-2])\.S(0[1-9]|1[0-2])\.N(0[1-9]|1[0-2])$")
EARTH = "H00.S00.N00"  # routing marker, explicitly NOT one of Ariadne's 1728 nodes


class CoordinateResolver:
    def __init__(self, source_edition: str, source_digest: str):
        if not nonempty_string(source_edition) or not nonempty_string(source_digest):
            raise ValueError("pinned source edition and digest required")
        self.source_edition = source_edition
        self.source_digest = source_digest

    def wrap_as_coordinate_packet(self, payload, metadata=None):
        if not isinstance(payload, dict):
            raise ValueError("payload must be object")
        metadata = metadata or {}
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be object")
        data = snapshot(payload)
        if any(x in data for x in ("authorized", "canon", "deployed")):
            # inherited authority claims may be data in an archive but cannot become packet fields
            return self.escalate_to_human_root("untrusted_authority_fields", data)
        target = metadata.get("hsn") or data.get("hsn") or EARTH
        if target != EARTH and not HSN.fullmatch(str(target)):
            return self.escalate_to_human_root("invalid_hsn", data)
        return {"schema": "atlas.swarmhub.coordinate.v0.1", "hsn": target,
                "sourceEdition": self.source_edition, "sourceDigest": self.source_digest,
                "grounding": "EARTH_ROUTING_ONLY" if target == EARTH else "HISTORICAL_HSN_ADDRESS_ONLY",
                "dAffinity": snapshot(metadata.get("dAffinity", [])),
                "payload": data, "payloadDigest": digest(data),
                "status": "CANDIDATE_UNREVIEWED", "authority": "NONE"}

    def validate_grounding(self, packet):
        if not isinstance(packet, dict) or packet.get("schema") != "atlas.swarmhub.coordinate.v0.1":
            return {"valid": False, "reason": "schema_missing", "authority": "NONE"}
        if packet.get("sourceEdition") != self.source_edition or packet.get("sourceDigest") != self.source_digest:
            return {"valid": False, "reason": "source_edition_mismatch", "authority": "NONE"}
        hsn = packet.get("hsn")
        if hsn != EARTH and (not isinstance(hsn, str) or not HSN.fullmatch(hsn)):
            return {"valid": False, "reason": "invalid_hsn", "authority": "NONE"}
        if packet.get("payloadDigest") != digest(packet.get("payload")):
            return {"valid": False, "reason": "payload_integrity_failure", "authority": "NONE"}
        if packet.get("authority") != "NONE" or packet.get("status") != "CANDIDATE_UNREVIEWED":
            return {"valid": False, "reason": "authority_injection", "authority": "NONE"}
        return {"valid": True, "reason": "source_addressed_only", "authority": "NONE"}

    def resolve_to_earth(self, claim):
        packet = self.wrap_as_coordinate_packet(claim, {"hsn": EARTH, "dAffinity": claim.get("dAffinity", []) if isinstance(claim, dict) else []})
        packet["routingOnly"] = True
        return packet

    def escalate_to_human_root(self, reason, payload):
        return {"schema": "atlas.swarmhub.escalation.v0.1", "status": "QUARANTINED_PENDING_REVIEW",
                "reason": reason, "original": snapshot(payload), "originalDigest": digest(payload),
                "humanRoot": "REQUIRED_BUT_NOT_CONTACTED", "authority": "NONE"}
