#!/usr/bin/env python3
"""Bind completed campaign/source/replication bytes into the two native hosts.

This prepares reversible source changes only. It does not publish, change host
access, invoke models, post Work messages, or create another queue.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.beast20.synthesis import compact_summary, report_bundle, validate_report
from src.beast20.long_horizon import validate_report as validate_simulation


# This receipt is the actual, retained R07 experiment, not a caller-selected
# "best" result. A replacement experiment needs an explicit reviewed new pin.
FALSIFIER_RECEIPT_SHA256 = "fb1c67732cb6e117a359a787c5a31b2c267568e055b950c7a271b0ef79f0c14d"
FALSIFIER_REPORT_SHA256 = "20672b85350eeeaed3c24873323fd71aff810993178305eea892befbe240b7b5"
FALSIFIER_WORKLOAD_SHA256 = "2d02a2d137205ebeb2157164068af6ab22fd1420b8438e17bf3c5e8bafcf9fc1"
FALSIFIER_SEMANTIC_SHA256 = "aac87a7a2c602b65b16bd5db6c35cd71982b3449f7b75f57f3120ba94ab07793"
FALSIFIER_SOURCE_PATHS = {
    "runner": "benchmarks/bench_synthesis20_falsifiers.py",
    "provenanceModule": "src/beast20/synthesis_provenance.py",
}
CAMPAIGN_SOURCE_PATHS = {
    "coordinator": "src/beast20/synthesis.py", "provenance": "src/beast20/synthesis_provenance.py",
    "falsifier": "benchmarks/bench_synthesis20_falsifiers.py", "runner": "benchmarks/run_synthesis20_campaign.py",
    "executor": "src/beast20/execution.py", "storage": "src/beast20/storage.py",
    "falsifier-receipt": "benchmarks/synthesis20/PROVENANCE_FALSIFIER_RESULTS.json",
}
_MAX_SAFE_INTEGER = 9007199254740991


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, code):
    if not ok:
        raise ValueError(code)


def read(path):
    return json.loads(path.read_bytes())


def _fields(value, fields, code):
    require(type(value) is dict and all(type(key) is str for key in value)
            and set(value) == set(fields), code)


def _digest(value, code):
    require(type(value) is str and len(value) == 64
            and all(character in "0123456789abcdef" for character in value), code)


def _integer(value, minimum=0, maximum=_MAX_SAFE_INTEGER, code="EXPORT_INTEGER_INVALID"):
    require(type(value) is int and minimum <= value <= maximum, code)


def campaign_projection(proof, report, replay, *, allow_partial=False, source_root=ROOT):
    """Return an exact public projection of an inspected local campaign.

    Private-input digests and caller narrative strings are not forwarded. This
    validates recorded counts and local source identities; it does not attest
    message authors, continuously refresh Work, or resolve deferred dissent.
    """
    narrative_fields = {"buildArtifactMeaning", "scope", "authority", "freshness", "completion"}
    fields = {"schema", "status", "campaignStatus", "evidenceKind", "reportSha256", "replayReportSha256",
              "sourceSha256", "privateObservationFileSha256", "actualObservedRoundMessages", "counts",
              "replayCounts", "reservedNonWorkSlotsPerformed", "modelCalls", "externalEffects"} | narrative_fields
    _fields(proof, fields, "CAMPAIGN_EXECUTION_FIELDS_INVALID")
    require(type(allow_partial) is bool, "CAMPAIGN_PARTIAL_FLAG_INVALID")
    for key, expected in (("schema", "atlas.beast20.synthesis-campaign-execution/v1"),
                          ("status", "COMPLETED_LOCAL_CAMPAIGN"),
                          ("evidenceKind", "LOCAL_REVIEW_ARTIFACTS_AND_EXECUTOR_REPLAY")):
        require(type(proof[key]) is str and proof[key] == expected, "CAMPAIGN_EXECUTION_SCHEMA_INVALID")
    require(type(proof["campaignStatus"]) is str and proof["campaignStatus"] in {"PASS", "HOLD", "FAIL"},
            "CAMPAIGN_EXECUTION_STATUS_INVALID")
    for key in narrative_fields:
        require(type(proof[key]) is str and 0 < len(proof[key]) <= 2048, "CAMPAIGN_NARRATIVE_BOUND")
    for key in ("reportSha256", "replayReportSha256", "privateObservationFileSha256"):
        _digest(proof[key], "CAMPAIGN_EXECUTION_DIGEST_INVALID")
    _fields(proof["sourceSha256"], CAMPAIGN_SOURCE_PATHS, "CAMPAIGN_SOURCE_SET_CHANGED")
    for value in proof["sourceSha256"].values():
        _digest(value, "CAMPAIGN_SOURCE_DIGEST_INVALID")
    report, replay = validate_report(report), validate_report(replay)
    for key, expected in (("counts", report["counts"]), ("replayCounts", replay["counts"])):
        _fields(proof[key], expected, "CAMPAIGN_COUNTER_FIELDS_INVALID")
        for value in proof[key].values():
            _integer(value, code="CAMPAIGN_COUNTER_INVALID")
        require(proof[key] == expected, "CAMPAIGN_RECEIPT_MISMATCH")
    _integer(proof["actualObservedRoundMessages"], 1, 20, "CAMPAIGN_OBSERVED_ROUND_BOUND")
    for key in ("reservedNonWorkSlotsPerformed", "modelCalls", "externalEffects"):
        _integer(proof[key], 0, 0, "CAMPAIGN_UNPERFORMED_EFFECTS_REQUIRED")
    require(proof["reportSha256"] == report_bundle(report)["reportSha256"]
            and proof["replayReportSha256"] == report_bundle(replay)["reportSha256"]
            and proof["campaignStatus"] == report["status"], "CAMPAIGN_RECEIPT_MISMATCH")
    require(report["campaignId"] == replay["campaignId"] and report["source"] == replay["source"],
            "CAMPAIGN_REPLAY_IDENTITY_MISMATCH")
    observed = proof["actualObservedRoundMessages"]
    require(all(report["counts"][key] == replay["counts"][key] == observed
                for key in ("observedReviewRounds", "ordersSubmitted", "peerObservations")),
            "CAMPAIGN_OBSERVATION_COUNTS_MISMATCH")
    require(replay["counts"]["implementedOrders"] == 0 and replay["counts"]["ordersComputed"] == 0,
            "CAMPAIGN_FRESH_REPLAY_CREDIT")
    if not allow_partial:
        require(observed == 20, "TWENTY_OBSERVED_ROUNDS_REQUIRED")
    try:
        source_hashes = {name: sha((source_root / path).read_bytes())
                         for name, path in CAMPAIGN_SOURCE_PATHS.items()}
    except OSError:
        raise ValueError("CAMPAIGN_SOURCE_UNAVAILABLE") from None
    require(source_hashes == proof["sourceSha256"], "CAMPAIGN_SOURCE_CHANGED")
    require(report["source"]["coordinatorCodeSha256"] == source_hashes["coordinator"]
            and report["source"]["provenanceCodeSha256"] == source_hashes["provenance"],
            "CAMPAIGN_LOADED_SOURCE_MISMATCH")
    public_fields = fields - narrative_fields - {"schema", "privateObservationFileSha256"}
    public = {"schema": "atlas.native1728.synthesis-execution-projection/v1",
              "sourceSchema": proof["schema"], **{key: proof[key] for key in sorted(public_fields)}}
    return json.loads(json.dumps(public, ensure_ascii=True, separators=(",", ":"), allow_nan=False))


def replication_projection(first, second, *, engine_sha256):
    """Conserve the claims made about two validated full-run projections.

    Callers obtain each input through simulation(), which verifies its report
    and retained files. This compact check does not execute another simulation.
    """
    _digest(engine_sha256, "SIMULATION_ENGINE_DIGEST_INVALID")
    run_fields = {"reportSha256", "seed", "counts", "auditReplayUpdates", "elapsedNs",
                  "selectedCandidateId", "baselineCandidateId", "engineSourceSha256"}
    count_fields = {"acceptedCandidateChanges", "epochs", "evaluatedTimelineYearUpdates", "holdoutEpochs",
                    "houses", "nodes", "representedTimelineYears", "spheres", "timelines", "trainEpochs",
                    "yearsPerTimeline"}
    for run in (first, second):
        _fields(run, run_fields, "SIMULATION_PROJECTION_FIELDS_INVALID")
        for key in ("reportSha256", "engineSourceSha256"):
            _digest(run[key], "SIMULATION_DIGEST_INVALID")
        for key in ("seed", "auditReplayUpdates", "elapsedNs"):
            _integer(run[key], code="SIMULATION_COUNTER_INVALID")
        require(run["engineSourceSha256"] == engine_sha256, "SIMULATION_ENGINE_CHANGED")
        for key in ("selectedCandidateId", "baselineCandidateId"):
            require(type(run[key]) is str and run[key] == "CFG.W01.M12.B12", "SIMULATION_CONTROL_NOT_RETAINED")
        counts = run["counts"]
        _fields(counts, count_fields, "SIMULATION_COUNT_FIELDS_INVALID")
        for value in counts.values():
            _integer(value, code="SIMULATION_COUNTER_INVALID")
        require((counts["epochs"], counts["timelines"], counts["yearsPerTimeline"]) == (1729, 1728, 1728)
                and (counts["nodes"], counts["spheres"], counts["houses"]) == (1728, 144, 12)
                and (counts["trainEpochs"], counts["holdoutEpochs"]) == (1297, 432),
                "SIMULATION_FULL_RUN_REQUIRED")
        require(counts["epochs"] == counts["trainEpochs"] + counts["holdoutEpochs"]
                and counts["evaluatedTimelineYearUpdates"] == counts["representedTimelineYears"]
                    == counts["epochs"] * counts["timelines"] * counts["yearsPerTimeline"]
                and run["auditReplayUpdates"] == 2 * counts["epochs"] * counts["yearsPerTimeline"]
                and counts["acceptedCandidateChanges"] <= counts["trainEpochs"],
                "SIMULATION_COUNT_CONSERVATION_FAILED")
    require(first["seed"] != second["seed"] and first["reportSha256"] != second["reportSha256"],
            "SIMULATION_DISTINCT_RUNS_REQUIRED")
    runs = json.loads(json.dumps([first, second], ensure_ascii=True, separators=(",", ":"), allow_nan=False))
    return {"schema": "atlas.native1728.replicated-simulation/v1", "runs": runs,
        "totalDirectTransitions": sum(row["counts"]["evaluatedTimelineYearUpdates"] for row in runs),
        "totalAdditionalAuditTransitions": sum(row["auditReplayUpdates"] for row in runs),
        "unit": "ONE_SYNTHETIC_REQUEST_CACHE_ADMISSION_TRANSITION",
        "configurationGain": "NONE_SELECTED_CONTROL_RETAINED_IN_BOTH_RUNS",
        "distinctModeledCacheChunkBehaviorsPerRun": 144, "directlyExecutedConfigurationsPerRun": 1728,
        "limits": ["Synthetic years are finite state updates, not elapsed historical years or semantic research.",
                   "Equivalent worker schedules repeat the same cache/chunk behavior.",
                   "The second run changes the workload seed; it does not invent algorithms or source patches."]}


def validate_falsifier(raw, *, source_root=ROOT):
    """Validate the exact retained experiment without rerunning its methods.

    The immutable byte pin is the trust anchor. Derived checks reconcile the
    declared fixed workload, all comparison losses and recorded invocations;
    self-consistent replacement JSON alone is never accepted. This establishes
    retained-record/source integrity, not authentic peer judgments, independent
    ground truth, collaboration quality or elapsed-time reproducibility.
    """
    require(type(raw) is bytes and len(raw) <= 1024 * 1024, "FALSIFIER_RECEIPT_BYTES_INVALID")
    require(sha(raw) == FALSIFIER_RECEIPT_SHA256, "FALSIFIER_RECORDED_RECEIPT_CHANGED")
    value = json.loads(raw)

    def digest(item):
        return sha(json.dumps(item, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=True, allow_nan=False).encode("ascii"))

    require(value["schema"] == "atlas.beast20.provenance-falsifiers/v1"
            and value["status"] == "COMPLETED"
            and value["evidenceKind"] == "SYNTHETIC_CONTRACT_EXPERIMENT",
            "FALSIFIER_EXPERIMENT_INCOMPLETE")
    require(value["reportSha256"] == FALSIFIER_REPORT_SHA256
            == digest({key: item for key, item in value.items() if key != "reportSha256"}),
            "FALSIFIER_LOGICAL_REPORT_CHANGED")
    implementation = value["implementation"]
    require(implementation["paths"] == FALSIFIER_SOURCE_PATHS, "FALSIFIER_SOURCE_PATHS_CHANGED")
    try:
        current_sources = {key: sha((source_root / path).read_bytes())
                           for key, path in FALSIFIER_SOURCE_PATHS.items()}
    except OSError:
        raise ValueError("FALSIFIER_SOURCE_UNAVAILABLE") from None
    require(current_sources == implementation["beforeSha256"] == implementation["afterSha256"]
            and implementation["modulePinSha256"] == current_sources["provenanceModule"],
            "FALSIFIER_SOURCE_CHANGED")
    workload = value["workload"]
    case_ids = [f"F{number:02d}" for number in range(1, 21)]
    require([case["id"] for case in workload] == case_ids
            and value["policySha256"] == digest(value["policy"])
            and value["workloadSha256"] == FALSIFIER_WORKLOAD_SHA256
            == digest({"seed": value["seed"], "policy": value["policy"], "cases": workload}),
            "FALSIFIER_WORKLOAD_OR_POLICY_CHANGED")
    results = value["results"]
    methods = ["VALUES_ONLY_ALL_DOMAINS", "WHOLE_PACKET", "FULL_KEYED_PROVENANCE"]
    require([case["caseId"] for case in results] == case_ids
            and [method["id"] for method in value["methods"]] == methods
            and all([row["method"] for row in case["results"]] == methods for case in results),
            "FALSIFIER_COMPARISON_SET_CHANGED")
    semantic = [{**case, "results": [{key: item for key, item in row.items() if key != "elapsedNs"}
                                      for row in case["results"]]} for case in results]
    require(value["semanticResultsSha256"] == FALSIFIER_SEMANTIC_SHA256
            == digest({"workloadSha256": value["workloadSha256"], "results": semantic}),
            "FALSIFIER_SEMANTIC_RESULTS_CHANGED")
    summaries = {}
    for index, method in enumerate(methods):
        rows = [case["results"][index] for case in results]
        summaries[method] = {
            "caseComparisons": len(rows), "encodingCalls": 2 * len(rows),
            "identityMatches": sum(row["identityMatches"] for row in rows),
            "decisionMatches": sum(row["decisionMatches"] for row in rows),
            "matchesBoth": sum(row["matchesBoth"] for row in rows),
            "losses": sum(not row["matchesBoth"] for row in rows),
            "missedChanges": sum("MISSED_CHANGE" in row["lossReasons"] for row in rows),
            "spuriousChanges": sum("SPURIOUS_CHANGE" in row["lossReasons"] for row in rows),
            "encodingErrors": sum(row["error"] is not None for row in rows),
            "heldCases": [case["caseId"] for case, row in zip(results, rows) if row["reviewDecision"] == "HOLD"],
            "completeFailedCases": [case["caseId"] for case, row in zip(results, rows)
                                    if row["reviewDecision"] == "FAIL"
                                    and row["observation"]["observed"] == row["observation"]["required"]],
        }
    require(value["summary"] == summaries, "FALSIFIER_SUMMARY_OR_LOSSES_CHANGED")
    invocations = value["execution"]["registeredModuleInvocations"]
    operations = ["make_provenance", "validate_provenance", "make_provenance",
                  "validate_provenance", "stale_causes"]
    expected_invocations = [(case_id, operation) for case_id in case_ids for operation in operations]
    require([(row["caseId"], row["operation"]) for row in invocations] == expected_invocations
            and [row["ordinal"] for row in invocations] == list(range(1, 101))
            and all(row["status"] == "RETURNED" and type(row["elapsedNs"]) is int
                    and row["elapsedNs"] >= 0 for row in invocations),
            "FALSIFIER_RECORDED_INVOCATIONS_CHANGED")
    call_counts = {operation: sum(row["operation"] == operation for row in invocations)
                   for operation in set(operations)}
    require(value["execution"]["registeredModuleCallCounts"] == call_counts
            == {"make_provenance": 40, "validate_provenance": 40, "stale_causes": 20}
            and value["counts"] == {"cases": 20, "methods": 3, "caseComparisons": 60,
                                    "encodingCalls": 120, "registeredModuleCalls": len(invocations)}
            and all(item is True for item in value["selfChecks"].values()),
            "FALSIFIER_EXECUTED_COUNTS_CHANGED")
    return value


def module(name, value):
    return ("// Generated from source-checked recorded evidence by export_synthesis20_hosts.py.\n"
            "const freeze=x=>{if(x&&typeof x==='object'){for(const v of Object.values(x))freeze(v);Object.freeze(x);}return x;};\n"
            + "export const " + name + "=freeze(" + json.dumps(value, ensure_ascii=True, separators=(",", ":")) + ");\n")


def simulation(folder):
    manifest = read(folder / "LONG_HORIZON_MANIFEST.json")
    raw = gzip.decompress((folder / "LONG_HORIZON_REPORT.json.gz").read_bytes())
    require(sha(raw) == manifest["reportSha256"], "SIMULATION_REPORT_CHANGED")
    report = validate_simulation(json.loads(raw))
    for filename, row in manifest["files"].items():
        body = raw if filename == "LONG_HORIZON_REPORT.json" else (folder / filename).read_bytes()
        require(sha(body) == row["sha256"] and len(body) == row["bytes"], "SIMULATION_ARTIFACT_CHANGED")
    return {"reportSha256": manifest["reportSha256"], "seed": report["execution"]["seed"],
            "counts": report["counts"], "auditReplayUpdates": report["execution"]["auditReplayUpdates"],
            "elapsedNs": report["execution"]["elapsedNs"],
            "selectedCandidateId": report["meta145"]["selectedCandidateId"],
            "baselineCandidateId": report["meta145"]["baselineCandidateId"],
            "engineSourceSha256": report["execution"]["engineSourceSha256"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--swarm-root", type=Path, required=True)
    parser.add_argument("--atlas-root", type=Path, required=True)
    parser.add_argument("--campaign-dir", type=Path, default=ROOT / "benchmarks/synthesis20/campaign")
    parser.add_argument("--allow-partial", action="store_true", help="Explicit local integration staging; not a complete campaign")
    args = parser.parse_args()
    folder, campaign = ROOT / "benchmarks/synthesis20", args.campaign_dir.resolve(strict=True)
    report = validate_report(read(campaign / "CAMPAIGN_REPORT.json"))
    replay = validate_report(read(campaign / "CAMPAIGN_REPLAY.json"))
    bundle, proof = report_bundle(report), read(campaign / "CAMPAIGN_EXECUTION.json")
    require(read(campaign / "CAMPAIGN_BUNDLE.json") == bundle, "CAMPAIGN_BUNDLE_CHANGED")
    public_proof = campaign_projection(proof, report, replay, allow_partial=args.allow_partial)
    artifacts = read(campaign / "CAMPAIGN_ARTIFACTS.json")
    for row in report["orders"]:
        if row["artifactSha256"] is None:
            continue
        artifact = artifacts["artifacts"][f'F{row["round"]:02d}']
        body = json.dumps(artifact["output"], sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        require(sha(body) == artifact["artifactSha256"] == row["artifactSha256"] == row["outputSha256"],
                "CAMPAIGN_ARTIFACT_CHANGED")
    first = simulation(ROOT / "benchmarks/native1728_evolution")
    second = simulation(folder / "replication1728")
    replication = replication_projection(first, second,
        engine_sha256=sha((ROOT / "benchmarks/native1728_evolution/engine.cpp").read_bytes()))
    falsifier = validate_falsifier((folder / "PROVENANCE_FALSIFIER_RESULTS.json").read_bytes())
    context = {"schema": "atlas.native1728.synthesis-context/v1", "replication": replication,
        "campaignExecution": public_proof,
        "controlledComparison": {key: falsifier[key] for key in ("schema", "status", "evidenceKind", "counts", "summary", "workloadSha256", "reportSha256", "limitations")},
        "campaignArtifactsSha256": sha((campaign / "CAMPAIGN_ARTIFACTS.json").read_bytes()),
        "partialStaging": report["counts"]["observedReviewRounds"] != 20}
    swarm, atlas = args.swarm_root.resolve(strict=True), args.atlas_root.resolve(strict=True)
    for root, project in ((swarm, "appgprj_6af53c11e53481918824eabc8eede04a"),
                          (atlas, "appgprj_6b02e16d290c8191a6c6405fc5227889")):
        require(read(root / ".openai/hosting.json")["project_id"] == project, "HOST_IDENTITY_MISMATCH")
    swarm_file = swarm / "lib/native1728-synthesis-release.mjs"
    swarm_file.write_text("// Exact campaign report; public digest-only peer references.\n"
        + "export const native1728SynthesisBundle=Object.freeze(" + json.dumps(bundle, ensure_ascii=True, separators=(",", ":")) + ");\n"
        + module("native1728SynthesisContext", context), encoding="utf-8")
    code = ("import {pathToFileURL} from 'node:url';const base=process.argv[1];"
            "const {getSynthesisStatus}=await import(pathToFileURL(base+'/lib/native1728-synthesis.mjs'));"
            "const {native1728SynthesisBundle,native1728SynthesisContext}=await import(pathToFileURL(base+'/lib/native1728-synthesis-release.mjs'));"
            "process.stdout.write(JSON.stringify({...getSynthesisStatus(native1728SynthesisBundle),context:native1728SynthesisContext}));")
    projected = json.loads(subprocess.run(["node", "--input-type=module", "-e", code, str(swarm)],
                                         check=True, capture_output=True, text=True, timeout=60).stdout)
    projected["interface"] = "https://swarmchat-private-broker-20261112.tdavesheldon.chatgpt.site/work/integration/synthesis"
    atlas_file = atlas / "librarian/hosting/native1728-synthesis-evidence.mjs"
    atlas_file.write_text(module("native1728SynthesisEvidence", projected), encoding="utf-8")
    receipt = {"schema": "atlas.native1728.synthesis-host-export/v1", "status": "VERIFIED_SOURCE_EXPORTS",
        "reportSha256": bundle["reportSha256"], "partialStaging": context["partialStaging"],
        "swarm": {"path": "lib/native1728-synthesis-release.mjs", "sha256": sha(swarm_file.read_bytes())},
        "atlas": {"path": "librarian/hosting/native1728-synthesis-evidence.mjs", "sha256": sha(atlas_file.read_bytes())},
        "newHostOperations": 2, "publicationPerformedByExporter": False}
    target = campaign / "HOST_EXPORT_MANIFEST.json"
    target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
