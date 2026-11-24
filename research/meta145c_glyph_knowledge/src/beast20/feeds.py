"""Conditional public feed refresh with durable, atomic source checkpoints.

Fresh implementation of HTTP cache-validator and token-bucket patterns;
see BEAST20_OPEN_SOURCE_PROVENANCE.md. The default transport performs no I/O.
Network use requires the explicitly constructed PublicHTTPTransport and a
bounded, exact host allowlist. Feed bytes remain evidence, never instructions.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
from email.utils import parsedate_to_datetime
import hashlib
import ipaddress
import json
import math
import re
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

MAX_BYTES = 2_000_000
MAX_ITEMS = 2000


def canonical_url(url: str) -> str:
    """Conservative URL identity: retain path/query spelling and ordering."""
    if type(url) is not str or len(url) > 4096 or any(ord(c) < 33 for c in url):
        raise ValueError("INVALID_PUBLIC_URL")
    p = urllib.parse.urlsplit(url)
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise ValueError("HTTPS_PUBLIC_URL_REQUIRED")
    host = p.hostname.encode("idna").decode("ascii").lower()
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        if "." not in host or host.endswith((".local", ".localhost", ".internal")):
            raise ValueError("PUBLIC_HOST_REQUIRED")
    else:
        if not ip.is_global:
            raise ValueError("PUBLIC_HOST_REQUIRED")
        if ip.version == 6:
            host = "[" + host + "]"
    port = p.port
    netloc = host if port in (None, 443) else f"{host}:{port}"
    return urllib.parse.urlunsplit(("https", netloc, p.path or "/", p.query, ""))


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      allow_nan=False, separators=(",", ":"))


def _unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def _reject_constant(value):
    raise ValueError("NONFINITE_JSON")


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict
    body: bytes
    url: str


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PublicHTTPTransport:
    """Small opt-in HTTPS GET transport; no redirect, credential, or paid API.

    Exact hosts must be selected by the caller. This is not a general untrusted
    URL proxy and is not suitable for accepting end-user host allowlists.
    """
    def __init__(self, allowed_hosts, timeout=15, max_bytes=MAX_BYTES):
        self.allowed_hosts = frozenset(allowed_hosts)
        if not self.allowed_hosts or len(self.allowed_hosts) > 32:
            raise ValueError("BOUNDED_HOST_ALLOWLIST_REQUIRED")
        if type(timeout) not in (int, float) or not 0 < timeout <= 60:
            raise ValueError("TIMEOUT_INVALID")
        if type(max_bytes) is not int or not 0 < max_bytes <= MAX_BYTES:
            raise ValueError("BYTE_LIMIT_INVALID")
        self.timeout, self.max_bytes = timeout, max_bytes
        self.opener = urllib.request.build_opener(_NoRedirect)

    def __call__(self, url, headers):
        url = canonical_url(url)
        if urllib.parse.urlsplit(url).hostname not in self.allowed_hosts:
            raise PermissionError("HOST_NOT_SELECTED")
        request = urllib.request.Request(url, method="GET", headers={
            "User-Agent": "Atlas-BEAST20/0.1 (bounded public research; no crawler)",
            "Accept": "application/atom+xml, application/rss+xml, application/feed+json, application/json",
            **headers,
        })
        try:
            response = self.opener.open(request, timeout=self.timeout)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            raw = response.read(self.max_bytes + 1)
            if len(raw) > self.max_bytes:
                raise ValueError("FEED_TOO_LARGE")
            return Response(response.code, dict(response.headers), raw, url)


def parse_feed(raw: bytes, source_url: str) -> list[dict]:
    """Bounded JSON Feed, RSS 2.0, or Atom parser retaining original text.

    No HTML rendering, external entities, tool directives, or source authority.
    Each revision is compared using exact logical fields, not normalized words.
    """
    if type(raw) is not bytes or len(raw) > MAX_BYTES:
        raise ValueError("FEED_BYTES_INVALID")
    source_url = canonical_url(source_url)
    text = raw.decode("utf-8-sig", errors="strict")
    items = []
    if text.lstrip().startswith(("{", "[")):
        data = json.loads(text, object_pairs_hook=_unique_pairs,
                          parse_constant=_reject_constant)
        rows = data.get("items") if type(data) is dict else data
        if type(rows) is not list or len(rows) > MAX_ITEMS:
            raise ValueError("FEED_ITEMS_INVALID")
        for row in rows:
            if type(row) is not dict:
                raise ValueError("FEED_ITEM_INVALID")
            items.append({"id": row.get("id"), "url": row.get("url"),
                          "title": row.get("title", ""),
                          "text": row.get("content_text", row.get("summary", "")),
                          "content_html": row.get("content_html", ""),
                          "published": row.get("date_published", ""),
                          "updated": row.get("date_modified", "")})
    else:
        if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
            raise ValueError("XML_DECLARATION_DENIED")
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise ValueError("INVALID_FEED_XML") from exc
        atom = "{http://www.w3.org/2005/Atom}"
        if root.tag == atom + "feed":
            rows = root.findall(atom + "entry")
            if len(rows) > MAX_ITEMS:
                raise ValueError("FEED_ITEMS_INVALID")
            for row in rows:
                link = next((link.get("href") for link in row.findall(atom + "link")
                             if link.get("rel", "alternate") == "alternate"), None)
                content = row.find(atom + "content")
                markup = ""
                content_text = row.findtext(atom + "content", "")
                if content is not None:
                    if content.get("type") == "xhtml":
                        markup = "".join(ET.tostring(child, encoding="unicode") for child in content)
                        content_text = "".join(content.itertext())
                    elif content.get("type") == "html":
                        markup = content.text or ""
                        content_text = row.findtext(atom + "summary", "")
                items.append({"id": row.findtext(atom + "id"), "url": link,
                              "title": row.findtext(atom + "title", ""),
                              "text": row.findtext(atom + "summary", content_text),
                              "content_html": markup,
                              "published": row.findtext(atom + "published", ""),
                              "updated": row.findtext(atom + "updated", "")})
        elif root.tag == "rss":
            rows = root.findall("./channel/item")
            if len(rows) > MAX_ITEMS:
                raise ValueError("FEED_ITEMS_INVALID")
            for row in rows:
                items.append({"id": row.findtext("guid"), "url": row.findtext("link"),
                              "title": row.findtext("title", ""),
                              "text": row.findtext("description", ""),
                              "content_html": "",
                              "published": row.findtext("pubDate", ""), "updated": ""})
        else:
            raise ValueError("UNSUPPORTED_FEED_FORMAT")
    cleaned = []
    for item in items:
        if item["url"] is not None:
            if type(item["url"]) is not str:
                raise ValueError("FEED_ITEM_URL_INVALID")
            item["url"] = canonical_url(urllib.parse.urljoin(source_url, item["url"]))
        if item["id"] is None:
            item["id"] = item["url"]
        if type(item["id"]) is not str or not 1 <= len(item["id"]) <= 4096:
            raise ValueError("FEED_ITEM_ID_REQUIRED")
        for key in ("title", "text", "content_html", "published", "updated"):
            if type(item[key]) is not str or len(item[key]) > 300_000:
                raise ValueError("FEED_ITEM_TEXT_INVALID")
        item["revision_sha256"] = _hash(_json(item).encode("utf-8"))
        cleaned.append(item)
    return cleaned


class FeedPoller:
    """E13–E16: conditional requests, revision dedupe, budgets, atomic cursors.

    Polls happen only on explicit calls. A host must supply an authorization
    callback; it is rechecked at READ and before both checkpoint write and
    RETURN. A local callback is a test seam, not proof of hosted authorization.
    """
    def __init__(self, path, *, allowed_hosts, transport, authorize,
                 clock=time.time, requests_per_second=0.5, burst=2):
        if not callable(transport) or not callable(authorize):
            raise ValueError("TRANSPORT_AND_AUTHORIZER_REQUIRED")
        if (type(requests_per_second) not in (int, float)
                or not math.isfinite(requests_per_second)
                or not 0 < requests_per_second <= 10
                or type(burst) is not int or not 1 <= burst <= 20):
            raise ValueError("BUDGET_INVALID")
        self.allowed_hosts = frozenset(allowed_hosts)
        if not self.allowed_hosts or len(self.allowed_hosts) > 32:
            raise ValueError("BOUNDED_HOST_ALLOWLIST_REQUIRED")
        self.transport, self.authorize, self.clock = transport, authorize, clock
        self.rate, self.burst = float(requests_per_second), burst
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS feed_sources(
          scope TEXT, url TEXT, generation INTEGER NOT NULL,
          etag TEXT, modified TEXT, body_digest TEXT, checked_at REAL,
          next_poll_at REAL NOT NULL DEFAULT 0,
          PRIMARY KEY(scope,url));
        CREATE TABLE IF NOT EXISTS feed_items(
          scope TEXT, source TEXT, item_id TEXT, revision TEXT,
          payload TEXT NOT NULL, PRIMARY KEY(scope,source,item_id,revision));
        CREATE TABLE IF NOT EXISTS feed_heads(
          scope TEXT, source TEXT, item_id TEXT, revision TEXT,
          PRIMARY KEY(scope,source,item_id));
        CREATE TABLE IF NOT EXISTS feed_budgets(
          origin TEXT PRIMARY KEY, tokens REAL, updated REAL, blocked_until REAL);
        CREATE TABLE IF NOT EXISTS feed_changes(
          sequence INTEGER PRIMARY KEY AUTOINCREMENT, scope TEXT NOT NULL,
          source TEXT NOT NULL, item_id TEXT NOT NULL, revision TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS feed_change_scope ON feed_changes(scope,source,sequence);
        CREATE TABLE IF NOT EXISTS feed_consumers(
          scope TEXT, source TEXT, consumer TEXT, acknowledged INTEGER NOT NULL,
          PRIMARY KEY(scope,source,consumer));
        """)
        if "next_poll_at" not in {row[1] for row in self.db.execute("PRAGMA table_info(feed_sources)")}:
            self.db.execute("ALTER TABLE feed_sources ADD COLUMN next_poll_at REAL NOT NULL DEFAULT 0")
            self.db.commit()
        # Upgrade previously stored heads to replayable events without erasing
        # history. New sources already append events in the checkpoint transaction.
        with self.db:
            self.db.execute("""INSERT INTO feed_changes(scope,source,item_id,revision)
                SELECT h.scope,h.source,h.item_id,h.revision FROM feed_heads h
                WHERE NOT EXISTS(SELECT 1 FROM feed_changes c WHERE c.scope=h.scope
                    AND c.source=h.source AND c.item_id=h.item_id)""")
        self.stats = {"requests": 0, "parsed": 0, "not_modified": 0,
                      "body_unchanged": 0, "new_revisions": 0, "duplicates": 0}

    def close(self):
        self.db.close()

    def _allow(self, scope_key, phase):
        if type(scope_key) is not str or not re.fullmatch(r"[0-9a-f]{64}", scope_key):
            raise ValueError("SCOPE_KEY_INVALID")
        if self.authorize(scope_key, phase) is not True:
            raise PermissionError("CURRENT_WORK_RIGHTS_REQUIRED")

    def _budget(self, origin, now):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute("SELECT tokens,updated,blocked_until FROM feed_budgets WHERE origin=?", (origin,)).fetchone()
            tokens, updated, blocked = row if row else (float(self.burst), now, 0)
            tokens = min(self.burst, tokens + max(0, now - updated) * self.rate)
            wait = max(0, blocked - now, (1 - tokens) / self.rate)
            if wait <= 0:
                self.db.execute("INSERT OR REPLACE INTO feed_budgets VALUES(?,?,?,?)",
                                (origin, tokens - 1, now, blocked))
            self.db.commit()
            return wait
        except BaseException:
            self.db.rollback()
            raise

    def _retry_after(self, value, now):
        try:
            seconds = float(value)
        except (TypeError, ValueError):
            try:
                date = parsedate_to_datetime(value)
                if date.tzinfo is None:
                    date = date.replace(tzinfo=timezone.utc)
                seconds = date.timestamp() - now
            except (TypeError, ValueError, OverflowError):
                seconds = 60.0
        return max(0.0, seconds) if math.isfinite(seconds) else 60.0

    def poll(self, scope_key, url):
        self._allow(scope_key, "READ")
        url = canonical_url(url)
        origin = urllib.parse.urlsplit(url).netloc
        if urllib.parse.urlsplit(url).hostname not in self.allowed_hosts:
            raise PermissionError("HOST_NOT_SELECTED")
        with self.lock:
            row = self.db.execute("SELECT generation,etag,modified,body_digest,next_poll_at FROM feed_sources WHERE scope=? AND url=?", (scope_key, url)).fetchone()
            generation, etag, modified, digest, next_poll = row if row else (0, None, None, None, 0)
            if next_poll > self.clock():
                self._allow(scope_key, "RETURN")
                return {"status": "CACHE_FRESH", "retry_after_seconds": next_poll - self.clock(),
                        "network_request": False, "items": []}
            wait = self._budget(origin, self.clock())
        if wait:
            self._allow(scope_key, "RETURN")
            return {"status": "RATE_LIMITED", "retry_after_seconds": wait,
                    "network_request": False, "items": []}
        headers = {}
        if etag:
            headers["If-None-Match"] = etag
        if modified:
            headers["If-Modified-Since"] = modified
        response = self.transport(url, headers)
        self.stats["requests"] += 1
        self._allow(scope_key, "RETURN")
        if not isinstance(response, Response) or canonical_url(response.url) != url:
            raise ValueError("RESPONSE_SOURCE_MISMATCH")
        if type(response.body) is not bytes or len(response.body) > MAX_BYTES:
            raise ValueError("FEED_BYTES_INVALID")
        headers = {str(k).lower(): str(v) for k, v in response.headers.items()}
        for key in ("etag", "last-modified"):
            if key in headers and (len(headers[key]) > 4096 or "\n" in headers[key] or "\r" in headers[key]):
                raise ValueError("RESPONSE_VALIDATOR_INVALID")
        now = self.clock()
        if response.status in (429, 503):
            retry = self._retry_after(headers.get("retry-after"), now)
            with self.lock, self.db:
                self.db.execute("UPDATE feed_budgets SET blocked_until=max(blocked_until,?) WHERE origin=?", (now + retry, origin))
            return {"status": "PROVIDER_BACKOFF", "retry_after_seconds": retry,
                    "network_request": True, "items": []}
        if response.status == 304:
            if digest is None:
                raise ValueError("NOT_MODIFIED_WITHOUT_CHECKPOINT")
            parsed = None
            new_digest = digest
            state = "NOT_MODIFIED"
        elif response.status == 200:
            new_digest = _hash(response.body)
            if new_digest == digest:
                parsed = None
                state = "BODY_UNCHANGED"
            else:
                parsed = parse_feed(response.body, url)
                self.stats["parsed"] += 1
                state = "UPDATED"
        else:
            return {"status": "HTTP_ERROR", "http_status": response.status,
                    "network_request": True, "items": []}
        cache_directives = {item.strip().lower() for item in headers.get("cache-control", "").split(",")}
        if "no-store" in cache_directives:
            # Honor provider storage policy, including previously held response
            # state. Source bytes are returned only to the authorized caller.
            self._allow(scope_key, "COMMIT")
            with self.lock, self.db:
                for table, column in (("feed_sources", "url"), ("feed_items", "source"), ("feed_heads", "source"), ("feed_changes", "source"), ("feed_consumers", "source")):
                    self.db.execute(f"DELETE FROM {table} WHERE scope=? AND {column}=?", (scope_key, url))
            self._allow(scope_key, "RETURN")
            return {"status": "NO_STORE", "items": parsed or [],
                    "network_request": True, "checkpoint_written": False,
                    "authority": "SOURCE_CONTENT_UNREVIEWED"}
        fresh_until = now
        if "no-cache" not in cache_directives:
            for directive in cache_directives:
                match = re.fullmatch(r'max-age="?(\d+)"?', directive)
                if match:
                    age = headers.get("age", "0")
                    elapsed = float(age) if re.fullmatch(r"\d+", age) else 0.0
                    fresh_until = max(fresh_until, now + max(0, float(match[1]) - elapsed))
        changed_items, duplicates, new_revisions = [], 0, 0
        with self.lock:
            self._allow(scope_key, "COMMIT")
            self.db.execute("BEGIN IMMEDIATE")
            try:
                current = self.db.execute("SELECT generation FROM feed_sources WHERE scope=? AND url=?", (scope_key, url)).fetchone()
                if (current[0] if current else 0) != generation:
                    raise ValueError("STALE_FEED_CHECKPOINT")
                for item in parsed or []:
                    payload = _json(item)
                    prior_head = self.db.execute("SELECT revision FROM feed_heads WHERE scope=? AND source=? AND item_id=?", (scope_key, url, item["id"])).fetchone()
                    cursor = self.db.execute("INSERT OR IGNORE INTO feed_items VALUES(?,?,?,?,?)",
                                             (scope_key, url, item["id"], item["revision_sha256"], payload))
                    if cursor.rowcount:
                        new_revisions += 1
                    else:
                        duplicates += 1
                    if prior_head is None or prior_head[0] != item["revision_sha256"]:
                        changed_items.append(item)
                        self.db.execute("INSERT INTO feed_changes(scope,source,item_id,revision) VALUES(?,?,?,?)",
                                        (scope_key, url, item["id"], item["revision_sha256"]))
                    self.db.execute("INSERT OR REPLACE INTO feed_heads VALUES(?,?,?,?)",
                                    (scope_key, url, item["id"], item["revision_sha256"]))
                # A 200 response can remove an old validator. A 304 preserves
                # the current validator when no replacement header is supplied.
                new_etag = headers.get("etag", etag if response.status == 304 else None)
                new_modified = headers.get("last-modified", modified if response.status == 304 else None)
                self.db.execute("INSERT OR REPLACE INTO feed_sources VALUES(?,?,?,?,?,?,?,?)",
                                (scope_key, url, generation + 1, new_etag, new_modified, new_digest, now, fresh_until))
                self._allow(scope_key, "RETURN")
                self.db.commit()
            except BaseException:
                self.db.rollback()
                raise
        self.stats["new_revisions"] += new_revisions
        self.stats["duplicates"] += duplicates
        if state == "NOT_MODIFIED":
            self.stats["not_modified"] += 1
        if state == "BODY_UNCHANGED":
            self.stats["body_unchanged"] += 1
        return {"status": state, "generation": generation + 1,
                "body_sha256": new_digest, "new_revisions": new_revisions,
                "changed_heads": len(changed_items),
                "duplicates": duplicates, "items": changed_items,
                "network_request": True, "source_url": url,
                "authority": "SOURCE_CONTENT_UNREVIEWED", "canon_effect": "NONE"}

    @staticmethod
    def _verified_item(payload, expected, item_id):
        if type(payload) is not str:
            raise ValueError("FEED_REVISION_MISSING")
        item = json.loads(payload, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)
        if type(item) is not dict:
            raise ValueError("FEED_REVISION_INTEGRITY_FAILURE")
        recorded = item.get("revision_sha256")
        logical = {k: v for k, v in item.items() if k != "revision_sha256"}
        if (recorded != expected or item.get("id") != item_id
                or _hash(_json(logical).encode("utf-8")) != expected):
            raise ValueError("FEED_REVISION_INTEGRITY_FAILURE")
        return item

    def pending(self, scope_key, url, consumer, limit=2000):
        """Replayable ordered delivery to a named local index, separate from fetch."""
        self._allow(scope_key, "READ")
        if type(consumer) is not str or not re.fullmatch(r"[A-Za-z0-9:._-]{1,160}", consumer):
            raise ValueError("CONSUMER_INVALID")
        if type(limit) is not int or not 1 <= limit <= 2000:
            raise ValueError("DELIVERY_LIMIT_INVALID")
        url = canonical_url(url)
        with self.lock:
            row = self.db.execute("SELECT acknowledged FROM feed_consumers WHERE scope=? AND source=? AND consumer=?", (scope_key, url, consumer)).fetchone()
            after = row[0] if row else 0
            rows = self.db.execute("""SELECT c.sequence,c.item_id,c.revision,i.payload
                 FROM feed_changes c LEFT JOIN feed_items i
                 ON i.scope=c.scope AND i.source=c.source AND i.item_id=c.item_id AND i.revision=c.revision
                 WHERE c.scope=? AND c.source=? AND c.sequence>? ORDER BY c.sequence LIMIT ?""",
                 (scope_key, url, after, limit + 1)).fetchall()
            result = {"items": [{"sequence": seq, "item": self._verified_item(payload, revision, item_id)}
                                for seq, item_id, revision, payload in rows[:limit]],
                      "has_more": len(rows) > limit}
        self._allow(scope_key, "RETURN")
        return result

    def ack(self, scope_key, url, consumer, sequence):
        """Advance one contiguous consumer delivery after destination commit."""
        self._allow(scope_key, "COMMIT")
        if (type(consumer) is not str or not re.fullmatch(r"[A-Za-z0-9:._-]{1,160}", consumer)
                or type(sequence) is not int or sequence < 1):
            raise ValueError("DELIVERY_ACK_INVALID")
        url = canonical_url(url)
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                row = self.db.execute("SELECT acknowledged FROM feed_consumers WHERE scope=? AND source=? AND consumer=?", (scope_key, url, consumer)).fetchone()
                after = row[0] if row else 0
                if sequence > after:
                    next_row = self.db.execute("SELECT MIN(sequence) FROM feed_changes WHERE scope=? AND source=? AND sequence>?", (scope_key, url, after)).fetchone()
                    if next_row[0] != sequence:
                        raise ValueError("DELIVERY_ACK_OUT_OF_ORDER")
                    self.db.execute("INSERT OR REPLACE INTO feed_consumers VALUES(?,?,?,?)", (scope_key, url, consumer, sequence))
                self._allow(scope_key, "RETURN")
                self.db.commit()
            except BaseException:
                self.db.rollback()
                raise

    def revisions(self, scope_key, url, item_id):
        self._allow(scope_key, "READ")
        with self.lock:
            result = []
            for payload, expected in self.db.execute(
                    "SELECT payload,revision FROM feed_items WHERE scope=? AND source=? AND item_id=? ORDER BY rowid",
                    (scope_key, canonical_url(url), item_id)):
                result.append(self._verified_item(payload, expected, item_id))
        self._allow(scope_key, "RETURN")
        return result
