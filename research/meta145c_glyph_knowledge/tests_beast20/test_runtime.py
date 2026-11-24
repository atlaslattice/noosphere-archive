import asyncio
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from src.beast20.execution import AsyncExecutor
from src.beast20.feeds import FeedPoller, Response
from src.beast20.runtime import AtlasBeastRuntime, CascadeCompiler, TraceBook
from src.beast20.storage import ArtifactStore, Scope
from src.core import SourceSnapshot
from src.gf8 import Plate, mode_hz
from src.glyph import REGISTRY_SHA, positional_gf7
from src.knowledge import topic_view
from src.memory import LocalMemory
from src.reasoning_filter import prepare_reasoning_context
from tests_public.test_synthetic_core import synthetic


def review(event_id="note1", coordinate="H01.S01.N01", action="NOTE", topic="T1", target=None):
    return {"event_id": event_id, "mode": "WORK", "scope": "SYNTHETIC_LOCAL_REVIEW",
            "coordinate": coordinate, "topic_id": topic, "action": action,
            "source_ref": "urn:atlas:synthetic:beast20", "source_digest": "a" * 64,
            "retract_event_id": target}


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.scope = Scope(REGISTRY_SHA, "ariadne-reader/v0.7", "synthetic-test", 1)
        self.store = ArtifactStore()
        self.allowed = True
        self.runtime = AtlasBeastRuntime(self.scope, self.store, lambda *_: self.allowed)
        self.memory = LocalMemory(":memory:")
        self.db = sqlite3.connect(":memory:")
        self.db.executescript("CREATE TABLE topics(id TEXT,label TEXT,original_status TEXT); CREATE TABLE topic_candidates(topic_id TEXT,hsn TEXT,rank INTEGER);")
        self.db.executemany("INSERT INTO topics VALUES(?,?,?)", [("T1", "first", "UNREVIEWED"), ("T2", "second", "UNREVIEWED")])
        self.db.executemany("INSERT INTO topic_candidates VALUES(?,?,?)", [("T1", "H01.S01.N01", 1), ("T2", "H01.S01.N01", 2), ("T2", "H02.S02.N02", 3)])

    def tearDown(self):
        self.store.close(); self.memory.close(); self.db.close()

    def test_topic_batch_exact_legacy_parity_valid_fixture(self):
        self.memory.append(review(topic="T2"))
        checkpoint = self.memory.verify()
        coordinates = ["H01.S01.N01", "H02.S02.N02", "H12.S12.N12"]
        expected = {hsn: topic_view(self.db, hsn, self.memory) for hsn in coordinates}
        actual = self.runtime.topic_views(self.db, self.memory, coordinates,
                    expected_tip=checkpoint["tip"], expected_count=checkpoint["count"])
        self.assertEqual(actual, expected)
        self.assertEqual(actual[coordinates[0]]["items"][0]["topic_id"], "T2")

    def test_old_checkpoint_and_truncated_history_rejected(self):
        empty = self.memory.verify()
        self.memory.append(review())
        current = self.memory.verify()
        with self.assertRaisesRegex(ValueError, "CHECKPOINT_CHANGED"):
            self.runtime.verified_memory(self.memory, ["H01.S01.N01"],
                expected_tip=empty["tip"], expected_count=0)
        self.memory.db.execute("DELETE FROM review_events"); self.memory.db.commit()
        with self.assertRaisesRegex(ValueError, "CHECKPOINT_CHANGED"):
            self.runtime.verified_memory(self.memory, ["H01.S01.N01"],
                expected_tip=current["tip"], expected_count=1)

    def test_tampered_memory_cannot_affect_projection(self):
        self.memory.append(review())
        tip = self.memory.verify()["tip"]
        self.memory.db.execute("UPDATE review_events SET action='CHALLENGE'"); self.memory.db.commit()
        with self.assertRaisesRegex(ValueError, "FAIL_CHAIN"):
            self.runtime.topic_views(self.db, self.memory, ["H01.S01.N01"], expected_tip=tip, expected_count=1)

    def test_retraction_has_exact_zero_delta(self):
        self.memory.append(review())
        self.memory.append(review("retract1", action="RETRACT", target="note1"))
        checkpoint = self.memory.verify()
        rows = self.runtime.verified_memory(self.memory, ["H01.S01.N01"],
                    expected_tip=checkpoint["tip"], expected_count=2)
        self.assertEqual(rows["H01.S01.N01"], {})

    def test_physics_reuse_exact_packet_parity_across_coordinates(self):
        plate = Plate(); frequency = mode_hz(plate, 1, 1)
        for n in range(1, 13):
            hsn = f"H01.S01.N{n:02d}"
            args = dict(hsn=hsn, gf7=positional_gf7(hsn), plate=plate,
                        drive_hz=frequency, grid=17, max_mode=4,
                        source_refs=["https://example.org/source"])
            self.assertEqual(self.runtime.reasoning_context(**args), prepare_reasoning_context(**args))
        self.assertEqual(self.runtime.stats["physics_computations"], 1)
        self.assertEqual(self.runtime.stats["physics_hits"], 11)

    def test_physics_configuration_invalidates_reuse(self):
        for plate in (Plate(), Plate(thickness_m=0.002)):
            self.runtime.reasoning_context(hsn="H01.S01.N01", gf7="GF7.B01.M01.C01",
                plate=plate, drive_hz=mode_hz(plate, 1, 1), grid=17, max_mode=4)
        self.assertEqual(self.runtime.stats["physics_computations"], 2)

    def test_physics_return_is_copy_and_revocation_denies_warm_value(self):
        args = dict(hsn="H01.S01.N01", gf7="GF7.B01.M01.C01", plate=Plate(), drive_hz=53.31829, grid=17, max_mode=4)
        result = self.runtime.reasoning_context(**args)
        result["physical_model_output"]["status"] = "FORGED"
        self.assertNotEqual(self.runtime.reasoning_context(**args)["physical_model_output"]["status"], "FORGED")
        self.allowed = False
        with self.assertRaises(PermissionError):
            self.runtime.reasoning_context(**args)

    def test_reasoning_context_requires_trusted_memory_checkpoint(self):
        args = dict(hsn="H01.S01.N01", gf7="GF7.B01.M01.C01", plate=Plate(), drive_hz=53.31829, grid=17, max_mode=4, memory=self.memory)
        with self.assertRaisesRegex(ValueError, "CHECKPOINT_INVALID"):
            self.runtime.reasoning_context(**args)
        result = self.runtime.reasoning_context(**args, expected_tip="0" * 64, expected_count=0)
        self.assertEqual(result["synthetic_review_tip_sha256"], "0" * 64)
        self.memory.append(review())
        with self.assertRaisesRegex(ValueError, "CHECKPOINT_CHANGED"):
            self.runtime.reasoning_context(**args, expected_tip="0" * 64, expected_count=0)

    def test_return_denial_and_during_projection_memory_update(self):
        self.runtime.authorize = lambda scope, phase: phase != "RETURN"
        with self.assertRaises(PermissionError):
            self.runtime.verified_memory(self.memory, ["H01.S01.N01"], expected_tip="0" * 64, expected_count=0)
        called = []
        def mutate(scope, phase):
            if phase == "RETURN" and not called:
                called.append(1); self.memory.append(review())
            return True
        self.runtime.authorize = mutate
        with self.assertRaisesRegex(ValueError, "CHECKPOINT_CHANGED"):
            self.runtime.topic_views(self.db, self.memory, ["H01.S01.N01"], expected_tip="0" * 64, expected_count=0)

    def test_trace_bounded_no_source_content(self):
        traces = TraceBook(capacity=2)
        for _ in range(5):
            with traces.span("verified_memory"):
                pass
        report = traces.report()
        self.assertEqual((report["total_spans"], report["retained_spans"]), (5, 2))
        self.assertEqual(set(report["spans"][0]), {"stage", "status", "elapsed_ns"})
        with self.assertRaises(ValueError):
            with traces.span("arbitrary_personal_identifier"):
                pass

    def test_feed_revisions_reach_index_and_reverts_are_visible(self):
        url = "https://feeds.example/atom"
        raw = [json.dumps({"items": [{"id": "one", "title": title}]}).encode() for title in ("芯片制造", "材料研究", "芯片制造")]
        poller = FeedPoller(":memory:", allowed_hosts={"feeds.example"},
                            transport=lambda *_: Response(200, {}, raw.pop(0), url),
                            authorize=lambda *_: True, burst=4)
        try:
            first = self.runtime.refresh_public_feed(poller, url)
            self.assertEqual(first["indexed_documents"], 1)
            self.assertEqual(len(self.runtime.search_public("芯片")), 1)
            doc_id = self.runtime.search_public("芯片")[0]["id"]
            self.store.memo_put(self.scope, "derived", {"old": True})
            self.store.set_dependencies(self.scope, "derived", [doc_id])
            second = self.runtime.refresh_public_feed(poller, url)
            self.assertEqual(second["invalidated_keys"], 2)
            self.assertFalse(self.store.memo_get(self.scope, "derived").hit)
            self.assertEqual(self.runtime.search_public("芯片"), [])
            third = self.runtime.refresh_public_feed(poller, url)
            self.assertEqual(third["new_revisions"], 0)
            self.assertEqual(third["indexed_documents"], 1)
            self.assertEqual(len(self.runtime.search_public("芯片")), 1)
        finally:
            poller.close()

    def test_no_store_feed_does_not_enter_search(self):
        url = "https://feeds.example/atom"
        poller = FeedPoller(":memory:", allowed_hosts={"feeds.example"},
                            transport=lambda *_: Response(200, {"Cache-Control": "no-store"}, b'{"items":[{"id":"one","title":"test"}]}', url),
                            authorize=lambda *_: True)
        try:
            self.assertEqual(self.runtime.refresh_public_feed(poller, url)["indexed_documents"], 0)
            self.assertEqual(self.runtime.search_public("test"), [])
            self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM beast_objects").fetchone()[0], 0)
        finally:
            poller.close()


class CascadeTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_topology_warm_and_four_affected_jobs(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "synthetic.json"
            raw = json.dumps(synthetic(), sort_keys=True).encode(); path.write_bytes(raw)
            snapshot = SourceSnapshot(path, expected_sha=sha256(raw).hexdigest())
            compiler = CascadeCompiler(snapshot)
            scope = Scope(snapshot.registry_sha, "synthetic/v1", "synthetic-test", 1)
            with ArtifactStore() as store:
                runtime = AtlasBeastRuntime(scope, store, lambda *_: True)
                executor = AsyncExecutor(":memory:", compiler.handlers(), scope_key=scope.key)
                try:
                    first = await runtime.run_cascade(compiler, executor)
                    self.assertTrue(first.succeeded)
                    self.assertEqual(first.stats["executed"], 1885)
                    self.assertEqual(first.outputs["META145"]["node_count"], 1728)
                    second = await runtime.run_cascade(compiler, executor)
                    self.assertEqual(second.outputs, first.outputs)
                    self.assertEqual(second.stats["executed"], 0)
                    self.assertEqual(second.stats["cache_hits"], 1885)
                    changed = await runtime.run_cascade(compiler, executor,
                        {"H01.S01.N01": {"review_note": "synthetic supplemental computation"}})
                    self.assertEqual(changed.stats["executed"], 4)
                    self.assertEqual(changed.stats["cache_hits"], 1881)
                    self.assertNotEqual(changed.outputs["META145"], first.outputs["META145"])
                    self.assertEqual(compiler.nodes["H01.S01.N01"], snapshot.nodes["H01.S01.N01"])
                    compiler.nodes["H01.S01.N01"]["name"] = "mutated"
                    with self.assertRaisesRegex(ValueError, "SNAPSHOT_MUTATED"):
                        compiler.tasks()
                finally:
                    executor.close()


if __name__ == "__main__":
    unittest.main()
