"""E17–E20: wire reuse to the actual R10 memory and R11/GF8 APIs.

An explicit callable is the seam for current host READ/RETURN permission.
Test callbacks are not authentication. This module does not create a resident,
model invocation, background schedule, scientific claim or CANON decision.
"""
from __future__ import annotations

from collections import Counter, OrderedDict, deque
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import time
import uuid

from .. import gf8, reasoning_filter
from ..glyph import REGISTRY_SHA, gf7_parts, hsn_parts
from ..memory import LocalMemory
from .execution import TaskSpec
from .storage import ArtifactStore, Scope, canonical_bytes, semantic_key, search_terms


def _digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


class TraceBook:
    """Bounded stage telemetry: timing/counts only, no source bodies or IDs."""
    def __init__(self, capacity=256, clock=time.perf_counter_ns):
        if type(capacity) is not int or not 1 <= capacity <= 10000:
            raise ValueError("TRACE_CAPACITY_INVALID")
        self.capacity, self.clock = capacity, clock
        self.events = deque(maxlen=capacity)
        self.counts = Counter()

    @contextmanager
    def span(self, stage):
        if type(stage) is not str or not re.fullmatch(r"[a-z_]{1,48}", stage):
            raise ValueError("BOUNDED_STAGE_NAME_REQUIRED")
        # Restrict metric dimensions to this runtime's fixed public stages.
        if stage not in {"verified_memory", "topic_views", "physics_context", "cascade", "feed_refresh", "public_search"}:
            raise ValueError("UNKNOWN_TRACE_STAGE")
        start = self.clock()
        status = "OK"
        try:
            yield
        except BaseException:
            status = "ERROR"
            raise
        finally:
            elapsed = max(0, self.clock() - start)
            self.counts[(stage, status)] += 1
            self.events.append({"stage": stage, "status": status, "elapsed_ns": elapsed})

    def report(self):
        return {"schema": "atlas.beast20.telemetry/v1", "capacity": self.capacity,
                "total_spans": sum(self.counts.values()),
                "retained_spans": len(self.events), "spans": list(self.events),
                "counts": [{"stage": stage, "status": status, "count": count}
                           for (stage, status), count in sorted(self.counts.items())]}


