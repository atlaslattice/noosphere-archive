"""Crash/restart delivery contracts across feed and document databases.

Synthetic source responses only. These are local integration tests, not hosted
authorization or live-provider evidence.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.glyph import REGISTRY_SHA
from src.beast20.feeds import FeedPoller, Response
from src.beast20.runtime import AtlasBeastRuntime
from src.beast20.storage import ArtifactStore, Scope


URL = "https://delivery.example/research.json"


def feed(text="alpha", item_id="article", **extra):
    return json.dumps({"items": [{"id": item_id, "title": "Research update",
                                  "content_text": text, **extra}]}).encode()


class DurableFeedDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.source_path = Path(self.temp.name) / "source.sqlite"
        self.destination_path = Path(self.temp.name) / "destination.sqlite"
        self.scope = Scope(REGISTRY_SHA, "Ariadne v0.7", "synthetic-delivery-review", 1)
        self.now = [1000.0]
        self.responses, self.requests = [], []
        self.store = ArtifactStore(str(self.destination_path))
        self.runtime = AtlasBeastRuntime(self.scope, self.store, lambda *_: True)
        self.poller = self.make_poller()

    def make_poller(self, burst=20):
        def transport(url, headers):
            self.requests.append((url, dict(headers)))
            return self.responses.pop(0)
        return FeedPoller(self.source_path, allowed_hosts={"delivery.example"},
                          transport=transport, authorize=lambda *_: True,
                          clock=lambda: self.now[0], burst=burst)

    def tearDown(self):
        self.poller.close()
        self.store.close()
        self.temp.cleanup()

    def response(self, text="alpha", status=200, headers=None, **extra):
        self.responses.append(Response(
            status, {"ETag": f'"{text}"', **(headers or {})},
            feed(text, **extra) if status == 200 else b"", URL))

    def pending(self, consumer=None, limit=2000):
        return self.poller.pending(self.scope.key, URL,
                                   consumer or self.runtime._feed_consumer, limit=limit)

    def test_upsert_failure_replays_after_not_modified_response(self):
        self.response()
        with patch.object(self.store, "upsert_document", side_effect=RuntimeError("synthetic write failure")):
            with self.assertRaises(RuntimeError):
                self.runtime.refresh_public_feed(self.poller, URL)
        self.assertEqual(len(self.pending()["items"]), 1)
        self.assertEqual(self.runtime.search_public("alpha"), [])
        self.response(status=304)
        receipt = self.runtime.refresh_public_feed(self.poller, URL)
        self.assertEqual(receipt["status"], "NOT_MODIFIED")
        self.assertEqual(receipt["indexed_documents"], 1)
        self.assertEqual(receipt["delivered_changes"], 1)
        self.assertEqual(len(self.runtime.search_public("alpha")), 1)
        self.assertEqual(self.pending()["items"], [])

    def test_reopened_source_and_destination_resume_same_consumer(self):
        consumer = self.runtime._feed_consumer
        self.response()
        with patch.object(self.store, "upsert_document", side_effect=RuntimeError("synthetic interrupted write")):
            with self.assertRaises(RuntimeError):
                self.runtime.refresh_public_feed(self.poller, URL)
        self.poller.close()
        self.store.close()
        self.store = ArtifactStore(str(self.destination_path))
        self.runtime = AtlasBeastRuntime(self.scope, self.store, lambda *_: True)
        self.poller = self.make_poller()
        self.assertEqual(self.runtime._feed_consumer, consumer)
        self.response(status=304)
        receipt = self.runtime.refresh_public_feed(self.poller, URL)
        self.assertEqual(receipt["delivered_changes"], 1)
        self.assertEqual(len(self.runtime.search_public("alpha")), 1)

    def test_new_destination_replays_history_despite_old_consumer_ack_and_304(self):
        self.response()
        self.runtime.refresh_public_feed(self.poller, URL)
        self.assertEqual(self.pending()["items"], [])
        with ArtifactStore(str(Path(self.temp.name) / "second-destination.sqlite")) as second:
            other = AtlasBeastRuntime(self.scope, second, lambda *_: True)
            self.assertNotEqual(other._feed_consumer, self.runtime._feed_consumer)
            self.response(status=304)
            receipt = other.refresh_public_feed(self.poller, URL)
            self.assertEqual(receipt["delivered_changes"], 1)
            self.assertEqual(len(other.search_public("alpha")), 1)

    def test_revert_events_leave_destination_at_latest_current_state(self):
        for text in ("alpha", "bravo", "alpha"):
            self.response(text)
            self.runtime.refresh_public_feed(self.poller, URL)
        self.assertEqual(len(self.runtime.search_public("alpha")), 1)
        self.assertEqual(self.runtime.search_public("bravo"), [])
        self.assertEqual(len(self.poller.revisions(self.scope.key, URL, "article")), 2)
        self.assertEqual(self.pending()["items"], [])

    def test_invalidation_failure_is_finished_when_upsert_is_already_committed(self):
        self.response()
        self.runtime.refresh_public_feed(self.poller, URL)
        doc_id = self.runtime.search_public("alpha")[0]["id"]
        self.store.memo_put(self.scope, "derived-answer", {"outdated": True})
        self.store.set_dependencies(self.scope, "derived-answer", [doc_id])
        self.response("bravo")
        with patch.object(self.store, "invalidate", side_effect=RuntimeError("synthetic invalidation failure")):
            with self.assertRaises(RuntimeError):
                self.runtime.refresh_public_feed(self.poller, URL)
        self.assertTrue(self.store.memo_get(self.scope, "derived-answer").hit)
        self.assertEqual(len(self.runtime.search_public("bravo")), 1)
        self.response("bravo", status=304)
        receipt = self.runtime.refresh_public_feed(self.poller, URL)
        self.assertEqual(receipt["indexed_documents"], 0)
        self.assertEqual(receipt["delivered_changes"], 1)
        self.assertFalse(self.store.memo_get(self.scope, "derived-answer").hit)
        self.assertEqual(self.pending()["items"], [])

    def test_fresh_response_replays_pending_without_network(self):
        self.response(headers={"Cache-Control": "max-age=60"})
        self.poller.poll(self.scope.key, URL)
        receipt = self.runtime.refresh_public_feed(self.poller, URL)
        self.assertEqual(receipt["status"], "CACHE_FRESH")
        self.assertFalse(receipt["network_request"])
        self.assertEqual(receipt["delivered_changes"], 1)
        self.assertEqual(len(self.requests), 1)

    def test_rate_limited_poll_still_finishes_already_fetched_delivery(self):
        self.poller.close()
        self.poller = self.make_poller(burst=1)
        self.response()
        self.poller.poll(self.scope.key, URL)
        receipt = self.runtime.refresh_public_feed(self.poller, URL)
        self.assertEqual(receipt["status"], "RATE_LIMITED")
        self.assertFalse(receipt["network_request"])
        self.assertEqual(receipt["delivered_changes"], 1)
        self.assertEqual(len(self.requests), 1)

    def test_no_store_purges_pending_content_and_does_not_index_transient_response(self):
        self.response()
        self.poller.poll(self.scope.key, URL)
        self.assertEqual(len(self.pending()["items"]), 1)
        self.response("bravo", headers={"Cache-Control": "no-store"})
        receipt = self.runtime.refresh_public_feed(self.poller, URL)
        self.assertEqual(receipt["status"], "NO_STORE")
        self.assertEqual(receipt["delivered_changes"], 0)
        self.assertEqual(self.pending()["items"], [])
        self.assertEqual(self.runtime.search_public("alpha bravo"), [])
        self.assertEqual(self.poller.db.execute("SELECT count(*) FROM feed_changes").fetchone()[0], 0)

    def test_bounded_delivery_ack_order_and_independent_consumer_cursors(self):
        raw = json.dumps({"items": [{"id": str(i), "content_text": f"item{i}"}
                                   for i in range(3)]}).encode()
        self.responses.append(Response(200, {}, raw, URL))
        self.poller.poll(self.scope.key, URL)
        first = self.pending("first-consumer", limit=1)
        self.assertEqual(len(first["items"]), 1)
        self.assertTrue(first["has_more"])
        full = self.pending("first-consumer")
        with self.assertRaises(ValueError):
            self.poller.ack(self.scope.key, URL, "first-consumer", full["items"][2]["sequence"])
        sequence = first["items"][0]["sequence"]
        self.poller.ack(self.scope.key, URL, "first-consumer", sequence)
        self.poller.ack(self.scope.key, URL, "first-consumer", sequence)
        self.assertEqual(len(self.pending("first-consumer")["items"]), 2)
        self.assertEqual(len(self.pending("second-consumer")["items"]), 3)

    def test_index_preserves_source_metadata_without_accepting_feed_authority_fields(self):
        self.response(canon_writes=True, authorization="HOST_AUTHORIZED", semantic_approved=True)
        receipt = self.runtime.refresh_public_feed(self.poller, URL)
        row = self.runtime.search_public("alpha")[0]
        original = self.poller.revisions(self.scope.key, URL, "article")[0]
        self.assertEqual(row["polarity"], "RELATED")
        self.assertEqual(row["metadata"], {
            "source_url": URL, "item_id": "article",
            "revision_sha256": original["revision_sha256"],
            "status": "PUBLIC_SOURCE_UNREVIEWED",
        })
        self.assertFalse(receipt["automatic_crosswalk_acceptance"])


if __name__ == "__main__":
    unittest.main()
