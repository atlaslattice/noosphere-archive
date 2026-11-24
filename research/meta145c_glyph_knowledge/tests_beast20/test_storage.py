"""Behavioral contracts for storage, reuse, invalidation and multilingual search."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.beast20.storage import (
    ArtifactStore, CacheLookup, IntegrityError, NEGATIVE, Scope,
    canonical_bytes, rrf, search_terms, semantic_key,
)


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.scope = Scope("a" * 64, "ariadne-test/v1", "owner-test", 1)
        self.now = 100.0
        self.store = ArtifactStore(max_memo_entries=3, clock=lambda: self.now)

    def tearDown(self):
        self.store.close()

    def test_content_address_preserves_exact_bytes(self):
        raw = "e\u0301 — 制造\n".encode()
        digest = self.store.put_object(self.scope, raw)
        self.assertEqual(digest, hashlib.sha256(raw).hexdigest())
        self.assertEqual(self.store.get_object(self.scope, digest), raw)
        self.assertNotEqual(digest, self.store.put_object(self.scope, "é — 制造\n".encode()))

    def test_scope_source_edition_principal_and_epoch_are_independent(self):
        digest = self.store.put_object(self.scope, b"public synthetic fixture")
        variants = [replace(self.scope, source_digest="b" * 64),
                    replace(self.scope, edition="other/v1"),
                    replace(self.scope, principal="another-test-owner"),
                    replace(self.scope, rights_epoch=2)]
        for other in variants:
            with self.subTest(other=other):
                self.assertIsNone(self.store.get_object(other, digest))
                self.assertNotEqual(other.key, self.scope.key)

    def test_scope_never_allows_private_modes(self):
        for mode in ("PLAY", "IMAGINE", "BRAIN", "work", True, "WORK "):
            with self.assertRaises(ValueError):
                replace(self.scope, mode=mode)

    def test_scope_rejects_invalid_digest_and_ambiguous_epoch(self):
        for changes in ({"source_digest": "a" * 63}, {"rights_epoch": True},
                        {"rights_epoch": -1}, {"rights_epoch": ""},
                        {"principal": ""}, {"edition": ""}):
            with self.assertRaises(ValueError):
                replace(self.scope, **changes)

    def test_batch_order_duplicates_missing_and_empty(self):
        first = self.store.put_object(self.scope, b"one")
        second = self.store.put_object(self.scope, b"two")
        self.assertEqual(self.store.batch_get(self.scope, [second, "0" * 64, first, second], 1),
                         [b"two", None, b"one", b"two"])
        self.assertEqual(self.store.batch_get(self.scope, []), [])

    def test_batch_over_sqlite_variable_limit_and_chunk_bounds(self):
        digests = [self.store.put_object(self.scope, str(i).encode()) for i in range(1001)]
        self.assertEqual(self.store.batch_get(self.scope, digests), [str(i).encode() for i in range(1001)])
        for chunk in (0, 401, True):
            with self.assertRaises(ValueError):
                self.store.batch_get(self.scope, digests, chunk)

    def test_corruption_rejected_for_direct_batch_and_duplicate_write(self):
        digest = self.store.put_object(self.scope, b"original")
        self.store.db.execute("UPDATE beast_objects SET body=? WHERE digest=?", (b"changed", digest))
        self.store.db.commit()
        for operation in (lambda: self.store.get_object(self.scope, digest),
                          lambda: self.store.batch_get(self.scope, [digest, "0" * 64]),
                          lambda: self.store.put_object(self.scope, b"original")):
            with self.assertRaises(IntegrityError):
                operation()

    def test_semantic_key_covers_all_parameters_and_is_order_stable(self):
        original = semantic_key(self.scope, "plate", "v1", {"a": 1, "b": 2}, [1, 2])
        self.assertEqual(original, semantic_key(self.scope, "plate", "v1", {"b": 2, "a": 1}, [1, 2]))
        variants = [semantic_key(self.scope, "other", "v1", {"a": 1, "b": 2}, [1, 2]),
                    semantic_key(self.scope, "plate", "v2", {"a": 1, "b": 2}, [1, 2]),
                    semantic_key(self.scope, "plate", "v1", {"a": 1, "b": 3}, [1, 2]),
                    semantic_key(self.scope, "plate", "v1", {"a": 1, "b": 2}, [2, 1]),
                    semantic_key(replace(self.scope, rights_epoch=2), "plate", "v1", {"a": 1, "b": 2}, [1, 2])]
        self.assertTrue(all(item != original for item in variants))

    def test_invalid_json_cannot_enter_cache_or_key(self):
        class Impure(str):
            pass
        for value in (math.nan, math.inf, {1: "non-string-key"}, Impure("x"), {"x": object()}):
            with self.assertRaises(ValueError):
                self.store.memo_put(self.scope, "bad", value)
            with self.assertRaises(ValueError):
                semantic_key(self.scope, "x", "v1", value)
        self.assertEqual(self.store.memo_get(self.scope, "bad"), CacheLookup(False))

    def test_memo_returns_copies_and_distinguishes_null_negative_and_miss(self):
        payload = {"nested": [1, 2]}
        self.store.memo_put(self.scope, "data", payload)
        payload["nested"].append(3)
        returned = self.store.memo_get(self.scope, "data")
        returned.value["nested"].append(4)
        self.assertEqual(self.store.memo_get(self.scope, "data").value, {"nested": [1, 2]})
        self.store.memo_put(self.scope, "null", None)
        self.store.memo_put(self.scope, "negative", NEGATIVE)
        self.assertEqual(self.store.memo_get(self.scope, "null"), CacheLookup(True, None, False))
        negative = self.store.memo_get(self.scope, "negative")
        self.assertTrue(negative.hit and negative.negative)
        self.assertIs(negative.value, NEGATIVE)
        self.assertFalse(self.store.memo_get(self.scope, "missing").hit)

    def test_ttl_has_exact_expiry_boundary(self):
        self.store.memo_put(self.scope, "x", {"x": 1}, ttl=5)
        self.now = 104.999
        self.assertTrue(self.store.memo_get(self.scope, "x").hit)
        self.now = 105
        self.assertFalse(self.store.memo_get(self.scope, "x").hit)

    def test_lru_eviction_and_negative_entries_count_toward_capacity(self):
        for key in "abc":
            self.store.memo_put(self.scope, key, key)
        self.store.memo_get(self.scope, "a")
        self.store.memo_put(self.scope, "d", NEGATIVE)
        self.assertTrue(self.store.memo_get(self.scope, "a").hit)
        self.assertFalse(self.store.memo_get(self.scope, "b").hit)
        self.assertTrue(self.store.memo_get(self.scope, "d").negative)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM beast_memo").fetchone()[0], 3)

    def test_memo_scope_ignores_same_named_key_in_other_epoch(self):
        self.store.memo_put(self.scope, "same", {"value": 42})
        self.assertFalse(self.store.memo_get(replace(self.scope, rights_epoch=2), "same").hit)

    def test_memo_detects_missing_or_corrupt_content(self):
        self.store.memo_put(self.scope, "x", {"x": 1})
        self.store.db.execute("UPDATE beast_memo SET body=NULL WHERE key='x'")
        self.store.db.commit()
        with self.assertRaises(IntegrityError):
            self.store.memo_get(self.scope, "x")
        self.store.memo_put(self.scope, "x", {"x": 1})
        self.store.db.execute("UPDATE beast_memo SET body=? WHERE key='x'", (b'{"x":2}',))
        self.store.db.commit()
        with self.assertRaises(IntegrityError):
            self.store.memo_get(self.scope, "x")

    def test_memo_churn_does_not_accumulate_derived_blobs_or_delete_raw_source(self):
        digest = self.store.put_object(self.scope, b"raw source retained")
        for number in range(500):
            self.store.memo_put(self.scope, f"derived-{number}", {"n": number, "text": "x" * 1000})
        count, bytes_retained = self.store.db.execute("SELECT COUNT(*),SUM(LENGTH(body)) FROM beast_memo").fetchone()
        self.assertEqual(count, 3)
        self.assertLess(bytes_retained, 3100)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM beast_objects").fetchone()[0], 1)
        self.assertEqual(self.store.get_object(self.scope, digest), b"raw source retained")
        self.now += 1000
        for number in range(497, 500):
            self.assertFalse(self.store.memo_get(self.scope, f"derived-{number}").hit)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM beast_memo").fetchone()[0], 0)
        self.assertEqual(self.store.get_object(self.scope, digest), b"raw source retained")

    def test_transitive_invalidation_diamond_cycle_and_scope(self):
        other = replace(self.scope, principal="other")
        for scope in (self.scope, other):
            self.store.set_dependencies(scope, "a", ["source"])
            self.store.set_dependencies(scope, "b", ["source", "c"])
            self.store.set_dependencies(scope, "c", ["a", "b"])
        self.store.memo_put(self.scope, "a", 1)
        self.store.memo_put(self.scope, "c", 2)
        self.store.memo_put(other, "c", 3)
        digest = self.store.put_object(self.scope, b"immutable source")
        self.assertEqual(self.store.invalidate(self.scope, ["source", "source"]), ["a", "b", "c", "source"])
        self.assertFalse(self.store.memo_get(self.scope, "a").hit)
        self.assertFalse(self.store.memo_get(self.scope, "c").hit)
        self.assertEqual(self.store.memo_get(other, "c").value, 3)
        self.assertEqual(self.store.get_object(self.scope, digest), b"immutable source")

    def test_dependency_replacement_removes_old_reverse_edge(self):
        self.store.set_dependencies(self.scope, "derived", ["old"])
        self.store.set_dependencies(self.scope, "derived", ["new"])
        self.assertEqual(self.store.invalidate(self.scope, ["old"]), ["old"])
        self.assertEqual(self.store.invalidate(self.scope, ["new"]), ["derived", "new"])

    def test_unicode_normalization_preserves_original_source(self):
        raw = "ＣＡＦÉ e\u0301 制造"
        self.assertTrue(self.store.upsert_document(self.scope, "d", raw))
        result = self.store.search(self.scope, "café é")
        self.assertEqual(result[0]["text"], raw)
        self.assertEqual(result[0]["source_digest"], hashlib.sha256(raw.encode()).hexdigest())

    def test_one_and_two_character_mandarin_queries(self):
        self.store.upsert_document(self.scope, "factory", "中国制造供应链 锂电池")
        self.store.upsert_document(self.scope, "other", "海洋环境")
        for query in ("制", "制造", "锂", "电池"):
            self.assertEqual(self.store.search(self.scope, query)[0]["id"], "factory")
        self.assertEqual(self.store.search(self.scope, ""), [])
        self.assertEqual(self.store.search(self.scope, "missing"), [])

    def test_polarities_are_independent_even_for_same_document_identifier(self):
        self.store.upsert_document(self.scope, "paper", "thermal transport supports", "SUPPORTS")
        self.store.upsert_document(self.scope, "paper", "thermal transport challenge", "CHALLENGES")
        rows = self.store.search(self.scope, "thermal transport")
        self.assertEqual({row["polarity"] for row in rows}, {"SUPPORTS", "CHALLENGES"})
        self.store.remove_document(self.scope, "paper", "SUPPORTS")
        self.assertEqual([row["polarity"] for row in self.store.search(self.scope, "thermal")], ["CHALLENGES"])

    def test_incremental_search_matches_independent_linear_token_overlap(self):
        documents = {"a": "battery thermal 制造", "b": "battery storage", "c": "海洋 锂电池"}
        for doc_id, text in documents.items():
            self.store.upsert_document(self.scope, doc_id, text)
        self.assertFalse(self.store.upsert_document(self.scope, "a", documents["a"]))
        documents["a"] = "thermal transport 制造"
        self.store.upsert_document(self.scope, "a", documents["a"])
        self.store.remove_document(self.scope, "b"); del documents["b"]
        for query in ("battery", "thermal", "制造", "海洋 thermal"):
            query_terms = search_terms(query)
            expected = sorted([(doc_id, len(query_terms & search_terms(text))) for doc_id, text in documents.items()
                               if query_terms & search_terms(text)], key=lambda item: (-item[1], item[0]))
            self.assertEqual([(row["id"], row["score"]) for row in self.store.search(self.scope, query)], expected)

    def test_document_replacement_removes_obsolete_terms(self):
        self.store.upsert_document(self.scope, "d", "old unique")
        self.store.upsert_document(self.scope, "d", "new content")
        self.assertEqual(self.store.search(self.scope, "old"), [])
        self.assertEqual(self.store.search(self.scope, "new")[0]["id"], "d")

    def test_identical_document_skips_tokenization_but_metadata_or_text_change_reindexes(self):
        self.store.upsert_document(self.scope, "d", "unchanged 制造", metadata={"v": 1})
        with patch("src.beast20.storage.search_terms", wraps=search_terms) as tokenize:
            self.assertFalse(self.store.upsert_document(self.scope, "d", "unchanged 制造", metadata={"v": 1}))
            tokenize.assert_not_called()
            self.assertTrue(self.store.upsert_document(self.scope, "d", "unchanged 制造", metadata={"v": 2}))
            tokenize.assert_called_once()
        self.assertEqual(self.store.search(self.scope, "制造")[0]["metadata"], {"v": 2})

    def test_search_does_not_cross_scopes_and_rejects_missing_source(self):
        self.store.upsert_document(self.scope, "d", "lookup")
        self.assertEqual(self.store.search(replace(self.scope, rights_epoch=2), "lookup"), [])
        self.store.db.execute("DELETE FROM beast_objects")
        self.store.db.commit()
        with self.assertRaises(IntegrityError):
            self.store.search(self.scope, "lookup")
        with self.assertRaises(IntegrityError):
            self.store.upsert_document(self.scope, "d", "lookup")

    def test_search_batches_hydration_in_one_query_without_skipping_integrity(self):
        for number in range(30):
            self.store.upsert_document(self.scope, f"doc-{number:02}", f"shared text {number}")
        statements = []
        self.store.db.set_trace_callback(statements.append)
        try:
            rows = self.store.search(self.scope, "shared", limit=20)
        finally:
            self.store.db.set_trace_callback(None)
        self.assertEqual(len(rows), 20)
        self.assertEqual(len(statements), 1)
        self.store.db.execute("UPDATE beast_objects SET body=? WHERE digest=?",
                              (b"corrupted", rows[0]["source_digest"]))
        self.store.db.commit()
        with self.assertRaises(IntegrityError):
            self.store.search(self.scope, "shared", limit=20)

    def test_long_search_chunks_terms_and_result_hydration_with_exact_scores(self):
        # More than 400 unique terms and more than 400 hits exercise both bounds.
        for number in range(405):
            self.store.upsert_document(self.scope, f"doc-{number:03}", f"token{number} shared")
        query = " ".join(f"token{number}" for number in range(405)) + " shared"
        rows = self.store.search(self.scope, query, limit=1000)
        self.assertEqual([(row["id"], row["score"]) for row in rows],
                         [(f"doc-{number:03}", 2) for number in range(405)])
        self.assertEqual(self.store.search(replace(self.scope, rights_epoch=2), query, limit=1000), [])

    def test_rrf_deduplicates_per_lane_and_preserves_dissent(self):
        supports = {"id": "p", "polarity": "SUPPORTS", "text": "reported improvement"}
        challenges = {"id": "p", "polarity": "CHALLENGES", "text": "failed replication"}
        rows = rrf([[supports, supports, challenges], [challenges, supports]], k=10)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["rrf_score"], 1 / 11 + 1 / 12)
        self.assertEqual(rows[1]["rrf_score"], rows[0]["rrf_score"])
        self.assertEqual([row["polarity"] for row in rows], ["CHALLENGES", "SUPPORTS"])

    def test_rrf_rejects_same_identity_different_source(self):
        with self.assertRaises(ValueError):
            rrf([[{"id": "p", "polarity": "SUPPORTS", "text": "one"}],
                 [{"id": "p", "polarity": "SUPPORTS", "text": "two"}]])

    def test_persistent_objects_memo_index_and_dependencies_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "state.sqlite3")
            with ArtifactStore(path, clock=lambda: self.now) as store:
                digest = store.put_object(self.scope, b"persisted")
                store.memo_put(self.scope, "derived", {"n": 7})
                store.upsert_document(self.scope, "doc", "persisted search")
                store.set_dependencies(self.scope, "derived", [digest])
            with ArtifactStore(path, clock=lambda: self.now) as store:
                self.assertEqual(store.get_object(self.scope, digest), b"persisted")
                self.assertEqual(store.memo_get(self.scope, "derived").value, {"n": 7})
                self.assertEqual(store.search(self.scope, "persisted")[0]["id"], "doc")
                self.assertEqual(store.invalidate(self.scope, [digest]), [digest, "derived"])

    def test_serialized_connection_handles_concurrent_writers(self):
        def write(number):
            raw = str(number).encode()
            digest = self.store.put_object(self.scope, raw)
            self.store.memo_put(self.scope, str(number), {"n": number})
            return self.store.get_object(self.scope, digest)
        with ThreadPoolExecutor(max_workers=8) as executor:
            self.assertEqual(list(executor.map(write, range(32))), [str(number).encode() for number in range(32)])
        self.assertLessEqual(self.store.db.execute("SELECT COUNT(*) FROM beast_memo").fetchone()[0], 3)

    def test_invalid_clock_and_ttl_fail_without_cache_result(self):
        for ttl in (0, -1, math.nan, math.inf, True):
            with self.assertRaises(ValueError):
                self.store.memo_put(self.scope, "x", 1, ttl)
        self.now = math.nan
        with self.assertRaises(ValueError):
            self.store.memo_put(self.scope, "x", 1)
        self.assertFalse(self.store.memo_get(self.scope, "x").hit)


if __name__ == "__main__":
    unittest.main()