class AtlasBeastRuntime:
    """Owner-local, source-scoped front door for measured Atlas computation."""
    def __init__(self, scope: Scope, store: ArtifactStore, authorize, traces=None):
        if type(scope) is not Scope or not callable(authorize):
            raise ValueError("SCOPE_AND_CURRENT_AUTHORIZER_REQUIRED")
        self.scope, self.store, self.authorize = scope, store, authorize
        self._scope_key = scope.key
        self.traces = traces or TraceBook()
        self.stats = Counter()
        # An editable SQLite mapping plus its own hash cannot authenticate a
        # computation. Trust only results computed in this runtime process;
        # re-compute once after restart unless a future host supplies an
        # independently authenticated output checkpoint.
        self._physics_receipts = OrderedDict()
        with store._lock, store.db:
            store.db.execute("CREATE TABLE IF NOT EXISTS beast_runtime_identity(name TEXT PRIMARY KEY,value TEXT NOT NULL)")
            store.db.execute("INSERT OR IGNORE INTO beast_runtime_identity VALUES('feed_consumer',?)", (uuid.uuid4().hex,))
            self._feed_consumer = store.db.execute("SELECT value FROM beast_runtime_identity WHERE name='feed_consumer'").fetchone()[0]
        # Pin implementation bytes as well as user-visible algorithm version.
        self.physics_code_digest = hashlib.sha256(
            Path(gf8.__file__).read_bytes() + b"\0" + Path(reasoning_filter.__file__).read_bytes()
        ).hexdigest()

    def _allow(self, phase):
        self.scope.__post_init__()
        if self.scope.key != self._scope_key:
            raise ValueError("RUNTIME_SCOPE_CHANGED")
        if self.authorize(self.scope, phase) is not True:
            raise PermissionError("CURRENT_WORK_RIGHTS_REQUIRED")
        if self.scope.key != self._scope_key:
            raise ValueError("RUNTIME_SCOPE_CHANGED")

    def verified_memory(self, memory: LocalMemory, coordinates, *, expected_tip, expected_count):
        """Never memoize away verification against the independent checkpoint."""
        self._allow("READ")
        with self.traces.span("verified_memory"):
            result = memory.verified_triage_batch(coordinates, expected_tip=expected_tip,
                                                   expected_count=expected_count)
            self.stats["memory_snapshots_verified"] += 1
        self._allow("RETURN")
        return result

    def topic_views(self, db, memory, coordinates, *, expected_tip, expected_count, limit=50):
        """One checkpoint verification + bounded SQL batches across coordinates.

        The original projection/rank arithmetic is unchanged. Historical topic
        rankings and reversible review deltas stay separate from source truth.
        """
        self._allow("READ")
        if type(limit) is not int or not 1 <= limit <= 500:
            raise ValueError("BAD_LIMIT")
        with self.traces.span("topic_views"):
            deltas = self.verified_memory(memory, coordinates, expected_tip=expected_tip,
                                         expected_count=expected_count)
            items = {coordinate: [] for coordinate in coordinates}
            for offset in range(0, len(coordinates), 400):
                chunk = coordinates[offset:offset + 400]
                sql = ("SELECT c.hsn,c.topic_id,t.label,c.rank,t.original_status "
                       "FROM topic_candidates c JOIN topics t ON c.topic_id=t.id "
                       "WHERE c.hsn IN (" + ",".join("?" for _ in chunk) + ")")
                for hsn, tid, label, rank, status in db.execute(sql, chunk):
                    delta = deltas[hsn].get(tid, 0)
                    items[hsn].append({"topic_id": tid, "label": label,
                        "historical_rank": rank, "raw_source_status": status,
                        "triage_delta": delta,
                        "triage_priority": 100 - rank * 10 + max(-4, min(4, delta)) * 20,
                        "relation": "HISTORICAL_HEURISTIC_CANDIDATE_UNREVIEWED", "authority": "NONE"})
            results = {}
            for hsn, rows in items.items():
                rows.sort(key=lambda x: (-x["triage_priority"], x["topic_id"]))
                results[hsn] = {"coordinate": hsn, "total": len(rows),
                    "shown": len(rows[:limit]), "omitted": max(0, len(rows) - limit),
                    "primary_count": sum(row["historical_rank"] == 1 for row in rows),
                    "alternate_count": sum(row["historical_rank"] > 1 for row in rows),
                    "items": rows[:limit], "triage_memory_used": True,
                    "memory_integrity": "CALLER_CHECKPOINT_MATCHED_LOCAL_SNAPSHOT",
                    "semantic_equivalence_approved": False, "hosted_verified": False,
                    "privacy": "WORK_SYNTHETIC_LOCAL_ONLY", "canon_effect": "NONE"}
            # Catch a memory update during projection; no cached count/tip is
            # treated as proof of current state or hosted authorization.
            memory.verified_triage_batch(coordinates, expected_tip=expected_tip,
                                        expected_count=expected_count)
        self._allow("RETURN")
        return results

    def reasoning_context(self, *, hsn, gf7, plate, drive_hz, source_refs=(),
                          memory=None, expected_tip=None, expected_count=None,
                          grid=33, max_mode=8):
        """Reuse identical GF8 physics across independently typed HSN contexts.

        HSN/GF7 positions never select the physical result. Model source bytes,
        material, geometry, damping, drive, resolution and truncation do.
        Context-specific source refs and review checkpoint are reattached only
        after validation; the output matches the existing reasoning filter.
        """
        self._allow("READ")
        if self.scope.source_digest != REGISTRY_SHA:
            raise ValueError("UNTRUSTED_REGISTRY_EDITION")
        hsn_parts(hsn); gf7_parts(gf7)
        if type(plate) is not gf8.Plate:
            raise ValueError("EXACT_PLATE_REQUIRED")
        if type(source_refs) not in (tuple, list) or len(source_refs) > 8 or any(
                type(ref) is not str or not reasoning_filter.SRC.fullmatch(ref) for ref in source_refs):
            raise ValueError("INVALID_SOURCE_REFERENCES")
        plate.validate()
        if not gf8._finite(drive_hz, 0.1, 1e6) or type(grid) is not int or not 17 <= grid <= 129 or type(max_mode) is not int or not 2 <= max_mode <= 12:
            raise ValueError("DRIVE_PARAMETERS_INVALID")
        source_refs = list(source_refs)
        if memory is None and (expected_tip is not None or expected_count is not None):
            raise ValueError("CHECKPOINT_WITHOUT_MEMORY")
        if memory is not None:
            self.verified_memory(memory, [hsn], expected_tip=expected_tip,
                                 expected_count=expected_count)
        with self.traces.span("physics_context"):
            key = semantic_key(self.scope, "gf8_physical_summary", self.physics_code_digest,
                               {"plate": asdict(plate), "material": plate.metadata(),
                                "drive_hz": drive_hz, "grid": grid, "max_mode": max_mode})
            cached = self.store.memo_get(self.scope, key)
            if cached.hit and key in self._physics_receipts:
                if cached.negative:
                    raise ValueError("PHYSICS_CACHE_SHAPE_INVALID")
                template = cached.value
                if _digest(template) != self._physics_receipts[key]:
                    raise ValueError("PHYSICS_CACHE_SOURCE_MISMATCH")
                self._physics_receipts.move_to_end(key)
                self.stats["physics_hits"] += 1
            else:
                template = reasoning_filter.prepare_reasoning_context(
                    hsn=hsn, gf7=gf7, plate=plate, drive_hz=drive_hz,
                    source_refs=(), review_tip=None, grid=grid, max_mode=max_mode)
                # Context-specific identifiers are never shared as physical input.
                for name in ("receipt_sha256", "hsn", "gf7", "source_refs", "synthetic_review_tip_sha256"):
                    template.pop(name)
                self.store.memo_put(self.scope, key, template, ttl=3600)
                self._physics_receipts[key] = _digest(template)
                if len(self._physics_receipts) > self.store.max_memo_entries:
                    self._physics_receipts.popitem(last=False)
                self.stats["physics_computations"] += 1
            packet = {**template, "hsn": hsn, "gf7": gf7, "source_refs": source_refs,
                      "synthetic_review_tip_sha256": expected_tip if memory is not None else None}
            packet["receipt_sha256"] = reasoning_filter._digest(packet)
            reasoning_filter.safe_explanation(packet)
        if memory is not None:
            memory.verified_triage_batch([hsn], expected_tip=expected_tip,
                                        expected_count=expected_count)
        self._allow("RETURN")
        return packet

    async def run_cascade(self, compiler, executor, node_inputs=None):
        self._allow("READ")
        if compiler.registry_digest != self.scope.source_digest or executor.scope_key != self.scope.key:
            raise ValueError("CASCADE_SOURCE_SCOPE_MISMATCH")
        with self.traces.span("cascade"):
            result = await executor.run_graph(compiler.tasks(node_inputs=node_inputs))
        self._allow("RETURN")
        return result

    def refresh_public_feed(self, poller, url):
        """Connect changed feed heads to the scoped index and dependency graph.

        No historical source revision is promoted to a factual assertion.
        Provider no-store responses do not enter either persistent component.
        A changed document invalidates only memo results depending on it.
        """
        self._allow("READ")
        with self.traces.span("feed_refresh"):
            result = poller.poll(self.scope.key, url)
            indexed, invalidated = 0, set()
            delivered, has_more = 0, False
            if result["status"] != "NO_STORE":
                self._allow("READ")
                pending = poller.pending(self.scope.key, url, self._feed_consumer)
                has_more = pending["has_more"]
                for event in pending["items"]:
                    item = event["item"]
                    from .feeds import canonical_url
                    source_url = canonical_url(url)
                    doc_id = "feed:" + _digest([source_url, item["id"]])
                    raw = canonical_bytes(item)
                    self.store.put_object(self.scope, raw)
                    text = "\n".join(item[key] for key in ("title", "text", "content_html"))
                    changed = self.store.upsert_document(self.scope, doc_id, text, polarity="RELATED",
                        metadata={"source_url": source_url, "item_id": item["id"],
                                  "revision_sha256": item["revision_sha256"],
                                  "status": "PUBLIC_SOURCE_UNREVIEWED"})
                    if changed:
                        indexed += 1
                    # Replaying after a crash must finish invalidation even if
                    # the document write committed before the interruption.
                    invalidated.update(self.store.invalidate(self.scope, [doc_id]))
                    self._allow("RETURN")
                    poller.ack(self.scope.key, url, self._feed_consumer, event["sequence"])
                    delivered += 1
            receipt = {key: value for key, value in result.items() if key != "items"}
            receipt.update({"indexed_documents": indexed, "invalidated_keys": len(invalidated),
                            "delivered_changes": delivered, "delivery_has_more": has_more,
                            "automatic_crosswalk_acceptance": False})
        self._allow("RETURN")
        return receipt

    def search_public(self, query, limit=20):
        self._allow("READ")
        with self.traces.span("public_search"):
            result = self.store.search(self.scope, query, limit=limit)
        self._allow("RETURN")
        return result


