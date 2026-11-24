"""Scoped reusable Work computation, with exact-byte provenance and search.

Fresh stdlib implementation of content addressing (Git-style), bounded memo
reuse (LRU/TTL), dependency invalidation and reciprocal-rank fusion. No source
code is copied from those projects. This is an owner-local data component, not
an authentication system: a Scope never proves permission. Its host must check
current rights before reading and again before returning any result.

The raw object bytes and their digests remain independent of Unicode-normalized
search terms. SUPPORTS and CHALLENGES remain separate records and result lanes.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import math
import re
import sqlite3
import threading
import time
from typing import Any, Callable, Iterable
import unicodedata


_HEX = re.compile(r"[0-9a-f]{64}\Z")
_WORDS = re.compile(r"[^\W_]+", re.UNICODE)
_POLARITIES = frozenset({"SUPPORTS", "CHALLENGES", "RELATED", "REQUIRES"})
_MAX_BYTES = 8 * 1024 * 1024


def _text(value: Any, label: str, maximum: int = 512) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        raise ValueError(f"{label}_INVALID")
    return value


def _plain(value: Any, depth: int = 0) -> None:
    """Reject custom objects before JSON encoding can call their hooks."""
    if depth > 32:
        raise ValueError("JSON_DEPTH_EXCEEDED")
    kind = type(value)
    if value is None or kind in (str, bool, int):
        return
    if kind is float and math.isfinite(value):
        return
    if kind in (list, tuple):
        for item in value:
            _plain(item, depth + 1)
        return
    if kind is dict and all(type(key) is str for key in value):
        for item in value.values():
            _plain(item, depth + 1)
        return
    raise ValueError("JSON_PRIMITIVES_REQUIRED")


def canonical_bytes(value: Any) -> bytes:
    """Canonical for this Python/JSON contract, not an RFC 8785 claim."""
    _plain(value)
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(raw) > _MAX_BYTES:
        raise ValueError("JSON_TOO_LARGE")
    return raw


def _scope_values(source_digest, edition, principal, rights_epoch, mode):
    """Validate current scalar values before any memoized identity lookup."""
    if type(source_digest) is not str or not _HEX.fullmatch(source_digest):
        raise ValueError("SOURCE_DIGEST_INVALID")
    _text(edition, "EDITION")
    _text(principal, "PRINCIPAL")
    if not ((type(rights_epoch) is int and rights_epoch >= 0)
            or (type(rights_epoch) is str and 0 < len(rights_epoch) <= 512)):
        raise ValueError("RIGHTS_EPOCH_INVALID")
    if type(mode) is not str or mode != "WORK":
        raise ValueError("PRIVATE_MODE_DENIED")
    return source_digest, edition, principal, rights_epoch, mode


@lru_cache(maxsize=256, typed=True)
def _scope_digest(source_digest, edition, principal, rights_epoch, mode):
    # Only already-validated primitive values enter this bounded cache. Its
    # key contains every scope field, so mutating even a frozen Scope cannot
    # reuse an earlier identity. This caches hashing, never authorization or
    # source/object bytes; payload digests are still checked on every read.
    return hashlib.sha256(canonical_bytes({
        "contract": "atlas.beast20.scope/v1", "source_digest": source_digest,
        "edition": edition, "principal": principal,
        "rights_epoch": rights_epoch, "mode": mode,
    })).hexdigest()


@dataclass(frozen=True)
class Scope:
    source_digest: str
    edition: str
    principal: str
    rights_epoch: str | int
    mode: str = "WORK"

    def __post_init__(self) -> None:
        _scope_values(self.source_digest, self.edition, self.principal,
                      self.rights_epoch, self.mode)

    @property
    def key(self) -> str:
        values = _scope_values(self.source_digest, self.edition, self.principal,
                               self.rights_epoch, self.mode)
        return _scope_digest(*values)


def _scope_key(scope: Scope) -> str:
    if type(scope) is not Scope:
        raise ValueError("EXACT_SCOPE_REQUIRED")
    # key validates the current fields even if object.__setattr__ was used.
    return scope.key


def semantic_key(scope: Scope, algorithm: str, version: str,
                 config: Any, inputs: Any = None) -> str:
    """Exact configuration + code version + source/scope identity for reuse."""
    return hashlib.sha256(canonical_bytes({
        "contract": "atlas.beast20.memo-key/v1", "scope": _scope_key(scope),
        "algorithm": _text(algorithm, "ALGORITHM"),
        "version": _text(version, "VERSION"), "config": config, "inputs": inputs,
    })).hexdigest()


class _Negative:
    def __repr__(self) -> str:
        return "NEGATIVE"


NEGATIVE = _Negative()


@dataclass(frozen=True)
class CacheLookup:
    hit: bool
    value: Any = None
    negative: bool = False


class IntegrityError(ValueError):
    """Stored exact bytes no longer agree with their expected digest."""


def _cjk(char: str) -> bool:
    code = ord(char)
    return (0x3400 <= code <= 0x9FFF or 0xF900 <= code <= 0xFAFF
            or 0x20000 <= code <= 0x323AF or 0x3040 <= code <= 0x30FF
            or 0xAC00 <= code <= 0xD7AF)


def search_terms(text: str) -> frozenset[str]:
    """NFKC/casefold words, plus CJK unigrams and adjacent bigrams.

    This is a lexical index, not segmentation, translation or semantic proof.
    Unigrams deliberately support one/two-character queries without FTS5's
    three-character trigram minimum. Exact original text is stored separately.
    """
    if type(text) is not str or len(text.encode("utf-8")) > _MAX_BYTES:
        raise ValueError("SEARCH_TEXT_INVALID")
    result: set[str] = set()
    for word in _WORDS.findall(unicodedata.normalize("NFKC", text).casefold()):
        latin: list[str] = []
        cjk_run: list[str] = []

        def flush_latin() -> None:
            if latin:
                result.add("w:" + "".join(latin)); latin.clear()

        def flush_cjk() -> None:
            if cjk_run:
                result.update("c:" + ch for ch in cjk_run)
                result.update("b:" + a + b for a, b in zip(cjk_run, cjk_run[1:]))
                cjk_run.clear()

        for char in word:
            if _cjk(char):
                flush_latin(); cjk_run.append(char)
            else:
                flush_cjk(); latin.append(char)
        flush_latin(); flush_cjk()
    return frozenset(result)


def rrf(rankings: Iterable[Iterable[dict]], k: int = 60, limit: int = 20) -> list[dict]:
    """Fuse ordered result lists by reciprocal rank, retaining evidence polarity.

    Duplicate appearances in one list count once. Payload disagreement for the
    same (id, polarity) is rejected instead of quietly selecting one source.
    Scores rank candidates; they are not truth probabilities or authority.
    """
    if type(k) is not int or k < 1 or type(limit) is not int or not 1 <= limit <= 10000:
        raise ValueError("RRF_CONFIGURATION_INVALID")
    scores: dict[tuple[str, str], float] = defaultdict(float)
    records: dict[tuple[str, str], dict] = {}
    fingerprints: dict[tuple[str, str], bytes] = {}
    for lane in rankings:
        seen: set[tuple[str, str]] = set()
        rank = 0
        for row in lane:
            if type(row) is not dict:
                raise ValueError("RRF_RECORD_INVALID")
            identity = (_text(row.get("id"), "DOCUMENT_ID"), row.get("polarity"))
            if type(identity[1]) is not str or identity[1] not in _POLARITIES:
                raise ValueError("EVIDENCE_POLARITY_INVALID")
            payload = {name: value for name, value in row.items()
                       if name not in ("score", "rrf_score")}
            raw = canonical_bytes(payload)
            if identity in fingerprints and fingerprints[identity] != raw:
                raise ValueError("RRF_SOURCE_CONFLICT")
            fingerprints[identity] = raw
            records[identity] = json.loads(raw)
            if identity in seen:
                continue
            seen.add(identity); rank += 1
            scores[identity] += 1.0 / (k + rank)
    ordered = sorted(scores, key=lambda key: (-scores[key], key[0], key[1]))[:limit]
    return [{**records[key], "rrf_score": scores[key]} for key in ordered]


class ArtifactStore:
    """One serialized SQLite connection; persistent bytes, bounded derived memo.

    Raw source objects are deliberately retained. Derived JSON lives directly
    in the bounded memo rows, so eviction does not leave orphan CAS payloads.
    The cache is entry-bounded (8 MiB maximum per entry); SQLite can retain
    reusable free pages after deletion, rather than immediately shrink its file.

    No network, source import, model call or authorization is performed. The
    default SQLite journal is retained: this component adds no multiwriter WAL
    or background checkpoint process. Call close() when finished.
    """

    def __init__(self, path: str = ":memory:", max_memo_entries: int = 256,
                 clock: Callable[[], float] = time.time):
        if type(max_memo_entries) is not int or not 1 <= max_memo_entries <= 1000000:
            raise ValueError("MEMO_CAPACITY_INVALID")
        self.max_memo_entries = max_memo_entries
        self.clock = clock
        self._lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS beast_objects(
            scope TEXT NOT NULL, digest TEXT NOT NULL, body BLOB NOT NULL,
            PRIMARY KEY(scope,digest));
        CREATE TABLE IF NOT EXISTS beast_counter(id INTEGER PRIMARY KEY, value INTEGER NOT NULL);
        INSERT OR IGNORE INTO beast_counter VALUES(1,0);
        CREATE TABLE IF NOT EXISTS beast_memo(
            scope TEXT NOT NULL, key TEXT NOT NULL, digest TEXT, negative INTEGER NOT NULL,
            expires REAL NOT NULL, accessed INTEGER NOT NULL, body BLOB,
            PRIMARY KEY(scope,key));
        CREATE INDEX IF NOT EXISTS beast_memo_lru ON beast_memo(accessed);
        CREATE INDEX IF NOT EXISTS beast_memo_expiry ON beast_memo(expires);
        CREATE TABLE IF NOT EXISTS beast_dependencies(
            scope TEXT NOT NULL, child TEXT NOT NULL, parent TEXT NOT NULL,
            PRIMARY KEY(scope,child,parent));
        CREATE INDEX IF NOT EXISTS beast_dependency_reverse ON beast_dependencies(scope,parent);
        CREATE TABLE IF NOT EXISTS beast_documents(
            scope TEXT NOT NULL, id TEXT NOT NULL, polarity TEXT NOT NULL,
            digest TEXT NOT NULL, metadata TEXT NOT NULL, PRIMARY KEY(scope,id,polarity));
        CREATE TABLE IF NOT EXISTS beast_terms(
            scope TEXT NOT NULL, term TEXT NOT NULL, id TEXT NOT NULL, polarity TEXT NOT NULL,
            PRIMARY KEY(scope,term,id,polarity),
            FOREIGN KEY(scope,id,polarity) REFERENCES beast_documents(scope,id,polarity)
                ON DELETE CASCADE);
        CREATE INDEX IF NOT EXISTS beast_document_terms ON beast_terms(scope,id,polarity);
        """)
        # Early local builds placed memo payloads in the shared raw-object table.
        # Preserve those existing bytes (their raw-source pin intent is unknown)
        # while ensuring all future cache churn is confined to bounded memo rows.
        if "body" not in {row[1] for row in self.db.execute("PRAGMA table_info(beast_memo)")}:
            self.db.execute("ALTER TABLE beast_memo ADD COLUMN body BLOB")
            self.db.execute("""UPDATE beast_memo SET body=(SELECT body FROM beast_objects
                WHERE beast_objects.scope=beast_memo.scope AND beast_objects.digest=beast_memo.digest)
                WHERE negative=0""")
        self.db.commit()

    def close(self) -> None:
        with self._lock:
            self.db.close()

    def __enter__(self) -> ArtifactStore:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _tick(self) -> int:
        self.db.execute("UPDATE beast_counter SET value=value+1 WHERE id=1")
        return self.db.execute("SELECT value FROM beast_counter WHERE id=1").fetchone()[0]

    def _now(self) -> float:
        now = self.clock()
        if type(now) not in (int, float) or not math.isfinite(now):
            raise ValueError("CLOCK_INVALID")
        return now

    def put_object(self, scope: Scope, body: bytes) -> str:
        scope_key = _scope_key(scope)
        if type(body) is not bytes or len(body) > _MAX_BYTES:
            raise ValueError("EXACT_BYTES_REQUIRED")
        digest = hashlib.sha256(body).hexdigest()
        with self._lock, self.db:
            existing = self.db.execute("SELECT body FROM beast_objects WHERE scope=? AND digest=?",
                                       (scope_key, digest)).fetchone()
            if existing is not None and existing[0] != body:
                raise IntegrityError("OBJECT_CORRUPTED_OR_DIGEST_COLLISION")
            self.db.execute("INSERT OR IGNORE INTO beast_objects VALUES(?,?,?)",
                            (scope_key, digest, body))
        return digest

    @staticmethod
    def _verify(digest: str, body: bytes) -> bytes:
        if hashlib.sha256(body).hexdigest() != digest:
            raise IntegrityError("OBJECT_DIGEST_MISMATCH")
        return body

    def get_object(self, scope: Scope, digest: str) -> bytes | None:
        return self.batch_get(scope, [digest])[0]

    def batch_get(self, scope: Scope, digests: Iterable[str], chunk_size: int = 400) -> list[bytes | None]:
        scope_key = _scope_key(scope)
        requested = list(digests)
        if len(requested) > 100000 or any(type(d) is not str or not _HEX.fullmatch(d) for d in requested):
            raise ValueError("DIGEST_BATCH_INVALID")
        if type(chunk_size) is not int or not 1 <= chunk_size <= 400:
            raise ValueError("CHUNK_SIZE_INVALID")
        unique = list(dict.fromkeys(requested))
        found: dict[str, bytes] = {}
        with self._lock:
            for offset in range(0, len(unique), chunk_size):
                chunk = unique[offset:offset + chunk_size]
                sql = "SELECT digest,body FROM beast_objects WHERE scope=? AND digest IN (" + ",".join("?" for _ in chunk) + ")"
                for digest, body in self.db.execute(sql, (scope_key, *chunk)):
                    found[digest] = self._verify(digest, body)
        return [found.get(digest) for digest in requested]

    def memo_put(self, scope: Scope, key: str, value: Any, ttl: float = 300.0) -> None:
        scope_key = _scope_key(scope); _text(key, "MEMO_KEY")
        if type(ttl) not in (int, float) or not math.isfinite(ttl) or ttl <= 0:
            raise ValueError("TTL_INVALID")
        raw = None if value is NEGATIVE else canonical_bytes(value)
        with self._lock, self.db:
            now = self._now()
            expires = now + ttl
            if not math.isfinite(expires):
                raise ValueError("TTL_INVALID")
            digest = None if raw is None else hashlib.sha256(raw).hexdigest()
            self.db.execute("INSERT OR REPLACE INTO beast_memo(scope,key,digest,negative,expires,accessed,body) VALUES(?,?,?,?,?,?,?)",
                            (scope_key, key, digest, int(value is NEGATIVE), expires, self._tick(), raw))
            self.db.execute("DELETE FROM beast_memo WHERE expires<=?", (now,))
            excess = self.db.execute("SELECT COUNT(*) FROM beast_memo").fetchone()[0] - self.max_memo_entries
            if excess > 0:
                self.db.execute("DELETE FROM beast_memo WHERE rowid IN (SELECT rowid FROM beast_memo ORDER BY accessed,scope,key LIMIT ?)", (excess,))

    def memo_get(self, scope: Scope, key: str) -> CacheLookup:
        scope_key = _scope_key(scope); _text(key, "MEMO_KEY")
        with self._lock, self.db:
            row = self.db.execute("SELECT digest,negative,expires,body FROM beast_memo WHERE scope=? AND key=?",
                                  (scope_key, key)).fetchone()
            if row is None:
                return CacheLookup(False)
            digest, negative, expires, raw = row
            if expires <= self._now():
                self.db.execute("DELETE FROM beast_memo WHERE scope=? AND key=?", (scope_key, key))
                return CacheLookup(False)
            self.db.execute("UPDATE beast_memo SET accessed=? WHERE scope=? AND key=?",
                            (self._tick(), scope_key, key))
            if negative:
                if digest is not None or raw is not None:
                    raise IntegrityError("NEGATIVE_MEMO_PAYLOAD_INVALID")
                return CacheLookup(True, NEGATIVE, True)
            if raw is None:
                raise IntegrityError("MEMO_PAYLOAD_MISSING")
            self._verify(digest, raw)
            # A fresh JSON object on every return prevents mutation of stored state.
            return CacheLookup(True, json.loads(raw), False)

    def set_dependencies(self, scope: Scope, key: str, parents: Iterable[str]) -> None:
        scope_key = _scope_key(scope); _text(key, "DEPENDENT_KEY")
        parents = sorted(set(_text(parent, "PARENT_KEY") for parent in parents))
        if len(parents) > 100000:
            raise ValueError("TOO_MANY_DEPENDENCIES")
        with self._lock, self.db:
            self.db.execute("DELETE FROM beast_dependencies WHERE scope=? AND child=?", (scope_key, key))
            self.db.executemany("INSERT INTO beast_dependencies VALUES(?,?,?)",
                                ((scope_key, key, parent) for parent in parents))

    def invalidate(self, scope: Scope, roots: Iterable[str]) -> list[str]:
        """Drop root/descendant memo entries. Cycles terminate; evidence remains."""
        scope_key = _scope_key(scope)
        queue = deque(_text(root, "INVALIDATION_ROOT") for root in roots)
        seen: set[str] = set()
        with self._lock, self.db:
            while queue:
                node = queue.popleft()
                if node in seen:
                    continue
                seen.add(node)
                queue.extend(row[0] for row in self.db.execute(
                    "SELECT child FROM beast_dependencies WHERE scope=? AND parent=?", (scope_key, node)))
            self.db.executemany("DELETE FROM beast_memo WHERE scope=? AND key=?",
                                ((scope_key, node) for node in seen))
        return sorted(seen)

    def upsert_document(self, scope: Scope, doc_id: str, text: str,
                        polarity: str = "SUPPORTS", metadata: Any = None) -> bool:
        """Update one posting list only; return False for byte-identical input."""
        scope_key = _scope_key(scope); _text(doc_id, "DOCUMENT_ID")
        if type(polarity) is not str or polarity not in _POLARITIES:
            raise ValueError("EVIDENCE_POLARITY_INVALID")
        if type(text) is not str:
            raise ValueError("SEARCH_TEXT_INVALID")
        raw = text.encode("utf-8")
        if len(raw) > _MAX_BYTES:
            raise ValueError("SEARCH_TEXT_INVALID")
        digest = hashlib.sha256(raw).hexdigest()
        meta = canonical_bytes({} if metadata is None else metadata).decode("utf-8")
        with self._lock, self.db:
            previous = self.db.execute("SELECT digest,metadata FROM beast_documents WHERE scope=? AND id=? AND polarity=?",
                                       (scope_key, doc_id, polarity)).fetchone()
            if previous == (digest, meta):
                # Do not silently accept a corrupted source merely because index metadata matches.
                if self.get_object(scope, digest) is None:
                    raise IntegrityError("SEARCH_OBJECT_MISSING")
                return False
            terms = search_terms(text)
            self.put_object(scope, raw)
            self.db.execute("DELETE FROM beast_documents WHERE scope=? AND id=? AND polarity=?",
                            (scope_key, doc_id, polarity))
            self.db.execute("INSERT INTO beast_documents VALUES(?,?,?,?,?)", (scope_key, doc_id, polarity, digest, meta))
            self.db.executemany("INSERT INTO beast_terms VALUES(?,?,?,?)",
                                ((scope_key, term, doc_id, polarity) for term in terms))
        return True

    def remove_document(self, scope: Scope, doc_id: str, polarity: str | None = None) -> int:
        scope_key = _scope_key(scope); _text(doc_id, "DOCUMENT_ID")
        if polarity is not None and (type(polarity) is not str or polarity not in _POLARITIES):
            raise ValueError("EVIDENCE_POLARITY_INVALID")
        with self._lock, self.db:
            if polarity is None:
                result = self.db.execute("DELETE FROM beast_documents WHERE scope=? AND id=?", (scope_key, doc_id))
            else:
                result = self.db.execute("DELETE FROM beast_documents WHERE scope=? AND id=? AND polarity=?", (scope_key, doc_id, polarity))
            return result.rowcount

    def search(self, scope: Scope, query: str, limit: int = 20) -> list[dict]:
        scope_key = _scope_key(scope)
        if type(limit) is not int or not 1 <= limit <= 10000 or type(query) is not str or len(query) > 8192:
            raise ValueError("SEARCH_CONFIGURATION_INVALID")
        terms = sorted(search_terms(query))
        if not terms:
            return []
        with self._lock:
            if len(terms) <= 400:
                # Rank first, then join only the bounded result set. This avoids
                # one metadata query + one object query + another scope hash per
                # hit, while retaining a digest check for every returned body.
                # Pin this table's declared PRIMARY KEY covering index: without
                # ANALYZE, SQLite can prefer the document-oriented cascade index
                # for GROUP BY and scan every term in the scope. Exact term
                # seeks avoid that plan without maintaining a duplicate index.
                sql = """WITH ranked AS (
                    SELECT id,polarity,COUNT(*) AS score
                    FROM beast_terms INDEXED BY sqlite_autoindex_beast_terms_1
                    WHERE scope=? AND term IN (""" + ",".join("?" for _ in terms) + """
                    ) GROUP BY id,polarity ORDER BY score DESC,id,polarity LIMIT ?
                    ) SELECT r.id,r.polarity,r.score,d.digest,d.metadata,o.body
                    FROM ranked r
                    LEFT JOIN beast_documents d ON d.scope=? AND d.id=r.id AND d.polarity=r.polarity
                    LEFT JOIN beast_objects o ON o.scope=d.scope AND o.digest=d.digest
                    ORDER BY r.score DESC,r.id,r.polarity"""
                rows = self.db.execute(sql, (scope_key, *terms, limit, scope_key)).fetchall()
            else:
                # Very long queries remain bounded below SQLite's traditional
                # parameter ceiling. Aggregate exact overlap across all chunks,
                # then hydrate winners in batches instead of per-hit queries.
                scores: dict[tuple[str, str], int] = defaultdict(int)
                for offset in range(0, len(terms), 400):
                    chunk = terms[offset:offset + 400]
                    sql = "SELECT id,polarity,COUNT(*) FROM beast_terms INDEXED BY sqlite_autoindex_beast_terms_1 WHERE scope=? AND term IN (" + ",".join("?" for _ in chunk) + ") GROUP BY id,polarity"
                    for doc_id, polarity, count in self.db.execute(sql, (scope_key, *chunk)):
                        scores[(doc_id, polarity)] += count
                ordered = sorted(scores, key=lambda item: (-scores[item], item[0], item[1]))[:limit]
                documents = {}
                for offset in range(0, len(ordered), 400):
                    chunk = ordered[offset:offset + 400]
                    sql = """SELECT d.id,d.polarity,d.digest,d.metadata,o.body
                        FROM beast_documents d LEFT JOIN beast_objects o
                        ON o.scope=d.scope AND o.digest=d.digest
                        WHERE d.scope=? AND (d.id,d.polarity) IN (""" + ",".join("(?,?)" for _ in chunk) + ")"
                    parameters = (scope_key, *(value for key in chunk for value in key))
                    for doc_id, polarity, digest, meta, raw in self.db.execute(sql, parameters):
                        documents[(doc_id, polarity)] = (digest, meta, raw)
                rows = []
                for key in ordered:
                    if key not in documents:
                        raise IntegrityError("SEARCH_DOCUMENT_MISSING")
                    rows.append((*key, scores[key], *documents[key]))
            results = []
            for doc_id, polarity, score, digest, meta, raw in rows:
                if raw is None:
                    raise IntegrityError("SEARCH_OBJECT_MISSING")
                self._verify(digest, raw)
                results.append({"id": doc_id, "polarity": polarity,
                                "score": score, "text": raw.decode("utf-8"),
                                "source_digest": digest, "metadata": json.loads(meta)})
        return results
