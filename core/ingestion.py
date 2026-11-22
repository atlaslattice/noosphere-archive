"""Issue #8: explicit raw export status; quarantine rather than erase."""
from .types import nonempty_string, valid_sha, digest, snapshot

STATES = {"raw_missing", "raw_partial", "raw_complete_unhashed", "raw_complete_hashed", "raw_source_unavailable"}


def validate_ingestion(packet):
    if not isinstance(packet, dict):
        return {"accepted": False, "reason": "packet_not_object", "status": "QUARANTINED_INCOMPLETE", "original": snapshot(packet)}
    errors = []
    status = packet.get("raw_export_status")
    if status not in STATES: errors.append("invalid_or_missing_raw_export_status")
    if not nonempty_string(packet.get("source_ref")): errors.append("source_ref_missing")
    if status == "raw_complete_hashed":
        if not valid_sha(packet.get("raw_sha256")): errors.append("raw_sha256_required")
        if not isinstance(packet.get("source_manifest"), list) or not packet["source_manifest"]: errors.append("source_manifest_required")
    else:
        if packet.get("claim_complete") is True: errors.append("completion_claim_without_hashed_export")
    if packet.get("canon") is True or packet.get("deployment") is True: errors.append("untrusted_authority_claim")
    accepted = not errors
    return {"accepted": accepted, "reason": "SOURCE_RECEIVED_UNREVIEWED" if accepted else "INCOMPLETE_SOURCE_HELD",
            "status": "CANDIDATE_UNREVIEWED" if accepted else "QUARANTINED_INCOMPLETE",
            "issues": errors, "original": snapshot(packet), "originalDigest": digest(packet),
            "authority": "NONE", "completenessEvidence": "SOURCE_HASH_PRESENT_NOT_EXTERNALLY_VERIFIED" if status == "raw_complete_hashed" and accepted else "NOT_VERIFIED"}