class CascadeCompiler:
    """Original source nodes → 144 Sphere reductions → 12 Houses → META145.

    These are concrete lexical/digest computations, not 1,885 expert turns.
    Supplemental per-node Work inputs are separate from the source snapshot.
    Changing one supplementary input invalidates just its node, Sphere, House
    and final reduction; changing the source edition changes the entire scope.
    """
    def __init__(self, snapshot):
        self.registry_digest = snapshot.registry_sha
        self._registry_digest = self.registry_digest
        self._algorithm_version = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self.nodes = json.loads(canonical_bytes(snapshot.nodes))
        self.spheres = json.loads(canonical_bytes(snapshot.spheres))
        self.houses = json.loads(canonical_bytes(snapshot.houses))
        if (len(self.nodes), len(self.spheres), len(self.houses)) != (1728, 144, 12):
            raise ValueError("CASCADE_CARDINALITY_INVALID")
        for hsn in self.nodes:
            hsn_parts(hsn)
        self._frozen_digest = _digest({"nodes": self.nodes, "spheres": self.spheres, "houses": self.houses})

    @staticmethod
    def handlers():
        def node(payload, parents):
            if parents:
                raise ValueError("NODE_HAS_UNEXPECTED_PARENTS")
            terms = sorted(search_terms(payload["name"]))
            return {"kind": "NODE", "node_count": 1, "coordinate": payload["hsn"],
                    "source_record_digest": payload["record_digest"],
                    "source_kind": payload["kind"], "node_unique_terms_sum": len(terms),
                    "lexical_digest": _digest(terms),
                    "supplement_digest": _digest(payload["supplemental"])}

        def reduce(payload, parents):
            if len(parents) != payload["children"]:
                raise ValueError("CASCADE_CHILD_COUNT_INVALID")
            return {"kind": payload["kind"], "coordinate": payload["id"],
                    "node_count": sum(row["node_count"] for row in parents.values()),
                    "node_unique_terms_sum": sum(row["node_unique_terms_sum"] for row in parents.values()),
                    "children": len(parents),
                    "child_output_digest": _digest(parents),
                    "semantic_approval": False, "model_turns": 0}
        return {"atlas_node": node, "atlas_reduce": reduce}

    def tasks(self, node_inputs=None):
        if self.registry_digest != self._registry_digest:
            raise ValueError("CASCADE_SOURCE_IDENTITY_CHANGED")
        if _digest({"nodes": self.nodes, "spheres": self.spheres, "houses": self.houses}) != self._frozen_digest:
            raise ValueError("CASCADE_SNAPSHOT_MUTATED")
        inputs = {} if node_inputs is None else json.loads(canonical_bytes(node_inputs))
        if type(inputs) is not dict or any(key not in self.nodes for key in inputs):
            raise ValueError("UNKNOWN_SUPPLEMENTAL_COORDINATE")
        tasks = []
        for nid, row in sorted(self.nodes.items()):
            tasks.append(TaskSpec(nid, "atlas_node", {"hsn": nid, "name": row["name"],
                                  "kind": row["kind"], "record_digest": row["source_record_sha256"],
                                  "supplemental": inputs.get(nid)}, house=nid[:3], version=self._algorithm_version))
        for sid, row in sorted(self.spheres.items()):
            tasks.append(TaskSpec(sid, "atlas_reduce", {"id": sid, "kind": "SPHERE", "children": 12},
                                  dependencies=tuple(row["children"]), house=sid[:3], version=self._algorithm_version))
        for hid, row in sorted(self.houses.items()):
            tasks.append(TaskSpec(hid, "atlas_reduce", {"id": hid, "kind": "HOUSE", "children": 12},
                                  dependencies=tuple(row["children"]), house=hid, version=self._algorithm_version))
        tasks.append(TaskSpec("META145", "atlas_reduce", {"id": "META145", "kind": "META", "children": 12},
                              dependencies=tuple(sorted(self.houses)), house="H01", version=self._algorithm_version))
        return tasks
