"""Twenty bounded, evidence-linked local review/build cycles.

This is a coordinator over :class:`AsyncExecutor`, not a new scheduler,
canonical task ledger, peer identity service, or model runner. Trusted host
code registers local handlers/checks and supplies current provenance and
authorization callbacks. Source hashes describe integrity; they do not grant
permissions. A positive result is local artifact/check evidence only.

Private observations retain the detached message a host actually read. Their
hashes are CLIENT_OBSERVED, and attribution is always SELF_DECLARED. Public
reports contain only those hashes, public order/subject labels, and outcomes.
They never contain peer message bodies, room/member/request identifiers,
handler outputs, artifact bytes, local paths, or exception text.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import inspect
import json
import math
from pathlib import Path
import re
from typing import Any, Callable

from .execution import AsyncExecutor, TaskSpec
from .federation import PinnedFederation, ENGINEERING
from .storage import Scope
from .synthesis_provenance import make_provenance, stale_causes, validate_provenance


SCHEMA = "atlas.beast20.synthesis-report/v1"
BUNDLE_SCHEMA = "atlas.beast20.synthesis-bundle/v1"
REGISTRY_SHA256 = "07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6"
PREDECESSOR_COMMIT = "2b825532125890dfe294a50f2ba3668bbd2c7d63"
PREDECESSOR_REPORT_SHA256 = "18cb16f53f2ee02fb3ae9ee599ea3bb8154b86dad83ac99cbb57af955eb3e1de"
EXCELLENCE_COMMIT = "389965f3aaa90c99815f8c727836ca342ef7f313"
LIMITS = {"maxRounds": 20, "maxOrders": 20, "maxExecutorCalls": 40,
          "maxChecksPerOrder": 20, "maxPeerObservations": 80,
          "maxOutputBytes": 65536, "maxArtifactBytes": 1048576}
NON_CLAIMS = [
    "Local campaign checks are not canonical EX1728 completion or publication.",
    "Peer references are client-observed content hashes with SELF_DECLARED attribution, not authenticated identities.",
    "Review rounds, executor calls, test receipts and implemented orders are distinct; genuine resident turns remain zero.",
    "Replayed or unchanged evidence earns no new implementation; retained cached check receipts are not newly executed tests.",
    "Cross-domain relationships are analogies, not semantic equivalence or evidence of improved answer quality.",
    "Registered callbacks are trusted local code; this coordinator is not an OS sandbox or an external-effects dispatcher.",
    "Declared challenge dispositions preserve dissent and do not establish independent peer acceptance.",
]
REASON_CODES = frozenset({
    "SOURCE_STALE", "PROVENANCE_UNAVAILABLE", "MISSING_PEER_EVIDENCE",
    "MISSING_POSITIVE_CHECK", "MISSING_NEGATIVE_CHECK", "UNRESOLVED_CHALLENGE",
    "DISPOSITION_CHECK_MISSING", "DISPOSITION_CHECK_FAILED", "HANDLER_FAILED",
    "OUTPUT_INVALID", "CHECK_FAILED", "ACCEPTANCE_UNBOUND", "ACCEPTANCE_REJECTED",
    "DEPENDENCY_BLOCKED", "EXECUTOR_FAILED", "EXECUTOR_DEFERRED",
    "REPLAYED_EVIDENCE", "NO_ARTIFACT_CHANGE", "DEPENDENCY_STALE",
})
_HEX = re.compile(r"[a-f0-9]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}\Z")
_SUCCESS = {"SUCCEEDED", "CACHED"}
_EXECUTION_STATES = _SUCCESS | {"DEAD_LETTER", "DEFERRED_BUSY", "DEFERRED_CIRCUIT",
                               "BLOCKED_DEPENDENCY", "NOT_RUN"}
_STATES = {"PLANNED", "RUNNING", "IMPLEMENTED", "VERIFIED", "INTEGRATED", "BLOCKED", "INVALIDATED"}
_MODULE_PATH = Path(__file__).resolve()
_PROVENANCE_PATH = _MODULE_PATH.with_name("synthesis_provenance.py")
_MODULE_SHA = hashlib.sha256(_MODULE_PATH.read_bytes()).hexdigest()
_PROVENANCE_SHA = hashlib.sha256(_PROVENANCE_PATH.read_bytes()).hexdigest()


def _require(ok, code):
    if not ok:
        raise ValueError(code)


def _digest(value):
    _require(type(value) is str and _HEX.fullmatch(value), "SYNTHESIS_DIGEST_INVALID")
    return value


def _identifier(value):
    _require(type(value) is str and _ID.fullmatch(value)
             and value not in {"__proto__", "constructor", "prototype"}
             and not value.startswith(("EX.", "H01.", "H02.", "H03.", "H04.", "H05.", "H06.",
                                       "H07.", "H08.", "H09.", "H10.", "H11.", "H12.")),
             "PUBLIC_CAMPAIGN_IDENTIFIER_REQUIRED")
    return value


def _canonical(value, maximum=4 * 1024 * 1024):
    def plain(item, depth=0):
        _require(depth <= 32, "SYNTHESIS_JSON_DEPTH")
        if item is None or type(item) in (str, bool):
            return
        if type(item) is int:
            _require(abs(item) <= 9007199254740991, "SYNTHESIS_JSON_INTEGER_BOUND")
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is list:
            for child in item:
                plain(child, depth + 1)
            return
        if type(item) is dict and all(type(k) is str for k in item):
            for child in item.values():
                plain(child, depth + 1)
            return
        raise ValueError("SYNTHESIS_PLAIN_FINITE_JSON_REQUIRED")
    plain(value)
    body = json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")
    _require(len(body) <= maximum, "SYNTHESIS_JSON_BYTES_BOUND")
    return body


def evidence_sha256(value):
    """Hash bounded canonical ASCII JSON; not an authentication signature."""
    return hashlib.sha256(_canonical(value)).hexdigest()


def _copy(value, maximum=4 * 1024 * 1024):
    return json.loads(_canonical(value, maximum))


def _subject(value):
    _require(type(value) is dict and set(value) == {"artifactId", "baselineSha256"},
             "SYNTHESIS_SUBJECT_INVALID")
    return {"artifactId": _identifier(value["artifactId"]),
            "baselineSha256": _digest(value["baselineSha256"])}


def make_order_provenance(*, handler_code_sha256, payload, subject, dependencies=None,
                          peer_refs=(), check_codes=None, inputs=None):
    """Bind all order semantics, plus host-supplied keyed current input digests.

    ``dependencies`` maps campaign order IDs to their planned provenance hash;
    the executor also binds actual parent result digests. ``inputs`` may add
    source/artifact pins but cannot override payload, subject or registry.
    """
    extra = {} if inputs is None else inputs
    _require(type(extra) is dict and not set(extra) & {"payload", "subject", "registry"},
             "SYNTHESIS_RESERVED_INPUT")
    _require(type(peer_refs) in (list, tuple) and len(peer_refs) <= 80,
             "SYNTHESIS_PEER_BOUND")
    refs = [_digest(x) for x in peer_refs]
    _require(len(refs) == len(set(refs)), "SYNTHESIS_DUPLICATE_PEER")
    return make_provenance(code_sha256=handler_code_sha256,
        inputs={**extra, "payload": evidence_sha256(payload),
                "subject": evidence_sha256(_subject(subject)), "registry": REGISTRY_SHA256},
        dependencies={} if dependencies is None else dependencies,
        peer_evidence={ref: ref for ref in refs}, checks={} if check_codes is None else check_codes)


def make_peer_observation(record):
    """Detach a host-observed Work row. No field proves who authored it.

    Retain this private object locally. Only ``sha256`` is exported. The host
    must obtain the row through its authorized room reader; this constructor
    can validate content shape but cannot attest a server or a resident.
    """
    required = {"roomId", "seq", "requestId", "memberId", "kind", "topic", "text"}
    optional = {"parentSeq", "referenceSeqs", "evidenceRefs", "createdAt"}
    _require(type(record) is dict and required <= set(record) <= required | optional,
             "SYNTHESIS_PEER_FIELDS")
    data = _copy(record, 16384)
    for field in required - {"seq"}:
        _require(type(data[field]) is str and 0 < len(data[field]) <= (8000 if field == "text" else 512),
                 "SYNTHESIS_PEER_FIELD_INVALID")
    _require(type(data["seq"]) is int and 1 <= data["seq"] <= 1000000, "SYNTHESIS_PEER_SEQ_INVALID")
    _require(data["kind"] in {"context", "proposal", "question", "objection", "revision", "decision", "summary", "creative"},
             "SYNTHESIS_PEER_KIND_INVALID")
    for field in ("parentSeq",):
        if field in data:
            _require(data[field] is None or (type(data[field]) is int and 0 < data[field] < data["seq"]),
                     "SYNTHESIS_PEER_PARENT_INVALID")
    if "referenceSeqs" in data:
        refs = data["referenceSeqs"]
        _require(type(refs) is list and len(refs) <= 100 and all(type(x) is int and 0 < x < data["seq"] for x in refs)
                 and len(refs) == len(set(refs)), "SYNTHESIS_PEER_REFERENCES_INVALID")
    if "evidenceRefs" in data:
        _require(type(data["evidenceRefs"]) is list and len(data["evidenceRefs"]) <= 20
                 and all(type(x) is str and x.startswith("https://") and len(x) <= 2048 for x in data["evidenceRefs"]),
                 "SYNTHESIS_PEER_LINKS_INVALID")
    if "createdAt" in data:
        _require(type(data["createdAt"]) is str and 0 < len(data["createdAt"]) <= 128,
                 "SYNTHESIS_PEER_TIME_INVALID")
    body = {"schema": "atlas.beast20.peer-observation/v1", "record": data,
            "attribution": "SELF_DECLARED", "integrity": "CLIENT_OBSERVED"}
    return {**body, "sha256": evidence_sha256(body)}


@dataclass(frozen=True)
class LocalHandler:
    function: Callable
    code_sha256: str
    effect: str = "PURE"


@dataclass(frozen=True)
class LocalCheck:
    function: Callable
    kind: str
    code_sha256: str


@dataclass(frozen=True)
class ArtifactResult:
    artifact: bytes
    output: Any


@dataclass(frozen=True)
class BuildOrder:
    order_id: str
    round_number: int
    handler: str
    payload: Any
    subject: dict
    provenance: dict
    dependencies: tuple[str, ...] = ()
    check_ids: tuple[str, ...] = ()
    peer_refs: tuple[str, ...] = ()
    challenge_refs: tuple[str, ...] = ()
    acceptance_task_id: str | None = None


@dataclass(frozen=True)
class ChallengeDisposition:
    challenge_ref: str
    action: str
    response_ref: str | None = None
    check_ids: tuple[str, ...] = ()


class ExcellenceBinding:
    """Read/verify existing genuine task evidence; never transition a ledger.

    The binding consumes the exact mounted AcceptanceRunner/EvidenceLedger
    types. A matching campaign artifact is required. No local check is minted
    into an Excellence receipt, and no canonical completion counter advances.
    """
    def __init__(self, federation, ledger):
        _require(type(federation) is PinnedFederation and "excellence" in federation._mounts,
                 "GENUINE_EXCELLENCE_MOUNT_REQUIRED")
        self.federation, self.ledger = federation, ledger
        self._verify()

    def _verify(self):
        mount = self.federation._mounts["excellence"]
        _require(mount.descriptor()["source_commit"] == EXCELLENCE_COMMIT, "EXCELLENCE_SOURCE_PIN_REQUIRED")
        mount.verify()
        api, _ = self.federation._plan()
        _require(type(self.ledger) is api.EvidenceLedger and type(self.ledger._runner) is api.AcceptanceRunner
                 and self.ledger.plan_sha256 == self.federation._plan_sha, "GENUINE_PLAN_LEDGER_REQUIRED")
        return mount, api

    def inspect(self, task_id, artifact_sha256):
        _require(type(task_id) is str and ENGINEERING.fullmatch(task_id), "ENGINEERING_ID_REQUIRED")
        _digest(artifact_sha256)
        mount, _ = self._verify()
        # Refresh is the existing ledger's own invalidation rule, not a new
        # campaign authority. It can invalidate stale historical evidence.
        self.ledger.refresh()
        record = self.ledger._records().get(task_id)
        _require(record is not None, "ENGINEERING_TASK_UNKNOWN")
        matched = False
        for stage, receipt in record["receipts"].items():
            verified = self.ledger._runner.verify(receipt, task_id, stage)
            matched |= artifact_sha256 in verified["artifact_sha256"].values()
        mount.verify()
        return {"bound": True, "taskId": task_id, "state": record["state"],
                "subjectMatched": matched and record["state"] in {"IMPLEMENTED", "VERIFIED", "INTEGRATED"}}


async def _invoke(function, *arguments):
    value = function(*arguments)
    return await value if inspect.isawaitable(value) else value


class SynthesisCoordinator:
    """One bounded graph at a time over an existing durable AsyncExecutor.

    ``observe_provenance(order_dict)`` must freshly observe bound source/code/
    dependency/peer/check identities. Echoing the plan is not source validation.
    It is called before admission, immediately around real work, and on every
    return including cached replay. Callbacks with equal bound work semantics
    must observe the same sources irrespective of the cosmetic round label.
    """
    def __init__(self, db_path, *, scope, campaign_id, handlers, checks,
                 observe_provenance, authorize, acceptance=None, workers=4):
        _require(type(scope) is Scope and scope.source_digest == REGISTRY_SHA256, "ORIGINAL_WORK_SCOPE_REQUIRED")
        _require(type(campaign_id) is str and 0 < len(campaign_id) <= 512, "CAMPAIGN_ID_REQUIRED")
        _require(type(handlers) is dict and 1 <= len(handlers) <= 20, "LOCAL_HANDLER_REGISTRY_REQUIRED")
        _require(type(checks) is dict and len(checks) <= 100, "LOCAL_CHECK_REGISTRY_REQUIRED")
        for name, entry in handlers.items():
            _identifier(name)
            _require(type(entry) is LocalHandler and callable(entry.function)
                     and entry.effect in {"PURE", "IDEMPOTENT_LOCAL"}, "PURE_LOCAL_HANDLER_REQUIRED")
            _digest(entry.code_sha256)
        for name, entry in checks.items():
            _identifier(name)
            _require(type(entry) is LocalCheck and callable(entry.function) and entry.kind in {"POSITIVE", "NEGATIVE"},
                     "LOCAL_CHECK_INVALID")
            _digest(entry.code_sha256)
        _require(callable(observe_provenance) and callable(authorize), "CURRENT_HOST_CALLBACKS_REQUIRED")
        _require(acceptance is None or type(acceptance) is ExcellenceBinding, "GENUINE_ACCEPTANCE_BINDING_REQUIRED")
        _require(type(workers) is int and 1 <= workers <= 20, "SYNTHESIS_WORKER_BOUND")
        self.scope, self._scope_key = scope, scope.key
        self.campaign_id = "SYN20-" + hashlib.sha256(campaign_id.encode("utf-8")).hexdigest()[:24]
        self.handlers, self.checks = dict(handlers), dict(checks)
        self.observe_provenance, self.authorize, self.acceptance = observe_provenance, authorize, acceptance
        self._running = False
        self._orders, self._calls, self._build_calls, self._gate_calls = {}, {}, {}, {}
        self._eval_orders, self._gate_holds = {}, {}
        self._guard("READ")
        self.executor = AsyncExecutor(db_path, {"synthesis_evaluate": self._evaluate, "synthesis_accept": self._accept},
            scope_key=evidence_sha256({"scope": self._scope_key, "campaign": self.campaign_id,
                                      "coordinator": _MODULE_SHA, "provenance": _PROVENANCE_SHA}),
            workers=workers, max_tasks=40, max_graphs=1, task_timeout=30, lease_seconds=60,
            circuit_threshold=100)

    def close(self):
        self.executor.close()

    def _guard(self, phase):
        if (self.scope.key != self._scope_key or self.authorize(self.scope, phase) is not True
                or self.scope.key != self._scope_key):
            raise PermissionError("SYNTHESIS_CURRENT_AUTHORIZATION_DENIED")
        _require(hashlib.sha256(_MODULE_PATH.read_bytes()).hexdigest() == _MODULE_SHA
                 and hashlib.sha256(_PROVENANCE_PATH.read_bytes()).hexdigest() == _PROVENANCE_SHA,
                 "SYNTHESIS_LOADED_CODE_CHANGED")

    async def _observe(self, order):
        try:
            return validate_provenance(await _invoke(self.observe_provenance, _copy(order)))
        except Exception:
            return None

    def _normalize(self, orders, peer_observations, dispositions):
        _require(type(orders) in (list, tuple) and len(orders) <= 20, "SYNTHESIS_ORDER_BOUND")
        _require(type(peer_observations) in (list, tuple) and len(peer_observations) <= 80, "SYNTHESIS_PEER_BOUND")
        peers, peer_positions, peer_requests = {}, set(), set()
        for item in peer_observations:
            _require(type(item) is dict and set(item) == {"schema", "record", "attribution", "integrity", "sha256"},
                     "SYNTHESIS_PEER_OBSERVATION_REQUIRED")
            item = _copy(item, 32768)
            detached = make_peer_observation(item["record"])
            _require(detached == item, "SYNTHESIS_PEER_HASH_MISMATCH")
            _require(item["sha256"] not in peers, "SYNTHESIS_DUPLICATE_PEER")
            position = (item["record"]["roomId"], item["record"]["seq"])
            request = (item["record"]["roomId"], item["record"]["requestId"])
            _require(position not in peer_positions and request not in peer_requests,
                     "SYNTHESIS_PEER_REVISION_CONFLICT")
            peer_positions.add(position)
            peer_requests.add(request)
            peers[item["sha256"]] = detached
        normalized = {}
        for item in orders:
            _require(type(item) is BuildOrder, "SYNTHESIS_BUILD_ORDER_REQUIRED")
            name = _identifier(item.order_id)
            _require(name not in normalized, "SYNTHESIS_DUPLICATE_ORDER")
            _require(type(item.round_number) is int and 1 <= item.round_number <= 20, "SYNTHESIS_ROUND_BOUND")
            _identifier(item.handler)
            _require(item.handler in self.handlers, "SYNTHESIS_HANDLER_UNREGISTERED")
            lists = {}
            for key, values, limit, validator in (
                ("dependencies", item.dependencies, 20, _identifier), ("checkIds", item.check_ids, 20, _identifier),
                ("peerRefs", item.peer_refs, 80, _digest), ("challengeRefs", item.challenge_refs, 80, _digest)):
                _require(type(values) in (tuple, list) and len(values) <= limit, "SYNTHESIS_LIST_BOUND")
                validated = [validator(x) for x in values]
                _require(len(validated) == len(set(validated)), "SYNTHESIS_DUPLICATE_REFERENCE")
                lists[key] = sorted(validated)
            _require(set(lists["checkIds"]) <= set(self.checks), "SYNTHESIS_CHECK_UNREGISTERED")
            _require(set(lists["peerRefs"]) <= set(peers), "SYNTHESIS_UNKNOWN_PEER")
            _require(set(lists["challengeRefs"]) == {ref for ref in lists["peerRefs"]
                     if peers[ref]["record"]["kind"] == "objection"},
                     "SYNTHESIS_CHALLENGE_REFERENCE_INVALID")
            task = item.acceptance_task_id
            _require(task is None or (type(task) is str and ENGINEERING.fullmatch(task)), "ENGINEERING_ID_REQUIRED")
            normalized[name] = {"id": name, "round": item.round_number, "handler": item.handler,
                "payload": _copy(item.payload, 65536), "subject": _subject(item.subject),
                "provenance": validate_provenance(item.provenance), **lists, "acceptanceTaskId": task}
        # Reuse executor graph validation for unknown dependencies and cycles,
        # before any current-source callback or handler is invoked.
        if normalized:
            self.executor._validate([TaskSpec(x["id"], "synthesis_evaluate", None,
                                              tuple(x["dependencies"]), max_attempts=1)
                                     for x in normalized.values()])
        for item in normalized.values():
            prov = item["provenance"]
            expected = make_order_provenance(handler_code_sha256=self.handlers[item["handler"]].code_sha256,
                payload=item["payload"], subject=item["subject"],
                dependencies={dep: normalized[dep]["provenance"]["sha256"] for dep in item["dependencies"]},
                peer_refs=item["peerRefs"], check_codes={key: self.checks[key].code_sha256 for key in item["checkIds"]},
                inputs={key: value for key, value in prov["inputs"].items() if key not in {"payload", "subject", "registry"}})
            _require(expected == prov, "SYNTHESIS_ORDER_PROVENANCE_MISMATCH")
        _require(type(dispositions) in (tuple, list) and len(dispositions) <= 80, "SYNTHESIS_DISPOSITION_BOUND")
        challenges = {ref for item in normalized.values() for ref in item["challengeRefs"]}
        resolutions = {}
        for item in dispositions:
            _require(type(item) is ChallengeDisposition and item.challenge_ref in challenges
                     and item.challenge_ref not in resolutions and item.action in {"ADDRESSED", "REJECTED", "DEFERRED"},
                     "SYNTHESIS_DISPOSITION_INVALID")
            _require(item.response_ref is None or (item.response_ref in peers and item.response_ref != item.challenge_ref),
                     "SYNTHESIS_DISPOSITION_RESPONSE_INVALID")
            if item.response_ref is not None:
                challenge, response = peers[item.challenge_ref]["record"], peers[item.response_ref]["record"]
                _require(response["roomId"] == challenge["roomId"] and response["seq"] > challenge["seq"]
                         and (response.get("parentSeq") == challenge["seq"]
                              or challenge["seq"] in response.get("referenceSeqs", [])),
                         "SYNTHESIS_DISPOSITION_REPLY_BINDING_INVALID")
            _require(type(item.check_ids) in (tuple, list) and len(item.check_ids) <= 20, "SYNTHESIS_DISPOSITION_CHECK_BOUND")
            ids = [_identifier(x) for x in item.check_ids]
            _require(len(ids) == len(set(ids)) and set(ids) <= set(self.checks), "SYNTHESIS_DISPOSITION_CHECK_INVALID")
            resolutions[item.challenge_ref] = {"challengeRef": item.challenge_ref, "action": item.action,
                                              "responseRef": item.response_ref, "checkIds": sorted(ids)}
        return normalized, resolutions

    @staticmethod
    def _causes(before, after):
        if after is None:
            return []
        return [{**row, "key": "key:" + hashlib.sha256(row["key"].encode("ascii")).hexdigest()}
                for row in stale_causes(before, after)]

    def _blank(self, order, reasons, observed=None):
        return {"status": "HOLD", "reasonCodes": sorted(set(reasons)), "output": None,
                "outputSha256": None, "artifactSha256": None, "changed": False, "checks": [],
                "observedProvenanceSha256": None if observed is None else observed["sha256"],
                "staleCauses": self._causes(order["provenance"], observed),
                "acceptance": {"bound": False, "taskId": order["acceptanceTaskId"],
                               "state": None, "subjectMatched": False}}

    async def _evaluate(self, payload, parents):
        token = payload["token"]
        self._calls[token] = self._calls.get(token, 0) + 1
        order = self._orders[token]
        self._guard("DISPATCH")
        observed = await self._observe(order)
        reasons = list(payload["reasons"])
        if observed is None:
            reasons.append("PROVENANCE_UNAVAILABLE")
        elif observed != order["provenance"]:
            reasons.append("SOURCE_STALE")
        result = self._blank(order, reasons, observed)
        if reasons:
            return result
        self._build_calls[token] = self._build_calls.get(token, 0) + 1
        try:
            built = await _invoke(self.handlers[order["handler"]].function,
                                  _copy(order["payload"]), _copy(parents))
        except Exception:
            result.update(status="FAIL", reasonCodes=["HANDLER_FAILED"])
            return result
        try:
            _require(type(built) is ArtifactResult and type(built.artifact) is bytes
                     and len(built.artifact) <= LIMITS["maxArtifactBytes"], "SYNTHESIS_ARTIFACT_INVALID")
            output = _copy(built.output, LIMITS["maxOutputBytes"])
            artifact_sha = hashlib.sha256(built.artifact).hexdigest()
        except Exception:
            result.update(status="FAIL", reasonCodes=["OUTPUT_INVALID"])
            return result
        result.update(output=output, outputSha256=evidence_sha256(output), artifactSha256=artifact_sha,
                      changed=artifact_sha != order["subject"]["baselineSha256"])
        for check_id in order["checkIds"]:
            check = self.checks[check_id]
            try:
                passed = await _invoke(check.function, built.artifact, _copy(output), _copy(order["payload"])) is True
            except Exception:
                passed = False
            receipt = {"id": check_id, "kind": check.kind, "passed": passed,
                       "subjectSha256": artifact_sha, "outputSha256": result["outputSha256"],
                       "codeSha256": check.code_sha256}
            receipt["receiptSha256"] = evidence_sha256({"schema": "atlas.beast20.synthesis-check/v1", **receipt})
            result["checks"].append(receipt)
        if any(not row["passed"] for row in result["checks"]):
            result["reasonCodes"].append("CHECK_FAILED")
        if order["acceptanceTaskId"] is not None:
            try:
                result["acceptance"] = self.acceptance.inspect(order["acceptanceTaskId"], artifact_sha)
                if not result["acceptance"]["subjectMatched"]:
                    result["reasonCodes"].append("ACCEPTANCE_REJECTED")
            except Exception:
                result["reasonCodes"].append("ACCEPTANCE_REJECTED")
        observed = await self._observe(order)
        result["observedProvenanceSha256"] = None if observed is None else observed["sha256"]
        result["staleCauses"] = self._causes(order["provenance"], observed)
        if observed is None:
            result["reasonCodes"].append("PROVENANCE_UNAVAILABLE")
        elif observed != order["provenance"]:
            result["reasonCodes"].append("SOURCE_STALE")
        self._guard("RETURN")
        result["reasonCodes"] = sorted(set(result["reasonCodes"]))
        result["status"] = ("FAIL" if "CHECK_FAILED" in result["reasonCodes"] else
                            "HOLD" if result["reasonCodes"] else "PASS")
        return result

    async def _accept(self, payload, parents):
        key = payload["evaluation"]
        self._gate_calls[key] = self._gate_calls.get(key, 0) + 1
        self._guard("DISPATCH")
        result = parents[key]
        if result["status"] != "PASS":
            raise ValueError("SYNTHESIS_ORDER_NOT_ACCEPTED")
        order = self._eval_orders[key]
        current = await self._observe(order)
        if current is None or current != order["provenance"]:
            self._gate_holds[key] = "PROVENANCE_UNAVAILABLE" if current is None else "SOURCE_STALE"
            raise ValueError("SYNTHESIS_GATE_SOURCE_CHANGED")
        return {"status": "PASS", "artifactSha256": result["artifactSha256"],
                "outputSha256": result["outputSha256"], "output": result["output"]}

    async def run(self, orders, *, peer_observations=(), dispositions=()):
        """Execute a partial or complete 20-cycle campaign and return redacted evidence.

        All graph/shape checks precede dispatch. Cache hits still recheck current
        provenance and permission. Failed evaluation gates block dependent work.
        A report is a detached snapshot, not a mutable canonical completion row.
        """
        _require(not self._running, "SYNTHESIS_RUN_ALREADY_ACTIVE")
        self._running = True
        try:
            self._guard("READ")
            specs, resolutions = self._normalize(orders, peer_observations, dispositions)
            self._orders, self._calls, self._build_calls, self._gate_calls = {}, {}, {}, {}
            self._eval_orders, self._gate_holds = {}, {}
            tasks, tokens, original_observed = [], {}, {}
            for name, order in sorted(specs.items()):
                observed = await self._observe(order)
                original_observed[name] = observed
                reasons = []
                if observed is None:
                    reasons.append("PROVENANCE_UNAVAILABLE")
                elif observed != order["provenance"]:
                    reasons.append("SOURCE_STALE")
                if not order["peerRefs"]:
                    reasons.append("MISSING_PEER_EVIDENCE")
                kinds = {self.checks[key].kind for key in order["checkIds"]}
                for kind in ("POSITIVE", "NEGATIVE"):
                    if kind not in kinds:
                        reasons.append("MISSING_" + kind + "_CHECK")
                for ref in order["challengeRefs"]:
                    disposition = resolutions.get(ref)
                    if (disposition is None or disposition["action"] == "DEFERRED"
                            or disposition["responseRef"] not in order["peerRefs"]):
                        reasons.append("UNRESOLVED_CHALLENGE")
                    elif not disposition["checkIds"] or not set(disposition["checkIds"]) <= set(order["checkIds"]):
                        reasons.append("DISPOSITION_CHECK_MISSING")
                if order["acceptanceTaskId"] is not None and self.acceptance is None:
                    reasons.append("ACCEPTANCE_UNBOUND")
                semantics = {key: value for key, value in order.items() if key not in {"id", "round", "dependencies"}}
                semantics["observedProvenance"] = observed
                semantics["dispositions"] = [resolutions.get(ref) for ref in order["challengeRefs"]]
                token = evidence_sha256(semantics)
                self._orders.setdefault(token, order)
                tokens[name] = token
                evaluation, gate = "eval:" + name, "gate:" + name
                self._eval_orders[evaluation] = order
                tasks.append(TaskSpec(evaluation, "synthesis_evaluate", {"token": token, "reasons": sorted(set(reasons))},
                    tuple("gate:" + dep for dep in order["dependencies"]), version="1", max_attempts=1))
                tasks.append(TaskSpec(gate, "synthesis_accept", {"evaluation": evaluation},
                                      (evaluation,), version="1", max_attempts=1))
            graph = await self.executor.run_graph(tasks) if tasks else None
            rows = []
            for name, order in sorted(specs.items(), key=lambda pair: (pair[1]["round"], pair[0])):
                evaluation, gate, token = "eval:" + name, "gate:" + name, tokens[name]
                eval_status = graph.receipts[evaluation]["status"]
                gate_status = graph.receipts[gate]["status"]
                result = _copy(graph.outputs.get(evaluation, self._blank(order, [
                    "DEPENDENCY_BLOCKED" if eval_status == "BLOCKED_DEPENDENCY" else
                    "EXECUTOR_DEFERRED" if eval_status.startswith("DEFERRED") else "EXECUTOR_FAILED"],
                    original_observed[name])))
                if eval_status == "DEAD_LETTER":
                    result["status"] = "FAIL"
                if gate_status not in _SUCCESS and result["status"] == "PASS":
                    result["status"] = "HOLD"
                    result["reasonCodes"].append(self._gate_holds.get(evaluation,
                        "EXECUTOR_DEFERRED" if gate_status.startswith("DEFERRED") else "EXECUTOR_FAILED"))
                # Return-time checks occur even when both executor jobs hit cache.
                current = await self._observe(order)
                if current is None or current != order["provenance"]:
                    result["reasonCodes"].append("PROVENANCE_UNAVAILABLE" if current is None else "SOURCE_STALE")
                    if result["status"] != "FAIL":
                        result["status"] = "HOLD"
                result["observedProvenanceSha256"] = None if current is None else current["sha256"]
                result["staleCauses"] = self._causes(order["provenance"], current)
                if order["acceptanceTaskId"] is not None and result["artifactSha256"] is not None:
                    try:
                        result["acceptance"] = self.acceptance.inspect(order["acceptanceTaskId"], result["artifactSha256"])
                        accepted = result["acceptance"]["subjectMatched"]
                    except Exception:
                        accepted = False
                    if not accepted:
                        result["reasonCodes"].append("ACCEPTANCE_REJECTED")
                        if result["status"] != "FAIL":
                            result["status"] = "HOLD"
                # Allocate a shared invocation once, never once per label.
                representative = self._orders[token]["id"] == name
                calls = self._calls.pop(token, 0) if representative else 0
                builds = self._build_calls.pop(token, 0) if representative else 0
                gates = self._gate_calls.get(evaluation, 0)
                status = result["status"]
                phase = ("FAILED" if status == "FAIL" else
                         "STALE" if "SOURCE_STALE" in result["reasonCodes"] else
                         "HELD" if status == "HOLD" else
                         "VERIFIED_REUSE" if builds == 0 else
                         "NO_CHANGE" if not result["changed"] else "TESTED")
                if phase == "VERIFIED_REUSE":
                    result["reasonCodes"].append("REPLAYED_EVIDENCE")
                if phase == "NO_CHANGE":
                    result["reasonCodes"].append("NO_ARTIFACT_CHANGE")
                rows.append({"id": name, "round": order["round"], "subject": order["subject"],
                    "status": status, "phase": phase, "reasonCodes": sorted(set(result["reasonCodes"])),
                    "provenanceSha256": order["provenance"]["sha256"],
                    "observedProvenanceSha256": result["observedProvenanceSha256"], "staleCauses": result["staleCauses"],
                    "peerRefs": order["peerRefs"], "challengeRefs": order["challengeRefs"],
                    "outputSha256": result["outputSha256"], "artifactSha256": result["artifactSha256"],
                    "changed": result["changed"], "executor": {"evaluationStatus": eval_status,
                        "gateStatus": gate_status, "actualCalls": calls + gates, "handlerCalls": builds},
                    "checks": result["checks"], "acceptance": result["acceptance"],
                    "implemented": phase == "TESTED" and builds > 0})
            # A source that changes late also invalidates every dependent public
            # result; historical successful execution is preserved in its fields.
            by_id = {row["id"]: row for row in rows}
            changed = True
            while changed:
                changed = False
                for row in rows:
                    if row["status"] == "PASS" and any(by_id[d]["status"] != "PASS" for d in specs[row["id"]]["dependencies"]):
                        row.update(status="HOLD", phase="STALE", implemented=False)
                        row["reasonCodes"] = sorted(set(row["reasonCodes"]) | {"DEPENDENCY_STALE"})
                        changed = True
            challenges = []
            for ref in sorted({ref for row in rows for ref in row["challengeRefs"]}):
                disposition = resolutions.get(ref)
                challenges.append({"ref": ref, "orderIds": sorted(row["id"] for row in rows if ref in row["challengeRefs"]),
                    "status": "UNRESOLVED" if disposition is None else
                        "DEFERRED" if disposition["action"] == "DEFERRED" else "DECLARED_" + disposition["action"],
                    "responseRef": None if disposition is None else disposition["responseRef"],
                    "checkIds": [] if disposition is None else disposition["checkIds"],
                    "dispositionSha256": None if disposition is None else evidence_sha256(disposition)})
            rounds = []
            for number in range(1, 21):
                members = [row for row in rows if row["round"] == number]
                refs = sorted({ref for row in members for ref in row["peerRefs"]})
                state = ("PLANNED" if not members else "FAIL" if any(row["status"] == "FAIL" for row in members)
                         else "HOLD" if any(row["status"] == "HOLD" for row in members) else "PASS")
                rounds.append({"round": number, "status": state, "orderIds": [row["id"] for row in members], "peerRefs": refs})
            report = {"schema": SCHEMA, "campaignId": self.campaign_id,
                "source": {"registrySha256": REGISTRY_SHA256, "predecessorCommit": PREDECESSOR_COMMIT,
                    "predecessorReportSha256": PREDECESSOR_REPORT_SHA256, "coordinatorCodeSha256": _MODULE_SHA,
                    "provenanceCodeSha256": _PROVENANCE_SHA, "excellenceCommit": EXCELLENCE_COMMIT if self.acceptance else None},
                "status": "FAIL" if any(row["status"] == "FAIL" for row in rows) else
                          "HOLD" if len({row["round"] for row in rows}) < 20 or any(row["status"] == "HOLD" for row in rows) else "PASS",
                "limits": dict(LIMITS), "counts": _counts(rows, rounds, challenges),
                "rounds": rounds, "orders": rows, "challenges": challenges, "nonClaims": list(NON_CLAIMS)}
            self._guard("RETURN")
            return validate_report(report)
        finally:
            self._running = False
            self._orders = {}


def _counts(rows, rounds, challenges):
    return {"requestedRounds": 20, "observedReviewRounds": sum(bool(row["orderIds"] and row["peerRefs"]) for row in rounds),
        "ordersSubmitted": len(rows), "ordersComputed": sum(row["executor"]["handlerCalls"] for row in rows),
        "ordersPassed": sum(row["status"] == "PASS" for row in rows),
        "ordersHeld": sum(row["status"] == "HOLD" for row in rows),
        "ordersFailed": sum(row["status"] == "FAIL" for row in rows),
        "ordersReused": sum(row["phase"] == "VERIFIED_REUSE" for row in rows),
        "ordersNoChange": sum(row["phase"] == "NO_CHANGE" for row in rows),
        "implementedOrders": sum(row["implemented"] for row in rows),
        "executorCalls": sum(row["executor"]["actualCalls"] for row in rows),
        "testReceipts": sum(len(row["checks"]) for row in rows),
        "peerObservations": len({ref for row in rows for ref in row["peerRefs"]}),
        "unresolvedChallenges": sum(row["status"] in {"UNRESOLVED", "DEFERRED"} for row in challenges),
        "genuineResidentTurns": 0, "canonicalTasksCompleted": 0}


def _validate_report(report):
    """Validate a bounded detached public report, including receipt bindings.

    This checks consistency, not authenticity of a rehashed report. The host
    must bind the exact report bytes to an independently retained receipt.
    """
    data = _copy(report)
    _require(type(data) is dict and set(data) == {"schema", "campaignId", "source", "status", "limits", "counts", "rounds", "orders", "challenges", "nonClaims"},
             "SYNTHESIS_REPORT_FIELDS")
    _require(data["schema"] == SCHEMA and type(data["campaignId"]) is str
             and re.fullmatch(r"SYN20-[a-f0-9]{24}", data["campaignId"]), "SYNTHESIS_REPORT_SCHEMA")
    source = data["source"]
    _require(type(source) is dict and set(source) == {"registrySha256", "predecessorCommit", "predecessorReportSha256", "coordinatorCodeSha256", "provenanceCodeSha256", "excellenceCommit"},
             "SYNTHESIS_SOURCE_FIELDS")
    _require(source["registrySha256"] == REGISTRY_SHA256 and source["predecessorCommit"] == PREDECESSOR_COMMIT
             and source["predecessorReportSha256"] == PREDECESSOR_REPORT_SHA256
             and source["excellenceCommit"] in {None, EXCELLENCE_COMMIT}, "SYNTHESIS_SOURCE_PINS")
    for key in ("coordinatorCodeSha256", "provenanceCodeSha256"):
        _digest(source[key])
    _require(data["limits"] == LIMITS and data["nonClaims"] == NON_CLAIMS, "SYNTHESIS_LIMITS_OR_NONCLAIMS")
    rows, rounds, challenges = data["orders"], data["rounds"], data["challenges"]
    _require(type(rows) is list and len(rows) <= 20 and type(rounds) is list and len(rounds) == 20
             and type(challenges) is list and len(challenges) <= 80, "SYNTHESIS_REPORT_BOUNDS")
    seen = set()
    order_fields = {"id", "round", "subject", "status", "phase", "reasonCodes", "provenanceSha256", "observedProvenanceSha256", "staleCauses", "peerRefs", "challengeRefs", "outputSha256", "artifactSha256", "changed", "executor", "checks", "acceptance", "implemented"}
    for row in rows:
        _require(type(row) is dict and set(row) == order_fields, "SYNTHESIS_ORDER_REPORT_FIELDS")
        _identifier(row["id"])
        _require(row["id"] not in seen and type(row["round"]) is int and 1 <= row["round"] <= 20, "SYNTHESIS_ORDER_REPORT_ID")
        seen.add(row["id"])
        _subject(row["subject"])
        _digest(row["provenanceSha256"])
        for key in ("observedProvenanceSha256", "outputSha256", "artifactSha256"):
            if row[key] is not None:
                _digest(row[key])
        _require((row["artifactSha256"] is None) == (row["outputSha256"] is None), "SYNTHESIS_ARTIFACT_OUTPUT_PAIR")
        _require(type(row["changed"]) is bool and row["changed"] == (row["artifactSha256"] is not None and row["artifactSha256"] != row["subject"]["baselineSha256"]), "SYNTHESIS_CHANGED_MISMATCH")
        allowed = {"PASS": {"TESTED", "VERIFIED_REUSE", "NO_CHANGE"}, "HOLD": {"HELD", "STALE"}, "FAIL": {"FAILED"}}
        _require(row["status"] in allowed and row["phase"] in allowed[row["status"]], "SYNTHESIS_PHASE_MISMATCH")
        reasons = row["reasonCodes"]
        _require(type(reasons) is list and all(type(x) is str for x in reasons) and reasons == sorted(set(reasons))
                 and set(reasons) <= REASON_CODES, "SYNTHESIS_REASON_CODES")
        for field in ("peerRefs", "challengeRefs"):
            values = row[field]
            _require(type(values) is list and len(values) <= 80, "SYNTHESIS_PUBLIC_REFS")
            for value in values:
                _digest(value)
            _require(values == sorted(set(values)), "SYNTHESIS_PUBLIC_REF_ORDER")
        _require(set(row["challengeRefs"]) <= set(row["peerRefs"]), "SYNTHESIS_PUBLIC_CHALLENGES")
        ex = row["executor"]
        _require(type(ex) is dict and set(ex) == {"evaluationStatus", "gateStatus", "actualCalls", "handlerCalls"}
                 and ex["evaluationStatus"] in _EXECUTION_STATES and ex["gateStatus"] in _EXECUTION_STATES
                 and type(ex["actualCalls"]) is int and 0 <= ex["actualCalls"] <= 2
                 and type(ex["handlerCalls"]) is int and 0 <= ex["handlerCalls"] <= 1
                 and ex["handlerCalls"] <= ex["actualCalls"], "SYNTHESIS_EXECUTOR_REPORT_INVALID")
        _require(type(row["implemented"]) is bool and row["implemented"] ==
                 (row["phase"] == "TESTED" and row["changed"] and ex["handlerCalls"] == 1), "SYNTHESIS_IMPLEMENTED_MISMATCH")
        if row["phase"] == "TESTED":
            _require(row["changed"] and ex["handlerCalls"] == 1 and ex["evaluationStatus"] == "SUCCEEDED"
                     and not reasons, "SYNTHESIS_TESTED_EVIDENCE_MISMATCH")
        elif row["phase"] == "NO_CHANGE":
            _require(not row["changed"] and ex["handlerCalls"] == 1 and ex["evaluationStatus"] == "SUCCEEDED"
                     and reasons == ["NO_ARTIFACT_CHANGE"], "SYNTHESIS_NO_CHANGE_MISMATCH")
        elif row["phase"] == "VERIFIED_REUSE":
            _require(ex["handlerCalls"] == 0 and reasons == ["REPLAYED_EVIDENCE"], "SYNTHESIS_REUSE_MISMATCH")
        else:
            _require(bool(reasons), "SYNTHESIS_NONSUCCESS_REASON_REQUIRED")
        _require(not set(reasons) & {"HANDLER_FAILED", "OUTPUT_INVALID", "CHECK_FAILED"}
                 or row["status"] == "FAIL", "SYNTHESIS_FAILURE_PROMOTED")
        receipts = row["checks"]
        _require(type(receipts) is list and len(receipts) <= 20, "SYNTHESIS_CHECK_RECEIPT_BOUND")
        check_ids = set()
        for receipt in receipts:
            _require(type(receipt) is dict and set(receipt) == {"id", "kind", "passed", "subjectSha256", "outputSha256", "codeSha256", "receiptSha256"}, "SYNTHESIS_CHECK_RECEIPT_FIELDS")
            _identifier(receipt["id"])
            _require(receipt["id"] not in check_ids and receipt["kind"] in {"POSITIVE", "NEGATIVE"}
                     and type(receipt["passed"]) is bool, "SYNTHESIS_CHECK_RECEIPT_INVALID")
            check_ids.add(receipt["id"])
            for field in ("subjectSha256", "outputSha256", "codeSha256", "receiptSha256"):
                _digest(receipt[field])
            _require(receipt["subjectSha256"] == row["artifactSha256"] and receipt["outputSha256"] == row["outputSha256"], "SYNTHESIS_CHECK_SUBJECT_MISMATCH")
            body = {key: value for key, value in receipt.items() if key != "receiptSha256"}
            _require(receipt["receiptSha256"] == evidence_sha256({"schema": "atlas.beast20.synthesis-check/v1", **body}), "SYNTHESIS_CHECK_RECEIPT_HASH")
        if row["status"] == "PASS":
            _require(row["peerRefs"] and row["artifactSha256"] is not None
                     and row["observedProvenanceSha256"] == row["provenanceSha256"]
                     and not row["staleCauses"]
                     and {x["kind"] for x in receipts} == {"POSITIVE", "NEGATIVE"}
                     and all(x["passed"] for x in receipts) and ex["evaluationStatus"] in _SUCCESS
                     and ex["gateStatus"] in _SUCCESS, "SYNTHESIS_PASS_EVIDENCE_MISSING")
        _require(not any(not x["passed"] for x in receipts) or row["status"] == "FAIL", "SYNTHESIS_FAILED_CHECK_PROMOTED")
        acceptance = row["acceptance"]
        _require(type(acceptance) is dict and set(acceptance) == {"bound", "taskId", "state", "subjectMatched"}
                 and type(acceptance["bound"]) is bool and type(acceptance["subjectMatched"]) is bool
                 and (acceptance["taskId"] is None or type(acceptance["taskId"]) is str and ENGINEERING.fullmatch(acceptance["taskId"]))
                 and acceptance["state"] in _STATES | {None}, "SYNTHESIS_ACCEPTANCE_FIELDS")
        _require(not acceptance["subjectMatched"] or (acceptance["bound"] and acceptance["taskId"] is not None
                 and acceptance["state"] in {"IMPLEMENTED", "VERIFIED", "INTEGRATED"}), "SYNTHESIS_ACCEPTANCE_UNBOUND")
        _require(acceptance["bound"] or (acceptance["state"] is None and not acceptance["subjectMatched"]),
                 "SYNTHESIS_ACCEPTANCE_STATE_WITHOUT_BINDING")
        _require(not acceptance["bound"] or (source["excellenceCommit"] == EXCELLENCE_COMMIT
                 and acceptance["taskId"] is not None), "SYNTHESIS_ACCEPTANCE_SOURCE_REQUIRED")
        if acceptance["taskId"] is not None and row["status"] == "PASS":
            _require(acceptance["bound"] and acceptance["subjectMatched"], "SYNTHESIS_ACCEPTANCE_REQUIRED")
        causes = row["staleCauses"]
        _require(type(causes) is list and len(causes) <= 1025, "SYNTHESIS_STALE_CAUSE_BOUND")
        for cause in causes:
            _require(type(cause) is dict and set(cause) == {"category", "key", "before", "after"}
                     and cause["category"] in {"CODE", "DATA", "DEPENDENCIES", "PEER_EVIDENCE", "CHECKS"}
                     and type(cause["key"]) is str and re.fullmatch(r"key:[a-f0-9]{64}", cause["key"]), "SYNTHESIS_STALE_CAUSE_INVALID")
            for side in ("before", "after"):
                if cause[side] is not None:
                    _digest(cause[side])
            _require(cause["before"] != cause["after"], "SYNTHESIS_STALE_CAUSE_UNCHANGED")
    _require(rows == sorted(rows, key=lambda row: (row["round"], row["id"])), "SYNTHESIS_ORDER_SORT")
    for number, row in enumerate(rounds, 1):
        _require(type(row) is dict and type(row.get("round")) is int, "SYNTHESIS_ROUND_TYPE")
        members = [item for item in rows if item["round"] == number]
        status = ("PLANNED" if not members else "FAIL" if any(x["status"] == "FAIL" for x in members)
                  else "HOLD" if any(x["status"] == "HOLD" for x in members) else "PASS")
        expected = {"round": number, "status": status, "orderIds": [x["id"] for x in members],
                    "peerRefs": sorted({ref for x in members for ref in x["peerRefs"]})}
        _require(row == expected, "SYNTHESIS_ROUND_MISMATCH")
    challenge_refs = sorted({ref for row in rows for ref in row["challengeRefs"]})
    _require(len(challenges) == len(challenge_refs), "SYNTHESIS_CHALLENGE_COUNT")
    for ref, row in zip(challenge_refs, challenges):
        _require(type(row) is dict and set(row) == {"ref", "orderIds", "status", "responseRef", "checkIds", "dispositionSha256"}
                 and row["ref"] == ref and row["orderIds"] == sorted(x["id"] for x in rows if ref in x["challengeRefs"])
                 and row["status"] in {"UNRESOLVED", "DECLARED_ADDRESSED", "DECLARED_REJECTED", "DEFERRED"}, "SYNTHESIS_CHALLENGE_ROW")
        for field in ("responseRef", "dispositionSha256"):
            if row[field] is not None:
                _digest(row[field])
        _require(type(row["checkIds"]) is list and len(row["checkIds"]) <= 20, "SYNTHESIS_CHALLENGE_CHECKS")
        for check_id in row["checkIds"]:
            _identifier(check_id)
        _require(row["checkIds"] == sorted(set(row["checkIds"])), "SYNTHESIS_CHALLENGE_CHECK_ORDER")
        if row["status"] == "UNRESOLVED":
            _require(row["responseRef"] is None and row["dispositionSha256"] is None and not row["checkIds"], "SYNTHESIS_UNRESOLVED_DISPOSITION")
        else:
            disposition = {"challengeRef": ref, "action": row["status"].removeprefix("DECLARED_"),
                           "responseRef": row["responseRef"], "checkIds": row["checkIds"]}
            _require(row["dispositionSha256"] == evidence_sha256(disposition), "SYNTHESIS_DISPOSITION_HASH")
        for order in (item for item in rows if item["id"] in row["orderIds"]):
            if row["status"] in {"UNRESOLVED", "DEFERRED"}:
                _require(order["status"] != "PASS", "SYNTHESIS_UNRESOLVED_CHALLENGE_PROMOTED")
            elif order["status"] == "PASS":
                passed_ids = {receipt["id"] for receipt in order["checks"] if receipt["passed"]}
                _require(row["responseRef"] in order["peerRefs"] and row["responseRef"] != ref
                         and row["checkIds"] and set(row["checkIds"]) <= passed_ids,
                         "SYNTHESIS_DISPOSITION_EVIDENCE_MISSING")
    _require(type(data["counts"]) is dict and all(type(value) is int and value >= 0 for value in data["counts"].values()),
             "SYNTHESIS_COUNT_INTEGER_REQUIRED")
    _require(data["counts"] == _counts(rows, rounds, challenges), "SYNTHESIS_COUNTS_MISMATCH")
    _require(data["counts"]["executorCalls"] <= 40 and data["counts"]["peerObservations"] <= 80, "SYNTHESIS_EXECUTION_BUDGET")
    status = ("FAIL" if any(row["status"] == "FAIL" for row in rows) else
              "HOLD" if len({row["round"] for row in rows}) < 20 or any(row["status"] == "HOLD" for row in rows) else "PASS")
    _require(data["status"] == status, "SYNTHESIS_STATUS_MISMATCH")
    return data


def validate_report(report):
    """Validate/detach the public evidence projection; never authenticate it.

    Malformed JSON-shaped values always reject with a bounded ValueError,
    including type substitutions that would otherwise raise a TypeError during
    an enum lookup. This is structural and semantic consistency verification,
    not proof that an untrusted producer actually ran the recorded work.
    """
    try:
        return _validate_report(report)
    except (TypeError, KeyError, AttributeError, OverflowError, RecursionError) as error:
        raise ValueError("SYNTHESIS_REPORT_INVALID") from None


def report_bundle(report):
    data = validate_report(report)
    body = _canonical(data)
    return {"schema": BUNDLE_SCHEMA, "reportJson": body.decode("ascii"),
            "reportSha256": hashlib.sha256(body).hexdigest()}


def compact_summary(report):
    data = validate_report(report)
    return {key: data[key] for key in ("schema", "campaignId", "source", "status", "limits", "counts", "nonClaims")}
