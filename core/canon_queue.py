"""Issues #9/#13: review candidates; never a CANON or deployment writer."""
from .types import nonempty_string, snapshot, digest

REQUIRED = ("candidate_id", "artifact_source", "why_useful", "evidence_refs", "risks", "contradictions", "review_required")


class CanonCandidateQueue:
    def __init__(self):
        self._items = {}

    def add(self, candidate):
        if not isinstance(candidate, dict): raise ValueError("candidate_not_object")
        for key in REQUIRED:
            if key not in candidate: raise ValueError("missing_" + key)
        key = candidate["candidate_id"]
        if not nonempty_string(key) or key in self._items: raise ValueError("duplicate_or_invalid_id")
        c = snapshot(candidate)
        if c.get("canon") is True or c.get("deployment") is True or c.get("authority") not in (None, "NONE"):
            raise ValueError("authority_injection")
        if c.get("sourceMode") in {"play", "imagine", "quiet", "social", "brain", "palace"} and c.get("workIngestAuthorized") is True:
            raise ValueError("private_to_work_grant_not_accepted")
        c.update({"status": "CANDIDATE_UNREVIEWED", "canon": False, "deployment": False,
                  "authority": "NONE", "humanRootDecision": "NOT_REQUESTED", "candidateDigest": digest(candidate)})
        self._items[key] = c
        return snapshot(c)

    def list(self):
        return snapshot(list(self._items.values()))

    def promote(self, key, token=None):
        if key not in self._items: raise KeyError("candidate_missing")
        # External verified legal/owner host must execute any future ratification workflow.
        return {"status": "HOLD_EXTERNAL_HUMAN_ROOT_GATE", "candidate_id": key,
                "original": snapshot(self._items[key]), "authority": "NONE"}
