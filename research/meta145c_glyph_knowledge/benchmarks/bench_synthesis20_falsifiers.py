#!/usr/bin/env python3
"""Twenty fixed synthetic provenance contracts, with all ablation results kept.

This compares local encodings, not Dagster execution, collaboration quality,
model answers or runtime speed. Each method receives the same twenty cases and
one comparison budget per case. The oracle is declared before any method runs.
No private Work text is loaded or included in the public output.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src/beast20/synthesis_provenance.py"
MODULE_PIN = "2c950acdc7e5dfae64f7cb6a999c3c700e0558d6ae8b98dc53802ede19ad28a8"
SEED = 1452020
MAP_FIELDS = ("inputs", "dependencies", "peer_evidence", "checks")
REQUIRED_CHECKS = ("positive", "negative")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("ascii")).hexdigest()


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


RUNNER_AT_IMPORT = file_digest(__file__)
MODULE_AT_IMPORT = file_digest(MODULE_PATH)
if MODULE_AT_IMPORT != MODULE_PIN:
    raise RuntimeError("FALSIFIER_PROVENANCE_IMPLEMENTATION_PIN_MISMATCH")
sys.path.insert(0, str(ROOT))
from src.beast20 import synthesis_provenance as actual  # noqa: E402

if file_digest(MODULE_PATH) != MODULE_AT_IMPORT:
    raise RuntimeError("FALSIFIER_IMPLEMENTATION_CHANGED_DURING_IMPORT")


# These rules and each case's literal expected result are part of the workload,
# not inferred from a selected method's output. This is a source-declared oracle,
# not an independently preregistered or blinded empirical study.
POLICY = {
    "schema": "atlas.beast20.provenance-falsifier-policy/v1",
    "identityFields": ["code_sha256", *MAP_FIELDS],
    "identityMeaning": "Exact recorded code digest and keyed, domain-specific digest maps.",
    "identityNeutral": ["map insertion order", "annotation", "output_sha256", "observations"],
    "requiredChecks": list(REQUIRED_CHECKS),
    "observationMeaning": "Synthetic check documents, each bound to its declared check digest; not real peer judgments.",
    "reviewDecisionOrder": [
        "Any absent check reference or absent/null/malformed/wrong-digest observation yields HOLD.",
        "Otherwise a complete set containing any FAIL yields FAIL, even at 100% review coverage.",
        "Otherwise a changed provenance identity yields RECHECK_REQUIRED.",
        "Otherwise the unchanged observed fixture yields PASS within this synthetic contract only.",
    ],
    "unchangedOutputRule": "Equal output hashes do not waive a provenance change or missing review evidence.",
    "unchangedIdentityRule": "An irrelevant tag change or reordered maps must not force a provenance change.",
    "scoring": "Identity relation and review decision are scored separately; both must match for a complete case match.",
    "caseBudgetPerMethod": 20,
    "comparisonsPerCase": 1,
    "encodingCallsPerComparison": 2,
    "bestOfSelection": False,
}


def fixture(label):
    return digest({"seed": SEED, "syntheticLabel": label})


def check_document(label, outcome):
    return {"schema": "atlas.beast20.synthetic-check/v1",
            "fixture": fixture(label), "outcome": outcome}


def base_snapshot():
    observations = {name: check_document(name, "PASS") for name in REQUIRED_CHECKS}
    return {
        "provenance": {"code_sha256": fixture("code/v1"),
                       "inputs": {"a": fixture("input/a"), "z": fixture("input/z")},
                       "dependencies": {"b": fixture("dependency/b"), "y": fixture("dependency/y")},
                       "peer_evidence": {"challenge": fixture("peer/challenge"), "response": fixture("peer/response")},
                       "checks": {key: digest(value) for key, value in observations.items()}},
        "observations": observations,
        "annotation": {"parentExperiment": "synthetic-control"},
        "output_sha256": digest({"syntheticOutput": "unchanged"}),
    }


def build_cases():
    cases = []
    base = base_snapshot()

    def add(case_id, name, relation, decision, mutate=None, *, before=None,
            explanation="", witness=None):
        old = deepcopy(base if before is None else before)
        new = deepcopy(old)
        if mutate is not None:
            mutate(new)
        cases.append({
            "id": case_id, "name": name,
            "expected": {"identityRelation": relation, "reviewDecision": decision},
            "explanation": explanation,
            "before": old, "after": new,
            "mapConstructionOrders": {
                side: {field: list(snapshot["provenance"][field]) for field in MAP_FIELDS}
                for side, snapshot in (("before", old), ("after", new))},
            "semanticWitness": witness,
        })

    def rename(snapshot, field, old, new):
        mapping = snapshot["provenance"][field]
        mapping[new] = mapping.pop(old)

    def change_check(snapshot, label, outcome):
        observation = check_document(label, outcome)
        snapshot["observations"]["negative"] = observation
        snapshot["provenance"]["checks"]["negative"] = digest(observation)

    add("F01", "identical_snapshot", "UNCHANGED", "PASS")

    def reorder(snapshot):
        for field in MAP_FIELDS:
            snapshot["provenance"][field] = dict(reversed(list(snapshot["provenance"][field].items())))
    add("F02", "reordered_maps", "UNCHANGED", "PASS", reorder,
        explanation="Map construction order is not an input identity change.")
    add("F03", "irrelevant_parent_label", "UNCHANGED", "PASS",
        lambda s: s["annotation"].update(parentExperiment="different-label"),
        explanation="The explicit neutral annotation must not force invalidation.")
    add("F04", "code_digest_change", "CHANGED", "RECHECK_REQUIRED",
        lambda s: s["provenance"].update(code_sha256=fixture("code/v2")))

    def change_data(snapshot):
        snapshot["provenance"]["inputs"]["a"] = fixture("input/a/v2")
        snapshot["output_sha256"] = digest({"syntheticOutput": "changed"})
    add("F05", "data_digest_change", "CHANGED", "RECHECK_REQUIRED", change_data)
    add("F06", "dependency_digest_change", "CHANGED", "RECHECK_REQUIRED",
        lambda s: s["provenance"]["dependencies"].update(b=fixture("dependency/b/v2")))
    add("F07", "peer_evidence_digest_change", "CHANGED", "RECHECK_REQUIRED",
        lambda s: s["provenance"]["peer_evidence"].update(challenge=fixture("peer/challenge/v2")))
    add("F08", "check_receipt_digest_change", "CHANGED", "RECHECK_REQUIRED",
        lambda s: change_check(s, "negative/new-passing-observation", "PASS"))
    add("F09", "input_key_rename", "CHANGED", "RECHECK_REQUIRED",
        lambda s: rename(s, "inputs", "a", "aa"),
        explanation="The input digest is unchanged, but the binding name changes.")
    add("F10", "dependency_key_rename", "CHANGED", "RECHECK_REQUIRED",
        lambda s: rename(s, "dependencies", "b", "bb"))

    moved = deepcopy(base)
    moved["provenance"]["inputs"] = {"a": fixture("input/a")}
    moved["provenance"]["dependencies"] = {"b": fixture("dependency/b")}
    def move_domain(snapshot):
        snapshot["provenance"]["inputs"]["b"] = snapshot["provenance"]["dependencies"].pop("b")
    add("F11", "dependency_moves_to_input_domain", "CHANGED", "RECHECK_REQUIRED", move_domain,
        before=moved, explanation="The same ordered digest values now occupy different semantic maps.")
    add("F12", "dependency_added", "CHANGED", "RECHECK_REQUIRED",
        lambda s: s["provenance"]["dependencies"].update(c=fixture("dependency/c")))
    add("F13", "dependency_removed", "CHANGED", "RECHECK_REQUIRED",
        lambda s: s["provenance"]["dependencies"].pop("y"))
    add("F14", "challenge_reference_removed", "CHANGED", "RECHECK_REQUIRED",
        lambda s: s["provenance"]["peer_evidence"].pop("challenge"),
        explanation="Removing a challenge reference must be visible; this does not resolve dissent.")
    add("F15", "negative_check_reference_removed", "CHANGED", "HOLD",
        lambda s: s["provenance"]["checks"].pop("negative"),
        explanation="An observation without the required bound reference cannot complete the review.")

    absolute = deepcopy(base)
    absolute["provenance"]["inputs"] = {"number": digest({"number": 3})}
    absolute["output_sha256"] = digest({"absoluteValue": abs(3)})
    def same_output(snapshot):
        snapshot["provenance"]["inputs"]["number"] = digest({"number": -3})
        snapshot["output_sha256"] = digest({"absoluteValue": abs(-3)})
    add("F16", "changed_input_with_invariant_output", "CHANGED", "RECHECK_REQUIRED", same_output,
        before=absolute, explanation="abs(3) equals abs(-3), but input provenance changes and requires recheck.",
        witness={"operation": "abs", "beforeInput": 3, "afterInput": -3,
                 "beforeOutput": abs(3), "afterOutput": abs(-3)})
    add("F17", "complete_review_contains_failure", "CHANGED", "FAIL",
        lambda s: change_check(s, "negative/failing-observation", "FAIL"),
        explanation="Both required observations are present and bound; a failed result remains FAIL.")
    add("F18", "negative_observation_absent", "UNCHANGED", "HOLD",
        lambda s: s["observations"].pop("negative"),
        explanation="The referenced check is unchanged, but no observation is available.")
    add("F19", "negative_observation_explicit_null", "UNCHANGED", "HOLD",
        lambda s: s["observations"].update(negative=None),
        explanation="Null is a distinct missing-observation case, not a passing check.")
    add("F20", "negative_observation_wrong_digest", "UNCHANGED", "HOLD",
        lambda s: s["observations"].update(negative=check_document("unbound-observation", "PASS")),
        explanation="A passing-looking observation for another digest cannot satisfy the bound check.")
    return cases


def make_cases():
    """Public integration API: fresh copies of the fixed twenty-case workload."""
    return build_cases()


def _plain_case(value, depth=0):
    if depth > 16:
        raise ValueError("FALSIFIER_CASE_DEPTH")
    if value is None or type(value) is bool:
        return
    if type(value) is str and len(value) <= 4096:
        return
    if type(value) is int and abs(value) <= 2**53 - 1:
        return
    if type(value) is list and len(value) <= 256:
        for item in value:
            _plain_case(item, depth + 1)
        return
    if type(value) is dict and len(value) <= 256:
        for key, item in value.items():
            if type(key) is not str or len(key) > 160:
                raise ValueError("FALSIFIER_CASE_KEY")
            _plain_case(item, depth + 1)
        return
    raise ValueError("FALSIFIER_CASE_PLAIN_BOUNDED_JSON_REQUIRED")


def _fixed_case(case):
    _plain_case(case)
    if type(case) is not dict or type(case.get("id")) is not str:
        raise ValueError("FALSIFIER_CASE_ID")
    encoded = canonical(case)
    if len(encoded) > 65536:
        raise ValueError("FALSIFIER_CASE_SIZE")
    candidates = {row["id"]: row for row in build_cases()}
    expected = candidates.get(case["id"])
    if expected is None or encoded != canonical(expected):
        raise ValueError("FALSIFIER_CASE_NOT_IN_FIXED_WORKLOAD")
    # Reconstruct the declared map insertion orders after transport through a
    # canonical JSON executor payload. No caller-supplied mutation is accepted.
    return expected


class InvocationBook:
    """Only these actual local module functions may be invoked by the full lane."""

    def __init__(self):
        self.registry = {"make_provenance": actual.make_provenance,
                         "validate_provenance": actual.validate_provenance,
                         "stale_causes": actual.stale_causes}
        self.rows = []

    def call(self, case_id, name, *args, **kwargs):
        start = time.perf_counter_ns()
        status = "RETURNED"
        try:
            return self.registry[name](*args, **kwargs)
        except Exception:
            status = "RAISED"
            raise
        finally:
            self.rows.append({"ordinal": len(self.rows) + 1, "caseId": case_id,
                              "operation": name, "status": status,
                              "elapsedNs": time.perf_counter_ns() - start})


def values_only(snapshot, _book, _case_id):
    p = snapshot["provenance"]
    components = [p["code_sha256"]]
    for field in MAP_FIELDS:
        components.extend(p[field][key] for key in sorted(p[field]))
    return hashlib.sha256("".join(components).encode("ascii")).hexdigest(), None


def whole_packet(snapshot, _book, _case_id):
    return digest(snapshot), None


def full_provenance(snapshot, book, case_id):
    record = book.call(case_id, "make_provenance", **snapshot["provenance"])
    verified = book.call(case_id, "validate_provenance", record)
    return verified["sha256"], verified


METHODS = (
    ("VALUES_ONLY_ALL_DOMAINS", values_only,
     "Simplified omission reference: fixed-length digest values, but no key names or domain boundaries."),
    ("WHOLE_PACKET", whole_packet,
     "Simplified overbinding reference: canonical JSON also includes neutral annotations, outputs and observation availability."),
    ("FULL_KEYED_PROVENANCE", full_provenance,
     "Actual pinned make_provenance and validate_provenance, with an additional actual stale_causes diagnostic."),
)


def review_observations(snapshot):
    missing, failed = [], []
    observed = 0
    for key in REQUIRED_CHECKS:
        refs, observations = snapshot["provenance"]["checks"], snapshot["observations"]
        if key not in refs:
            missing.append({"key": key, "reason": "CHECK_REFERENCE_ABSENT"})
            continue
        if key not in observations:
            missing.append({"key": key, "reason": "OBSERVATION_ABSENT"})
            continue
        observation = observations[key]
        if observation is None:
            missing.append({"key": key, "reason": "OBSERVATION_NULL"})
            continue
        if (type(observation) is not dict or
                observation.get("schema") != "atlas.beast20.synthetic-check/v1" or
                observation.get("outcome") not in {"PASS", "FAIL"}):
            missing.append({"key": key, "reason": "OBSERVATION_MALFORMED"})
            continue
        if digest(observation) != refs[key]:
            missing.append({"key": key, "reason": "OBSERVATION_DIGEST_MISMATCH"})
            continue
        observed += 1
        if observation["outcome"] == "FAIL":
            failed.append(key)
    state = "HOLD" if missing else "FAIL" if failed else "PASS"
    return {"state": state, "required": len(REQUIRED_CHECKS), "observed": observed,
            "missing": missing, "failed": failed}


def compare_case(case, name, encoder, book, encoding_counts):
    start = time.perf_counter_ns()
    before, after = deepcopy(case["before"]), deepcopy(case["after"])
    observation = review_observations(after)
    result = {"method": name, "beforeIdentity": None, "afterIdentity": None,
              "identityRelation": "ERROR", "reviewDecision": "HOLD_ERROR",
              "observation": observation, "causeRows": None, "error": None}
    try:
        encoding_counts[name] += 1
        old_id, old_record = encoder(before, book, case["id"])
        encoding_counts[name] += 1
        new_id, new_record = encoder(after, book, case["id"])
        relation = "UNCHANGED" if old_id == new_id else "CHANGED"
        decision = observation["state"]
        if decision == "PASS" and relation == "CHANGED":
            decision = "RECHECK_REQUIRED"
        result.update(beforeIdentity=old_id, afterIdentity=new_id,
                      identityRelation=relation, reviewDecision=decision)
        if name == "FULL_KEYED_PROVENANCE":
            result["causeRows"] = book.call(case["id"], "stale_causes", old_record, new_record)
    except Exception as error:
        # Retain a method failure on the same case; never drop a losing trial.
        result["error"] = {"type": type(error).__name__, "message": str(error)}
        result.update(identityRelation="ERROR", reviewDecision="HOLD_ERROR")
    result["elapsedNs"] = time.perf_counter_ns() - start
    result["identityMatches"] = result["identityRelation"] == case["expected"]["identityRelation"]
    result["decisionMatches"] = result["reviewDecision"] == case["expected"]["reviewDecision"]
    result["matchesBoth"] = result["identityMatches"] and result["decisionMatches"]
    result["lossReasons"] = []
    if not result["identityMatches"]:
        result["lossReasons"].append("MISSED_CHANGE" if result["identityRelation"] == "UNCHANGED"
                                     else "SPURIOUS_CHANGE" if result["identityRelation"] == "CHANGED"
                                     else "ENCODING_ERROR")
    if not result["decisionMatches"]:
        result["lossReasons"].append("WRONG_REVIEW_DECISION")
    return result


def _evaluate_case(case, book, encoding_counts):
    return {"caseId": case["id"],
            "outputEqual": case["before"]["output_sha256"] == case["after"]["output_sha256"],
            "results": [compare_case(case, name, encoder, book, encoding_counts)
                        for name, encoder, _ in METHODS]}


def _semantic_results(results):
    return [{**case, "results": [{k: v for k, v in row.items() if k != "elapsedNs"}
                                  for row in case["results"]]} for case in results]


def run_case(case):
    """Execute one registered fixed case; return a deterministic review artifact.

    This uses the same comparator, oracle and actual module calls as the full
    experiment. Timings are excluded from this return so existing executor
    receipts can bind stable outputs. It does not implement or accept a patch.
    """
    before = {"runner": file_digest(__file__), "provenanceModule": file_digest(MODULE_PATH)}
    if before != {"runner": RUNNER_AT_IMPORT, "provenanceModule": MODULE_AT_IMPORT}:
        raise RuntimeError("FALSIFIER_SOURCE_CHANGED_AFTER_IMPORT")
    fixed = _fixed_case(case)
    book = InvocationBook()
    counts = dict.fromkeys((name for name, _, _ in METHODS), 0)
    row = _semantic_results([_evaluate_case(fixed, book, counts)])[0]
    after = {"runner": file_digest(__file__), "provenanceModule": file_digest(MODULE_PATH)}
    if before != after:
        raise RuntimeError("FALSIFIER_SOURCE_CHANGED_DURING_CASE")
    result = {
        "schema": "atlas.beast20.provenance-falsifier-case/v1",
        "evidenceKind": "SYNTHETIC_CONTRACT_EXPERIMENT",
        "caseId": fixed["id"], "caseSha256": digest(fixed), "policySha256": digest(POLICY),
        "expected": deepcopy(fixed["expected"]), "outputEqual": row["outputEqual"],
        "results": row["results"],
        "counts": {"caseComparisons": len(row["results"]), "encodingCalls": sum(counts.values()),
                   "registeredModuleCalls": len(book.rows),
                   "registeredModuleCallCounts": {name: sum(r["operation"] == name for r in book.rows)
                                                  for name in book.registry}},
        "fullContractMatches": next(r["matchesBoth"] for r in row["results"] if r["method"] == "FULL_KEYED_PROVENANCE"),
        "implementationSha256": before,
        "scope": "One local synthetic review-result artifact, not a source patch, peer turn, acceptance or hosted result.",
    }
    result["sha256"] = digest(result)
    return result


def run_experiment():
    start = time.perf_counter_ns()
    paths = {"runner": Path(__file__), "provenanceModule": MODULE_PATH}
    before_hashes = {name: file_digest(path) for name, path in paths.items()}
    if before_hashes != {"runner": RUNNER_AT_IMPORT, "provenanceModule": MODULE_AT_IMPORT}:
        raise RuntimeError("FALSIFIER_SOURCE_CHANGED_AFTER_IMPORT")
    cases = make_cases()
    if [c["id"] for c in cases] != [f"F{i:02d}" for i in range(1, 21)]:
        raise RuntimeError("FALSIFIER_FIXED_CASE_SET_REQUIRED")
    for case in cases:
        if (case["expected"]["identityRelation"] not in {"CHANGED", "UNCHANGED"} or
                case["expected"]["reviewDecision"] not in {"PASS", "FAIL", "HOLD", "RECHECK_REQUIRED"}):
            raise RuntimeError("FALSIFIER_ORACLE_INVALID")
    policy_digest = digest(POLICY)
    workload_digest = digest({"seed": SEED, "policy": POLICY, "cases": cases})
    book = InvocationBook()
    encoding_counts = dict.fromkeys((name for name, _, _ in METHODS), 0)
    results = []
    for case in cases:
        results.append(_evaluate_case(case, book, encoding_counts))
    after_hashes = {name: file_digest(path) for name, path in paths.items()}
    if before_hashes != after_hashes:
        raise RuntimeError("FALSIFIER_SOURCE_CHANGED_DURING_EVALUATION")
    summary = {}
    for name, _, _ in METHODS:
        rows = [next(r for r in case["results"] if r["method"] == name) for case in results]
        summary[name] = {
            "caseComparisons": len(rows), "encodingCalls": encoding_counts[name],
            "identityMatches": sum(r["identityMatches"] for r in rows),
            "decisionMatches": sum(r["decisionMatches"] for r in rows),
            "matchesBoth": sum(r["matchesBoth"] for r in rows),
            "losses": sum(not r["matchesBoth"] for r in rows),
            "missedChanges": sum("MISSED_CHANGE" in r["lossReasons"] for r in rows),
            "spuriousChanges": sum("SPURIOUS_CHANGE" in r["lossReasons"] for r in rows),
            "encodingErrors": sum(r["error"] is not None for r in rows),
            "heldCases": [case["caseId"] for case, r in zip(results, rows) if r["reviewDecision"] == "HOLD"],
            "completeFailedCases": [case["caseId"] for case, r in zip(results, rows)
                                    if r["reviewDecision"] == "FAIL" and r["observation"]["observed"] == r["observation"]["required"]],
        }
    pairwise = {}
    for reference in ("VALUES_ONLY_ALL_DOMAINS", "WHOLE_PACKET"):
        counts = {"bothCorrect": 0, "fullOnlyCorrect": 0, "referenceOnlyCorrect": 0, "bothIncorrect": 0}
        for case in results:
            by_name = {r["method"]: r for r in case["results"]}
            full, other = by_name["FULL_KEYED_PROVENANCE"]["matchesBoth"], by_name[reference]["matchesBoth"]
            key = "bothCorrect" if full and other else "fullOnlyCorrect" if full else "referenceOnlyCorrect" if other else "bothIncorrect"
            counts[key] += 1
        pairwise[reference] = counts
    call_counts = {name: sum(row["operation"] == name for row in book.rows) for name in book.registry}
    semantic_results = _semantic_results(results)
    self_checks = {
        "allTwentyCasesRetainedForEveryMethod": all(row["caseComparisons"] == 20 for row in summary.values()),
        "equalEncodingCallBudgetExecuted": all(count == 40 for count in encoding_counts.values()),
        "actualModuleCallBudgetExecuted": call_counts == {"make_provenance": 40, "validate_provenance": 40, "stale_causes": 20},
        "workloadAndOracleUnchanged": workload_digest == digest({"seed": SEED, "policy": POLICY, "cases": cases}) and policy_digest == digest(POLICY),
        "sourceHashesUnchanged": before_hashes == after_hashes,
        "lossesRetained": all(row["matchesBoth"] + row["losses"] == 20 for row in summary.values()),
    }
    report = {
        "schema": "atlas.beast20.provenance-falsifiers/v1", "status": "COMPLETED",
        "evidenceKind": "SYNTHETIC_CONTRACT_EXPERIMENT", "seed": SEED,
        "fixtureGeneration": "Fixed seed labels hashed into synthetic digest values; no random case selection.",
        "groundTruthDeclaredBeforeEvaluation": True, "policy": POLICY, "policySha256": policy_digest,
        "workloadSha256": workload_digest, "workload": cases,
        "methods": [{"id": name, "description": description, "productionBaseline": False,
                     "actualModule": name == "FULL_KEYED_PROVENANCE", "caseBudget": 20}
                    for name, _, description in METHODS],
        "counts": {"cases": len(cases), "methods": len(METHODS), "caseComparisons": sum(r["caseComparisons"] for r in summary.values()),
                   "encodingCalls": sum(encoding_counts.values()), "registeredModuleCalls": len(book.rows)},
        "results": results, "summary": summary, "pairwiseOutcomes": pairwise,
        "semanticResultsSha256": digest({"workloadSha256": workload_digest, "results": semantic_results}),
        "execution": {"elapsedNs": time.perf_counter_ns() - start, "registeredModuleCallCounts": call_counts,
                      "registeredModuleInvocations": book.rows,
                      "countScope": "Top-level registered calls only; nested validation calls are not double counted. Encoding calls overlap module calls and are not additional independent work.",
                      "timingScope": "Actual whole-comparison and registered-call wall time. Methods do different validation work; timings are not a performance comparison or speedup."},
        "implementation": {"paths": {"runner": "benchmarks/bench_synthesis20_falsifiers.py",
                                     "provenanceModule": "src/beast20/synthesis_provenance.py"},
                           "beforeSha256": before_hashes, "afterSha256": after_hashes,
                           "modulePinSha256": MODULE_PIN},
        "selfChecks": self_checks,
        "designChallenges": ["Complete review coverage can still contain a failed check; missing observations must hold.",
                             "Invariance can be correct: irrelevant labels do not alter provenance, and equal outputs do not erase changed inputs."],
        "limitations": [
            "The oracle is an explicit contract declared in source before evaluation, not independently preregistered or blinded ground truth.",
            "The two reference encodings are deliberate simplified ablations, not Dagster, LangGraph, Temporal or in-toto production implementations.",
            "Fixed-length digest inputs do not reproduce Dagster's arbitrary-length concatenation example; the omission reference tests lost names and map domains.",
            "All methods share the same synthetic observation guard. Its FAIL/HOLD behavior is not a gain attributable to the full encoding.",
            "Each method receives every case once, but CPU work differs; no matched model-budget or runtime speed claim is made.",
            "Synthetic check documents and expected outputs are fixtures, not actual peer judgments, model answers or executed acceptance commands.",
            "Full encoding agreement with this declared policy is contract evidence, not a generalization estimate, cognitive-quality result or collaboration benefit.",
            "Only recorded provenance is compared; omitted real dependencies, unauthenticated evidence and unknown source changes remain outside this experiment.",
            "No private Work message bodies, room identifiers or peer identities are included. No source invalidation, dispatch, publication or permissions are performed.",
        ],
    }
    if not all(self_checks.values()):
        report["status"] = "COMPLETED_WITH_INTERNAL_CHECK_FAILURES"
    elif summary["FULL_KEYED_PROVENANCE"]["losses"]:
        report["status"] = "COMPLETED_WITH_CONTRACT_MISMATCHES_RETAINED"
    report["reportSha256"] = digest(report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "benchmarks/synthesis20/PROVENANCE_FALSIFIER_RESULTS.json")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.replace:
        parser.error("output exists; select a fresh path or explicitly --replace")
    report = run_experiment()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="ascii")
    print(json.dumps({key: report[key] for key in ("status", "evidenceKind", "counts", "summary",
                                                  "workloadSha256", "semanticResultsSha256", "reportSha256", "selfChecks")}, indent=2))
    if report["status"] != "COMPLETED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
