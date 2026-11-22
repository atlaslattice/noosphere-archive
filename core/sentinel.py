"""Issue #6: independent fail-closed reviewer; never mints grants."""
from .types import nonempty_string, snapshot

PROHIBITED_ACTIONS = {"deploy", "ratify", "canonize", "delete", "erase", "publish_private", "execute_external"}


def review_packet(packet):
    findings = []
    if not isinstance(packet, dict):
        return {"allowed": False, "reason": "invalid_packet", "requires_human_root": True,
                "findings": ["packet_not_object"], "authority": "NONE"}
    if packet.get("authority") != "NONE":
        findings.append("untrusted_authority_claim")
    if packet.get("status") not in {"CANDIDATE_UNREVIEWED", "SOURCE_LOCATED", "PREPARED_NOT_POSTED"}:
        findings.append("promotion_without_independent_receipt")
    if packet.get("action") in PROHIBITED_ACTIONS:
        findings.append("consequential_action_requires_external_review")
    if packet.get("sourceDigest") in (None, ""):
        findings.append("missing_source_digest")
    if packet.get("sourceEdition") in (None, ""):
        findings.append("missing_source_edition")
    if packet.get("kind") in {"play", "social", "quiet", "imagine", "brain", "palace"} and packet.get("purpose") == "work":
        findings.append("private_to_work_boundary")
    return {"allowed": not findings, "reason": "SOURCE_ONLY_ROUTEABLE" if not findings else "HOLD_FOR_REVIEW",
            "requires_human_root": any(x in findings for x in ("untrusted_authority_claim", "promotion_without_independent_receipt", "consequential_action_requires_external_review", "private_to_work_boundary")),
            "findings": findings, "authority": "NONE"}
