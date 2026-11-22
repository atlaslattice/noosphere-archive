"""Local synthetic demonstration; all outputs are source-only, non-authoritative."""
import json
from .coordinate_resolver import CoordinateResolver
from .sentinel import review_packet
from .orchestrator import Orchestrator
from .preservation import PreservationLog
from .ingestion import validate_ingestion
from .rhythm import proposed_macrocycle


def main():
    resolver = CoordinateResolver("Ariadne-v0.7-illustrative-source-ref", "digest-unverified-demo")
    packet = resolver.wrap_as_coordinate_packet({"claim": "synthetic water service"},{"hsn": "H02.S05.N02"})
    outcome = Orchestrator(sentinel=review_packet).route(packet)
    log = PreservationLog()
    before = {"old": "original retained"}
    record = log.transition(before, {"deleted": True}, "delete", "synthetic-source")
    raw = validate_ingestion({"source_ref": "synthetic-source", "raw_export_status": "raw_partial", "claim_complete": True})
    print(json.dumps({"coordinate": packet["hsn"], "routing": outcome["status"],
                      "destruction": record["status"], "originalStillReachable": log.read_snapshot(record["beforeDigest"]) == before,
                      "incompleteIngestion": raw["status"],
                      "threeSlotRhythm": [proposed_macrocycle(i)["slot"] for i in range(3)]}, indent=2))

if __name__ == "__main__": main()
