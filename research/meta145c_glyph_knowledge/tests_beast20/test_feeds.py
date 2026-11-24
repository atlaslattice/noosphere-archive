import json
import tempfile
import unittest
from pathlib import Path

from src.beast20.feeds import FeedPoller, Response, canonical_url, parse_feed

URL = "https://feeds.example/research.atom"
SCOPE = "a" * 64


def body(title="芯片制造", item_id="entry-1"):
    return json.dumps({"items": [{"id": item_id, "url": "https://papers.example/item",
                                "title": title, "content_text": "供应链材料 research"}]},
                      ensure_ascii=False).encode()


class FeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = [1000.0]
        self.requests = []
        self.responses = []
        self.allowed = [True]

        def transport(url, headers):
            self.requests.append((url, dict(headers)))
            return self.responses.pop(0)

        self.poller = FeedPoller(str(Path(self.temp.name) / "feed.sqlite"),
                                 allowed_hosts={"feeds.example"}, transport=transport,
                                 authorize=lambda scope, phase: self.allowed[0],
                                 clock=lambda: self.now[0], burst=2)

    def tearDown(self):
        self.poller.close()
        self.temp.cleanup()

    def response(self, raw=None, status=200, headers=None):
        self.responses.append(Response(status, headers or {}, body() if raw is None else raw, URL))

    def test_conditional_304_skips_parse(self):
        self.response(headers={"ETag": '"v1"', "Last-Modified": "Mon, 23 Nov 2026 00:00:00 GMT"})
        first = self.poller.poll(SCOPE, URL)
        self.response(b"", 304)
        second = self.poller.poll(SCOPE, URL)
        self.assertEqual(first["new_revisions"], 1)
        self.assertEqual(second["status"], "NOT_MODIFIED")
        self.assertEqual(self.requests[1][1]["If-None-Match"], '"v1"')
        self.assertEqual(self.poller.stats["parsed"], 1)

    def test_same_bytes_skip_parser_without_validator(self):
        self.response()
        self.poller.poll(SCOPE, URL)
        self.response()
        result = self.poller.poll(SCOPE, URL)
        self.assertEqual(result["status"], "BODY_UNCHANGED")
        self.assertEqual(self.poller.stats["parsed"], 1)

    def test_restart_revision_history_and_changed_title(self):
        self.response()
        first = self.poller.poll(SCOPE, URL)
        self.response(body("新型芯片制造"))
        second = self.poller.poll(SCOPE, URL)
        self.assertNotEqual(first["body_sha256"], second["body_sha256"])
        self.assertEqual(len(self.poller.revisions(SCOPE, URL, "entry-1")), 2)
        self.assertEqual(self.poller.revisions(SCOPE, URL, "entry-1")[0]["title"], "芯片制造")
        self.poller.close()
        self.poller = FeedPoller(str(Path(self.temp.name) / "feed.sqlite"),
                                 allowed_hosts={"feeds.example"}, transport=lambda *_: None,
                                 authorize=lambda *_: True, clock=lambda: self.now[0])
        self.assertEqual(len(self.poller.revisions(SCOPE, URL, "entry-1")), 2)

    def test_equivalent_json_dedupes_logical_item(self):
        self.response()
        self.poller.poll(SCOPE, URL)
        self.response(json.dumps(json.loads(body()), indent=2).encode())
        result = self.poller.poll(SCOPE, URL)
        self.assertEqual((result["new_revisions"], result["duplicates"]), (0, 1))

    def test_rate_limit_no_transport(self):
        for _ in range(2):
            self.response()
            self.poller.poll(SCOPE, URL)
        result = self.poller.poll(SCOPE, URL)
        self.assertEqual(result["status"], "RATE_LIMITED")
        self.assertEqual(len(self.requests), 2)
        self.now[0] += 2
        self.response()
        self.assertEqual(self.poller.poll(SCOPE, URL)["status"], "BODY_UNCHANGED")

    def test_retry_after_persists_provider_backoff(self):
        self.response(b"", 429, {"Retry-After": "30"})
        self.assertEqual(self.poller.poll(SCOPE, URL)["retry_after_seconds"], 30)
        self.assertEqual(self.poller.poll(SCOPE, URL)["status"], "RATE_LIMITED")
        self.now[0] += 30
        self.response()
        self.assertEqual(self.poller.poll(SCOPE, URL)["status"], "UPDATED")

    def test_bad_parse_does_not_advance_checkpoint(self):
        self.response(b"<!DOCTYPE feed><feed/>", headers={"ETag": '"bad"'})
        with self.assertRaises(ValueError):
            self.poller.poll(SCOPE, URL)
        self.assertEqual(self.poller.db.execute("select count(*) from feed_sources").fetchone()[0], 0)

    def test_unsolicited_304_rejected(self):
        self.response(b"", 304)
        with self.assertRaisesRegex(ValueError, "WITHOUT_CHECKPOINT"):
            self.poller.poll(SCOPE, URL)

    def test_access_revoked_during_transport_leaks_no_items_or_checkpoint(self):
        def revoked(url, headers):
            self.allowed[0] = False
            return Response(200, {}, body(), url)
        self.poller.transport = revoked
        with self.assertRaises(PermissionError):
            self.poller.poll(SCOPE, URL)
        self.assertEqual(self.poller.db.execute("select count(*) from feed_items").fetchone()[0], 0)

    def test_epoch_isolation_and_current_read_denied(self):
        self.response()
        self.poller.poll(SCOPE, URL)
        self.assertEqual(self.poller.revisions("b" * 64, URL, "entry-1"), [])
        self.allowed[0] = False
        with self.assertRaises(PermissionError):
            self.poller.revisions(SCOPE, URL, "entry-1")

    def test_stale_concurrent_fetch_cannot_overwrite_newer_checkpoint(self):
        def concurrent(url, headers):
            with self.poller.db:
                self.poller.db.execute("insert into feed_sources values(?,?,?,?,?,?,?,?)", (SCOPE, URL, 1, None, None, "b" * 64, 1000, 0))
            return Response(200, {}, body(), url)
        self.poller.transport = concurrent
        with self.assertRaisesRegex(ValueError, "STALE_FEED_CHECKPOINT"):
            self.poller.poll(SCOPE, URL)
        self.assertEqual(self.poller.db.execute("select count(*) from feed_items").fetchone()[0], 0)

    def test_unselected_host_and_redirect_response_rejected(self):
        with self.assertRaises(PermissionError):
            self.poller.poll(SCOPE, "https://other.example/feed")
        self.responses.append(Response(200, {}, body(), "https://other.example/feed"))
        with self.assertRaisesRegex(ValueError, "SOURCE_MISMATCH"):
            self.poller.poll(SCOPE, URL)

    def test_validator_header_injection_rejected(self):
        self.response(headers={"ETag": "ok\r\nInjected: yes"})
        with self.assertRaisesRegex(ValueError, "VALIDATOR_INVALID"):
            self.poller.poll(SCOPE, URL)

    def test_atom_rss_and_relative_links(self):
        atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>one</id><title>A</title><link href="/one"/><summary>B</summary></entry></feed>'
        rss = b'<rss><channel><item><guid>one</guid><link>https://feeds.example/one</link><title>A</title><description>B</description></item></channel></rss>'
        self.assertEqual(parse_feed(atom, URL), parse_feed(rss, URL))

    def test_url_normalization_conservative(self):
        self.assertEqual(canonical_url("https://EXAMPLE.com:443/a?b=2&a=1#part"), "https://example.com/a?b=2&a=1")
        for url in ("http://example.com", "https://user:password@example.com", "https://127.0.0.1", "https://localhost/", "https://[::1]/"):
            with self.assertRaises(ValueError):
                canonical_url(url)

    def test_ambiguous_json_and_nonbytes_rejected(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_JSON_KEY"):
            parse_feed(b'{"items": [], "items": []}', URL)
        with self.assertRaises(ValueError):
            parse_feed("not bytes", URL)


if __name__ == "__main__":
    unittest.main()
