#!/usr/bin/env python3
"""Execute 20 bounded local review-artifact orders linked to observed Work rows.

This is an integration harness, not an agent simulator or source patch generator.
The optional twentieth, deferred claim is held without dispatch. Each other
order runs one declared falsifier through the real coordinator and executor.
Raw Work observations are private inputs and are never included in exports.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks"))

SCHEMA = "atlas.beast20.synthesis-campaign-execution/v1"
RUNNER = Path(__file__).resolve()
SOURCE_PATHS = {
    "coordinator": ROOT / "src/beast20/synthesis.py",
    "provenance": ROOT / "src/beast20/synthesis_provenance.py",
    "falsifier": ROOT / "benchmarks/bench_synthesis20_falsifiers.py",
    "runner": RUNNER,
    "executor": ROOT / "src/beast20/execution.py",
    "storage": ROOT / "src/beast20/storage.py",
    "falsifier-receipt": ROOT / "benchmarks/synthesis20/PROVENANCE_FALSIFIER_RESULTS.json",
}
IMPORT_SOURCE_SHA256 = {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in SOURCE_PATHS.items()}

from src.beast20.storage import Scope
from src.beast20.synthesis import (
    ArtifactResult, BuildOrder, ChallengeDisposition, LocalCheck, LocalHandler,
    REGISTRY_SHA256, SynthesisCoordinator, compact_summary, evidence_sha256,
    make_order_provenance, make_peer_observation, report_bundle, validate_report,
)
from bench_synthesis20_falsifiers import make_cases, run_case

if IMPORT_SOURCE_SHA256 != {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in SOURCE_PATHS.items()}:
    raise RuntimeError("CAMPAIGN_SOURCE_CHANGED_DURING_IMPORT")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def sha(value):
    return hashlib.sha256(value).hexdigest()


def require(ok, code):
    if not ok:
        raise ValueError(code)


def source_hashes():
    return {key: sha(path.read_bytes()) for key, path in SOURCE_PATHS.items()}


def read_observations(path, *, allow_partial=False):
    """Shape-check detached caller observations; this does not attest the server."""
    raw = path.read_bytes()
    require(len(raw) <= 1024 * 1024, "PRIVATE_INPUT_TOO_LARGE")
    data = json.loads(raw)
    require(type(data) is dict and set(data) == {"schema", "rounds", "deferredClaim"}
            and data["schema"] == "atlas.beast20.observed-work-input/v1", "OBSERVED_INPUT_SCHEMA")
    rows = data["rounds"]
    require(type(rows) is list and 1 <= len(rows) <= 20, "OBSERVED_ROUND_BOUND")
    found, messages = {}, set()
    for row in rows:
        require(type(row) is dict and set(row) == {"round", "record"}, "OBSERVED_ROUND_FIELDS")
        number = row["round"]
        require(type(number) is int and 1 <= number <= 20 and number not in found,
                "OBSERVED_ROUND_DUPLICATE_OR_INVALID")
        observed = make_peer_observation(row["record"])
        require(observed["sha256"] not in messages, "OBSERVED_MESSAGE_REUSED")
        messages.add(observed["sha256"])
        found[number] = observed
    if not allow_partial:
        require(set(found) == set(range(1, 21)), "TWENTY_DISTINCT_OBSERVED_ROUNDS_REQUIRED")
    deferred = data["deferredClaim"]
    if deferred is not None:
        require(type(deferred) is dict and set(deferred) == {"challengeRound", "responseRound"},
                "DEFERRED_CLAIM_FIELDS")
        require(all(type(deferred[k]) is int and deferred[k] in found for k in deferred),
                "DEFERRED_CLAIM_OBSERVATION_REQUIRED")
        require(found[deferred["challengeRound"]]["record"]["kind"] == "objection",
                "ACTUAL_OBJECTION_OBSERVATION_REQUIRED")
    return found, deferred, sha(raw)


def retained_case_result(case):
    """Use an earlier actual run as the complete parity witness, without re-running it."""
    raw = SOURCE_PATHS["falsifier-receipt"].read_bytes()
    require(sha(raw) == IMPORT_SOURCE_SHA256["falsifier-receipt"], "RETAINED_FALSIFIER_CHANGED")
    reference = json.loads(raw)
    require(reference["schema"] == "atlas.beast20.provenance-falsifiers/v1" and reference["status"] == "COMPLETED"
            and reference["reportSha256"] == evidence_sha256({k: v for k, v in reference.items() if k != "reportSha256"}),
            "RETAINED_FALSIFIER_INVALID")
    implementation = {"runner": IMPORT_SOURCE_SHA256["falsifier"], "provenanceModule": IMPORT_SOURCE_SHA256["provenance"]}
    require(reference["implementation"]["beforeSha256"] == reference["implementation"]["afterSha256"] == implementation,
            "RETAINED_FALSIFIER_SOURCE_MISMATCH")
    require(next(row for row in reference["workload"] if row["id"] == case["id"]) == case,
            "RETAINED_FALSIFIER_CASE_MISMATCH")
    row = next(row for row in reference["results"] if row["caseId"] == case["id"])
    lanes = [{k: v for k, v in lane.items() if k != "elapsedNs"} for lane in row["results"]]
    calls = [call for call in reference["execution"]["registeredModuleInvocations"] if call["caseId"] == case["id"]]
    require(len(calls) == 5 and all(call["status"] == "RETURNED" for call in calls), "RETAINED_FALSIFIER_CALLS_INVALID")
    result = {"schema": "atlas.beast20.provenance-falsifier-case/v1", "evidenceKind": "SYNTHETIC_CONTRACT_EXPERIMENT",
        "caseId": case["id"], "caseSha256": evidence_sha256(case), "policySha256": reference["policySha256"],
        "expected": case["expected"], "outputEqual": row["outputEqual"], "results": lanes,
        "counts": {"caseComparisons": len(lanes), "encodingCalls": 2 * len(lanes), "registeredModuleCalls": len(calls),
                   "registeredModuleCallCounts": {name: sum(call["operation"] == name for call in calls)
                       for name in reference["execution"]["registeredModuleCallCounts"]}},
        "fullContractMatches": next(lane["matchesBoth"] for lane in lanes if lane["method"] == "FULL_KEYED_PROVENANCE"),
        "implementationSha256": implementation,
        "scope": "One local synthetic review-result artifact, not a source patch, peer turn, acceptance or hosted result."}
    return {**result, "sha256": evidence_sha256(result)}


def validate_review_artifact(artifact, output, payload, expected_parent_digests):
    """Require the declared case/oracle and every comparison, including losses."""
    if type(artifact) is not bytes or type(output) is not dict or artifact != canonical(output):
        return False
    if set(output) != {"schema", "evidenceKind", "case", "result", "parentArtifactSha256"}:
        return False
    if output["schema"] != "atlas.beast20.local-review-artifact/v1" or output["evidenceKind"] != "CONTROLLED_PROVENANCE_CONTRACT":
        return False
    cases = {case["id"]: case for case in make_cases()}
    case = cases.get(payload["caseId"])
    if case is None or output["case"] != case:
        return False
    result = output["result"]
    if result != retained_case_result(case):
        return False
    if type(result) is not dict or result.get("caseId") != case["id"]:
        return False
    rows = result.get("results")
    if type(rows) is not list or {row.get("method") for row in rows} != {
        "VALUES_ONLY_ALL_DOMAINS", "WHOLE_PACKET", "FULL_KEYED_PROVENANCE"
    }:
        return False
    if len(rows) != 3:
        return False
    if (result.get("expected") != case["expected"] or result.get("caseSha256") != evidence_sha256(case)
            or result.get("sha256") != evidence_sha256({key: value for key, value in result.items() if key != "sha256"})
            or result.get("fullContractMatches") is not True):
        return False
    current = next(row for row in rows if row["method"] == "FULL_KEYED_PROVENANCE")
    if (current.get("error") is not None or current.get("identityRelation") != case["expected"]["identityRelation"]
            or current.get("reviewDecision") != case["expected"]["reviewDecision"]
            or current.get("matchesBoth") is not True):
        return False
    for row in rows:
        if row.get("identityMatches") != (row.get("identityRelation") == case["expected"]["identityRelation"]):
            return False
        if row.get("decisionMatches") != (row.get("reviewDecision") == case["expected"]["reviewDecision"]):
            return False
    return (type(output["parentArtifactSha256"]) is list
            and output["parentArtifactSha256"] == list(expected_parent_digests)
            and all(type(x) is str and re.fullmatch(r"[a-f0-9]{64}", x)
                    for x in output["parentArtifactSha256"]))


def build_review(payload, parents):
    case = next(case for case in make_cases() if case["id"] == payload["caseId"])
    parent_digests = sorted(parent["artifactSha256"] for parent in parents.values())
    output = {"schema": "atlas.beast20.local-review-artifact/v1",
              "evidenceKind": "CONTROLLED_PROVENANCE_CONTRACT", "case": case,
              "result": run_case(case), "parentArtifactSha256": parent_digests}
    return ArtifactResult(canonical(output), output)


def check_positive(artifact, output, payload, expected_parent_digests):
    return validate_review_artifact(artifact, output, payload, expected_parent_digests)


def check_negative(artifact, output, payload, expected_parent_digests):
    # A re-encoded/re-hashed wrong outcome must fail semantically. This is not
    # merely a test that changing bytes changes their digest.
    altered = json.loads(canonical(output))
    current = next(row for row in altered["result"]["results"] if row["method"] == "FULL_KEYED_PROVENANCE")
    current["reviewDecision"] = "FAIL" if current["reviewDecision"] != "FAIL" else "PASS"
    current["decisionMatches"] = True
    current["matchesBoth"] = True
    altered["result"]["sha256"] = evidence_sha256({key: value for key, value in altered["result"].items() if key != "sha256"})
    return validate_review_artifact(canonical(altered), altered, payload, expected_parent_digests) is False


async def execute(args):
    peers, deferred, private_sha = read_observations(args.peer_observations, allow_partial=args.allow_partial)
    pins = source_hashes()
    require(pins == IMPORT_SOURCE_SHA256, "CAMPAIGN_SOURCE_CHANGED_AFTER_IMPORT")
    handler_sha = pins["runner"]
    check_codes = {"review-positive": handler_sha, "review-negative": handler_sha}
    orders, planned = [], {}
    by_number = {number: row["sha256"] for number, row in peers.items()}
    dispositions = []
    artifacts = {}
    parent_witnesses = {}

    def record_review(payload, parents):
        parent_witnesses[payload["caseId"]] = tuple(sorted(parent["artifactSha256"] for parent in parents.values()))
        result = build_review(payload, parents)
        artifacts[payload["caseId"]] = {"artifactSha256": sha(result.artifact),
                                       "outputSha256": evidence_sha256(result.output), "output": result.output}
        return result
    for number in sorted(peers):
        order_id = f"REVIEW-{number:02d}"
        payload = {"caseId": f"F{number:02d}", "artifactKind": "LOCAL_REVIEW_RESULT"}
        subject = {"artifactId": f"review-result-{number:02d}", "baselineSha256": sha(b"")}
        # Five waves of four independent orders demonstrate bounded dependency
        # propagation without claiming a performance gain for this graph.
        dependencies = (f"REVIEW-{number-4:02d}",) if (number > 4 and number-4 in peers
            and (deferred is None or number-4 != deferred["challengeRound"])) else ()
        refs, challenges = {by_number[number]}, ()
        if deferred is not None and number in {20, deferred["challengeRound"]}:
            challenge = by_number[deferred["challengeRound"]]
            response = by_number[deferred["responseRound"]]
            refs.update((challenge, response))
            challenges = (challenge,)
            if not dispositions:
                dispositions.append(ChallengeDisposition(challenge, "DEFERRED", response_ref=response))
            payload["claim"] = "GENERAL_COLLABORATIVE_ANSWER_QUALITY_GAIN"
        extra = {**{f"source:{key}": value for key, value in pins.items()}, "private-observation-file": private_sha}
        provenance = make_order_provenance(handler_code_sha256=handler_sha, payload=payload, subject=subject,
            dependencies={dep: planned[dep]["sha256"] for dep in dependencies}, peer_refs=sorted(refs),
            check_codes=check_codes, inputs=extra)
        planned[order_id] = provenance
        orders.append(BuildOrder(order_id, number, "review", payload, subject, provenance,
            dependencies=dependencies, check_ids=tuple(check_codes), peer_refs=tuple(sorted(refs)), challenge_refs=challenges))

    def current(order):
        now_peers, now_deferred, now_private_sha = read_observations(args.peer_observations, allow_partial=args.allow_partial)
        now_hashes = source_hashes()
        # Reload and hash the observed records on every check. The host does not
        # pretend this local read reauthenticates their original live author.
        available = {row["sha256"] for row in now_peers.values()}
        current_refs = [ref for ref in order["peerRefs"] if ref in available]
        return make_order_provenance(handler_code_sha256=now_hashes["runner"], payload=order["payload"],
            subject=order["subject"], dependencies={dep: planned[dep]["sha256"] for dep in order["dependencies"]},
            peer_refs=current_refs, check_codes={key: now_hashes["runner"] for key in order["checkIds"]},
            inputs={**{f"source:{key}": value for key, value in now_hashes.items()},
                    "private-observation-file": now_private_sha})

    scope = Scope(REGISTRY_SHA256, "synthesis20-v1", "authorized-local-campaign", "observed-work-v1")
    def authorize(observed_scope, phase):
        return observed_scope == scope and phase in {"READ", "DISPATCH", "RETURN"}

    args.output_dir.mkdir(parents=True, exist_ok=True)
    require(not (args.output_dir / "CAMPAIGN_REPORT.json").exists() or args.replace, "OUTPUT_EXISTS_USE_EXPLICIT_REPLACE")
    with tempfile.TemporaryDirectory(prefix="native1728-synthesis20-") as temporary:
        coordinator = SynthesisCoordinator(Path(temporary) / "campaign.sqlite", scope=scope,
            campaign_id="native1728-reviewed-campaign-v1", handlers={"review": LocalHandler(record_review, handler_sha)},
            checks={"review-positive": LocalCheck(lambda a, o, p: check_positive(a, o, p, parent_witnesses[p["caseId"]]), "POSITIVE", handler_sha),
                    "review-negative": LocalCheck(lambda a, o, p: check_negative(a, o, p, parent_witnesses[p["caseId"]]), "NEGATIVE", handler_sha)},
            observe_provenance=current, authorize=authorize)
        try:
            report = await coordinator.run(orders, peer_observations=list(peers.values()), dispositions=dispositions)
            replay = await coordinator.run(orders, peer_observations=list(peers.values()), dispositions=dispositions)
        finally:
            coordinator.close()
    require(source_hashes() == pins, "CAMPAIGN_SOURCE_CHANGED")
    require(sha(args.peer_observations.read_bytes()) == private_sha, "OBSERVED_INPUT_CHANGED")
    require(replay["counts"]["implementedOrders"] == 0 and replay["counts"]["ordersComputed"] == 0,
            "REPLAY_EARNED_FRESH_IMPLEMENTATION")
    require(all(row["status"] != "FAIL" for row in report["orders"]), "CAMPAIGN_CHECK_FAILED")
    for row in report["orders"]:
        if row["artifactSha256"] is not None:
            artifact = artifacts[f'F{row["round"]:02d}']
            require((artifact["artifactSha256"], artifact["outputSha256"]) ==
                    (row["artifactSha256"], row["outputSha256"]), "CAMPAIGN_ARTIFACT_BINDING_MISMATCH")
    bundle = report_bundle(report)
    proof = {
        "schema": SCHEMA, "status": "COMPLETED_LOCAL_CAMPAIGN", "campaignStatus": report["status"],
        "evidenceKind": "LOCAL_REVIEW_ARTIFACTS_AND_EXECUTOR_REPLAY",
        "reportSha256": bundle["reportSha256"], "replayReportSha256": report_bundle(replay)["reportSha256"],
        "sourceSha256": pins, "privateObservationFileSha256": private_sha,
        "actualObservedRoundMessages": len(peers), "counts": report["counts"], "replayCounts": replay["counts"],
        "reservedNonWorkSlotsPerformed": 0, "modelCalls": 0, "externalEffects": 0,
        "buildArtifactMeaning": "One changed local review-result JSON per executed case; these are not source patches or independent features.",
        "scope": "The standalone falsifier experiment and this integration run are separate executions; their counts are not added to claim additional independent cases.",
        "authority": "Actual collaborator messages were read through an authorized Work room. This input file is a client observation, not server-signed authorship or independent resident verification.",
        "freshness": "Local input/source bytes are re-read around dispatch and return, including cached replay; external live state is not continuously monitored.",
        "completion": "The coordinator creates no canonical task transitions. Source publication and host deployment are separately recorded release actions.",
    }
    outputs = {"CAMPAIGN_REPORT.json": validate_report(report), "CAMPAIGN_BUNDLE.json": bundle,
               "CAMPAIGN_REPLAY.json": validate_report(replay), "CAMPAIGN_EXECUTION.json": proof,
               "CAMPAIGN_ARTIFACTS.json": {"schema": "atlas.beast20.local-review-artifacts/v1", "artifacts": artifacts}}
    for name, value in outputs.items():
        (args.output_dir / name).write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="ascii")
    print(json.dumps({key: proof[key] for key in ("status", "campaignStatus", "reportSha256", "counts", "replayCounts")}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--peer-observations", type=Path, required=True,
                        help="Private detached records read from the authorized Work campaign")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "benchmarks/synthesis20/campaign")
    parser.add_argument("--allow-partial", action="store_true", help="Keep a visibly partial HOLD report during integration")
    parser.add_argument("--replace", action="store_true")
    asyncio.run(execute(parser.parse_args()))


if __name__ == "__main__":
    main()
