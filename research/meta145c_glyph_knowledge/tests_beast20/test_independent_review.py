"""Independent regressions for observed feed-state and format failures.

These cases use synthetic local source responses. They perform no networking
and do not count as hosted provider or authorization evidence.
"""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import threading
import unittest

from src.beast20.feeds import FeedPoller, Response, parse_feed


URL = "https://review.example/feed"
SCOPE = "c" * 64


def json_item(text):
    return json.dumps({"items": [{"id": "reversible-item", "content_text": text}]}).encode()


def atom_xhtml(text):
    return (
        '<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>same-item</id>'
        '<content type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml">'
        f'<p>{text}</p></div></content></entry></feed>'
    ).encode()


class IndependentFeedReview(unittest.TestCase):
    def test_reverting_to_archived_revision_emits_current_head_change(self):
        responses = iter(Response(200, {}, json_item(text), URL)
                         for text in ("original", "revised", "original"))
        with tempfile.TemporaryDirectory() as temp:
            poller = FeedPoller(
                Path(temp) / "review.sqlite", allowed_hosts={"review.example"},
                transport=lambda *_: next(responses), authorize=lambda *_: True,
                clock=lambda: 1000.0, burst=20)
            try:
                first = poller.poll(SCOPE, URL)
                second = poller.poll(SCOPE, URL)
                reverted = poller.poll(SCOPE, URL)
                self.assertEqual(first["new_revisions"], 1)
                self.assertEqual(second["new_revisions"], 1)
                self.assertEqual(reverted["new_revisions"], 0)
                self.assertEqual(reverted["changed_heads"], 1)
                self.assertEqual([item["text"] for item in reverted["items"]], ["original"])
                self.assertEqual(len(poller.revisions(SCOPE, URL, "reversible-item")), 2)
            finally:
                poller.close()

    def test_html_only_json_feed_retains_inert_original_markup(self):
        first_markup = '<p lang="zh">供应链 <strong>制造</strong></p>'
        second_markup = '<p lang="zh">供应链 <strong>更新</strong></p>'

        def item(markup):
            raw = json.dumps({"items": [{"id": "html-only", "content_html": markup}]},
                             ensure_ascii=False).encode()
            return parse_feed(raw, URL)[0]

        first, second = item(first_markup), item(second_markup)
        self.assertEqual(first["content_html"], first_markup)
        self.assertEqual(second["content_html"], second_markup)
        self.assertNotEqual(first["revision_sha256"], second["revision_sha256"])

    def test_atom_xhtml_retains_markup_and_distinct_content_revisions(self):
        first = parse_feed(atom_xhtml("Original content"), URL)[0]
        second = parse_feed(atom_xhtml("Changed content"), URL)[0]
        first_markup = first.get("content_xhtml") or first.get("content_html")
        second_markup = second.get("content_xhtml") or second.get("content_html")
        self.assertIsInstance(first_markup, str)
        self.assertIsInstance(second_markup, str)
        self.assertIn("Original content", first_markup)
        self.assertIn("Changed content", second_markup)
        self.assertIn("<", first_markup)
        self.assertNotEqual(first["revision_sha256"], second["revision_sha256"])

    def test_html_change_is_not_hidden_by_unchanged_text_alternative(self):
        first = {"id": "alternatives", "content_text": "Same text", "content_html": "<p>First</p>"}
        second = {**first, "content_html": "<p>Second</p>"}
        left = parse_feed(json.dumps({"items": [first]}).encode(), URL)[0]
        right = parse_feed(json.dumps({"items": [second]}).encode(), URL)[0]
        self.assertEqual(left["text"], right["text"])
        self.assertNotEqual(left["revision_sha256"], right["revision_sha256"])

    def test_archival_read_rejects_payload_that_disagrees_with_revision_digest(self):
        with tempfile.TemporaryDirectory() as temp:
            poller = FeedPoller(
                Path(temp) / "review.sqlite", allowed_hosts={"review.example"},
                transport=lambda *_: Response(200, {}, json_item("original"), URL),
                authorize=lambda *_: True, clock=lambda: 1000.0, burst=20)
            try:
                poller.poll(SCOPE, URL)
                original = poller.db.execute("SELECT payload FROM feed_items").fetchone()[0]
                altered = json.loads(original)
                altered["text"] = "tampered despite the unchanged original digest"
                with poller.db:
                    poller.db.execute("UPDATE feed_items SET payload=?", (json.dumps(altered),))
                with self.assertRaises(ValueError):
                    poller.revisions(SCOPE, URL, "reversible-item")
            finally:
                poller.close()

    def test_long_retry_after_is_not_shortened_into_an_early_provider_request(self):
        now, requested = [1000.0], []

        def transport(url, _headers):
            requested.append(url)
            if len(requested) == 1:
                return Response(429, {"Retry-After": "172800"}, b"", url)
            return Response(200, {}, json_item("available again"), url)

        with tempfile.TemporaryDirectory() as temp:
            poller = FeedPoller(
                Path(temp) / "review.sqlite", allowed_hosts={"review.example"},
                transport=transport, authorize=lambda *_: True,
                clock=lambda: now[0], burst=20)
            try:
                backoff = poller.poll(SCOPE, URL)
                self.assertGreaterEqual(backoff["retry_after_seconds"], 172800)
                now[0] += 86401
                still_waiting = poller.poll(SCOPE, URL)
                self.assertFalse(still_waiting["network_request"])
                self.assertEqual(len(requested), 1)
                now[0] = 1000.0 + 172800
                self.assertTrue(poller.poll(SCOPE, URL)["network_request"])
                self.assertEqual(len(requested), 2)
            finally:
                poller.close()

    def test_fresh_max_age_avoids_network_until_expiry(self):
        now, requested = [1000.0], []

        def transport(url, _headers):
            requested.append(url)
            return Response(200, {"Cache-Control": "max-age=60"}, json_item("fresh"), url)

        with tempfile.TemporaryDirectory() as temp:
            poller = FeedPoller(
                Path(temp) / "review.sqlite", allowed_hosts={"review.example"},
                transport=transport, authorize=lambda *_: True,
                clock=lambda: now[0], burst=20)
            try:
                poller.poll(SCOPE, URL)
                now[0] += 1
                fresh = poller.poll(SCOPE, URL)
                self.assertFalse(fresh["network_request"])
                self.assertEqual(len(requested), 1)
                now[0] = 1060.0
                self.assertTrue(poller.poll(SCOPE, URL)["network_request"])
                self.assertEqual(len(requested), 2)
            finally:
                poller.close()

    def test_no_store_response_does_not_persist_content_or_source_checkpoint(self):
        with tempfile.TemporaryDirectory() as temp:
            poller = FeedPoller(
                Path(temp) / "review.sqlite", allowed_hosts={"review.example"},
                transport=lambda *_: Response(
                    200, {"Cache-Control": "no-store", "ETag": '"transient"'},
                    json_item("ephemeral source response"), URL),
                authorize=lambda *_: True, clock=lambda: 1000.0, burst=20)
            try:
                poller.poll(SCOPE, URL)
                for table in ("feed_items", "feed_heads", "feed_sources"):
                    self.assertEqual(poller.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0], 0)
            finally:
                poller.close()

    def test_concurrent_instances_share_one_origin_budget(self):
        barrier = threading.Barrier(4)
        requested = []

        def transport(url, _headers):
            requested.append(url)
            return Response(200, {}, b'{"items": []}', url)

        with tempfile.TemporaryDirectory() as temp:
            pollers = [FeedPoller(
                Path(temp) / "shared.sqlite", allowed_hosts={"review.example"},
                transport=transport, authorize=lambda *_: True,
                clock=lambda: 1000.0, burst=1) for _ in range(4)]
            try:
                def poll(index):
                    barrier.wait(timeout=5)
                    return pollers[index].poll(SCOPE, f"{URL}/{index}")

                with ThreadPoolExecutor(max_workers=4) as pool:
                    results = list(pool.map(poll, range(4)))
                self.assertEqual(len(requested), 1)
                self.assertEqual(sum(item["network_request"] for item in results), 1)
            finally:
                for poller in pollers:
                    poller.close()


if __name__ == "__main__":
    unittest.main()
