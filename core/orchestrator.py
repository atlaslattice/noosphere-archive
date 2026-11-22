"""Issue #6: routing separated from review, no action dispatch or private data import."""
from .types import digest, snapshot


class Orchestrator:
    def __init__(self, sentinel=None):
        self.sentinel = sentinel

    def route(self, packet):
        data = snapshot(packet)
        if self.sentinel is None:
            return {"status": "HOLD_UNREVIEWED_NO_SENTINEL", "packetDigest": digest(data),
                    "authority": "NONE", "original": data}
        reviewed = self.sentinel(data)
        if not isinstance(reviewed, dict) or reviewed.get("authority") != "NONE":
            return {"status": "HOLD_INVALID_REVIEW", "packetDigest": digest(data), "original": data, "authority": "NONE"}
        if reviewed.get("allowed") is not True:
            return {"status": "QUARANTINED_PENDING_REVIEW", "packetDigest": digest(data),
                    "findings": snapshot(reviewed.get("findings", [])), "original": data, "authority": "NONE"}
        return {"status": "SOURCE_ONLY_REVIEW_QUEUE", "packetDigest": digest(data),
                "original": data, "authority": "NONE", "actualExecution": False}
