"""Issue #7: immutable append-only local reference receipts; not a hosted transactional DB."""
from .types import digest, nonempty_string, snapshot

DESTRUCTIVE = {"delete", "erase", "overwrite", "truncate", "purge", "drop", "destroy"}


class PreservationLog:
    def __init__(self):
        self._snapshots = {}  # content-addressed; retained forever within this process
        self._events = []

    def capture(self, obj):
        image = snapshot(obj)
        key = digest(image)
        self._snapshots[key] = image
        return key

    def read_snapshot(self, key):
        if key not in self._snapshots:
            raise KeyError("snapshot_not_found")
        return snapshot(self._snapshots[key])

    def transition(self, before, after, action, source_ref):
        if not nonempty_string(source_ref):
            raise ValueError("source_ref_required")
        if not nonempty_string(action, 120):
            raise ValueError("action_required")
        b = self.capture(before)
        if action.lower() in DESTRUCTIVE:
            a = b
            effective = "QUARANTINE_INTENT_NO_DESTRUCTIVE_WRITE"
            status = "HELD_FOR_HUMAN_REVIEW"
        else:
            a = self.capture(after)
            effective = action.upper()
            status = "PRESERVED_UNREVIEWED"
        event = {"seq": len(self._events) + 1, "beforeDigest": b, "afterDigest": a,
                 "requestedAction": action, "effectiveAction": effective, "status": status,
                 "sourceRef": source_ref, "authority": "NONE"}
        self._events.append(snapshot(event))
        return snapshot(event)

    def events(self):
        return snapshot(self._events)

    def supersede(self, old, revised, source_ref):
        return self.transition(old, revised, "supersede", source_ref)

    def quarantine(self, obj, reason, source_ref):
        return self.transition(obj, {"quarantined": snapshot(obj), "reason": reason}, "quarantine", source_ref)
