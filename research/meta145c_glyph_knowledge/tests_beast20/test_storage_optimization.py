"""Compatibility, adversarial mutation and migration checks for storage hot paths."""
from collections import OrderedDict
from dataclasses import replace
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest

from src.beast20 import storage
from src.beast20.storage import ArtifactStore, IntegrityError, Scope, canonical_bytes, semantic_key


class StorageOptimizationTests(unittest.TestCase):
    def setUp(self):
        self.scope = Scope("a" * 64, "ariadne-test/v1", "owner-é-制造", 0)
        self.now = 100.0
        self.store = ArtifactStore(max_memo_entries=8, clock=lambda: self.now)

    def tearDown(self):
        self.store.close()

    def test_published_baseline_scope_and_semantic_digests_are_unchanged(self):
        # Fixed vectors captured from the exact 2bea022 storage module.
        vectors = [
            (0, "e7729632b2380bd5a274885e31fc0dae30d01fa5cd05f1c39352065761c36953",
             "a911f549fa628f838c9f6ede2c396319048eeea68c355e949a78d6f939a86282"),
            ("0", "e9926ab38380a9472e6136dbbf5aaf0f90b93303ad3c7aeb73e0a868cb945fcb",
             "0504c54e408c7f6ac05c0dc074cbe591805a5d24d966bc6c6dfe57c3227af4f4"),
            (7, "6c3763bdf440e2d06525059aca447a1d6f7c3d29e7c31eef227e5cb282b74949",
             "b6a7035fea5219a885b82ce8570844e154a09007d582b402078bcbf55869267c"),
            ("rights-v2", "364592b059cb1160c5db1c1f2da0d5e7507ebebe1dadaeb62fa4101b1c8dadac",
             "87afe5d60e78687bb1f7b1c673e8e681dc2f5b929fe54d9a292bf9c58112392d"),
        ]
        for epoch, identity, memo in vectors:
            with self.subTest(epoch=epoch):
                scope = replace(self.scope, rights_epoch=epoch)
                for _ in range(3):
                    self.assertEqual(scope.key, identity)
                    self.assertEqual(semantic_key(scope, "derive", "v1", {"b": 2, "a": 1},
                                                  {"nodes": ["H01.S01.N01"]}), memo)

    def test_each_valid_mutated_scope_field_changes_the_namespace(self):
        for field, changed in (("source_digest", "b" * 64), ("edition", "ariadne-test/v2"),
                               ("principal", "other-owner"), ("rights_epoch", "0")):
            with self.subTest(field=field):
                scope = replace(self.scope)
                original_key = scope.key
                digest = self.store.put_object(scope, b"original bytes")
                self.store.memo_put(scope, "entry", {"original": True})
                original_value = getattr(scope, field)
                object.__setattr__(scope, field, changed)
                self.assertNotEqual(scope.key, original_key)
                self.assertIsNone(self.store.get_object(scope, digest))
                self.assertFalse(self.store.memo_get(scope, "entry").hit)
                object.__setattr__(scope, field, original_value)
                self.assertEqual(scope.key, original_key)
                self.assertEqual(self.store.get_object(scope, digest), b"original bytes")
                self.assertEqual(self.store.memo_get(scope, "entry").value, {"original": True})

    def test_warmed_identity_never_bypasses_current_field_validation(self):
        for field, invalid in (("source_digest", "x"), ("edition", ""), ("principal", ""),
                               ("rights_epoch", True), ("mode", "PLAY")):
            with self.subTest(field=field):
                scope = replace(self.scope)
                digest = self.store.put_object(scope, b"must stay scoped")
                object.__setattr__(scope, field, invalid)
                for operation in (lambda: scope.key, lambda: self.store.get_object(scope, digest),
                                  lambda: self.store.memo_get(scope, "entry"),
                                  lambda: semantic_key(scope, "derive", "v1", {})):
                    with self.assertRaises(ValueError):
                        operation()

    def test_invalid_objects_are_rejected_before_cache_hash_or_comparison_hooks(self):
        calls = []
        class Hostile(str):
            def __hash__(self):
                calls.append("hash")
                raise AssertionError("invalid value entered cache")
            def __eq__(self, other):
                calls.append("eq")
                raise AssertionError("invalid value compared")
        _ = self.scope.key
        object.__setattr__(self.scope, "principal", Hostile("owner"))
        with self.assertRaisesRegex(ValueError, "PRINCIPAL_INVALID"):
            self.store.memo_get(self.scope, "x")
        self.assertEqual(calls, [])

    def test_scope_hash_cache_is_entry_bounded_and_recomputes_evicted_values(self):
        expected = self.scope.key
        for number in range(600):
            self.assertEqual(len(replace(self.scope, principal=f"scope-{number}").key), 64)
        self.assertLessEqual(storage._scope_digest.cache_info().currsize, 256)
        self.assertEqual(self.scope.key, expected)

    def test_scope_subclasses_are_not_admitted_by_storage_after_cache_warmup(self):
        class DerivedScope(Scope):
            pass
        _ = self.scope.key
        with self.assertRaisesRegex(ValueError, "EXACT_SCOPE_REQUIRED"):
            self.store.memo_get(DerivedScope("a" * 64, "ariadne-test/v1", "owner-é-制造", 0), "x")

    def test_expiry_cleanup_is_global_and_exact_at_the_boundary(self):
        other = replace(self.scope, principal="second-owner")
        raw_digest = self.store.put_object(other, b"retain source")
        self.store.memo_put(self.scope, "expired", 1, ttl=5)
        self.store.memo_put(other, "also-expired", 2, ttl=5)
        self.store.memo_put(other, "later", 3, ttl=20)
        self.now = 104.999
        self.assertTrue(self.store.memo_get(self.scope, "expired").hit)
        self.now = 105
        self.store.memo_put(self.scope, "trigger", 4, ttl=1)
        rows = self.store.db.execute("SELECT key FROM beast_memo ORDER BY key").fetchall()
        self.assertEqual(rows, [("later",), ("trigger",)])
        self.assertEqual(self.store.get_object(other, raw_digest), b"retain source")
        self.now = 106
        self.assertFalse(self.store.memo_get(self.scope, "trigger").hit)
        self.assertEqual(self.store.memo_get(other, "later").value, 3)

    def test_lru_tie_break_remains_scope_then_key(self):
        self.store.max_memo_entries = 2
        other = replace(self.scope, principal="second-owner")
        self.store.memo_put(self.scope, "a", 1)
        self.store.memo_put(other, "b", 2)
        with self.store.db:
            self.store.db.execute("UPDATE beast_memo SET accessed=7")
            self.store.db.execute("UPDATE beast_counter SET value=50 WHERE id=1")
        expected_evicted = min((self.scope.key, "a"), (other.key, "b"))
        self.store.memo_put(self.scope, "new", 3)
        identities = set(self.store.db.execute("SELECT scope,key FROM beast_memo"))
        self.assertNotIn(expected_evicted, identities)
        self.assertIn((self.scope.key, "new"), identities)

    def test_capacity_semantics_match_lru_oracle_for_small_and_large_caches(self):
        for capacity in (1, 8, 256, 2048):
            with self.subTest(capacity=capacity):
                with ArtifactStore(max_memo_entries=capacity, clock=lambda: self.now) as store:
                    oracle = OrderedDict()
                    for number in range(min(capacity + 9, 260)):
                        key = f"k{number}"
                        store.memo_put(self.scope, key, number)
                        oracle[key] = number
                        if len(oracle) > capacity:
                            oracle.popitem(last=False)
                        if number % 5 == 0:
                            touched = next(iter(oracle))
                            self.assertEqual(store.memo_get(self.scope, touched).value, oracle[touched])
                            oracle.move_to_end(touched)
                    self.assertEqual(set(k for k, in store.db.execute("SELECT key FROM beast_memo")), set(oracle))

    def test_existing_database_gets_index_without_losing_raw_memo_or_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "existing.sqlite")
            with ArtifactStore(path, clock=lambda: self.now) as store:
                digest = store.put_object(self.scope, b"durable source")
                store.memo_put(self.scope, "derived", {"value": 7})
                store.set_dependencies(self.scope, "derived", [digest])
                store.db.execute("DROP INDEX beast_memo_expiry")
                store.db.commit()
            with ArtifactStore(path, clock=lambda: self.now) as store:
                self.assertEqual(store.get_object(self.scope, digest), b"durable source")
                self.assertEqual(store.memo_get(self.scope, "derived").value, {"value": 7})
                self.assertEqual(store.invalidate(self.scope, [digest]), sorted([digest, "derived"]))
                self.assertEqual(store.get_object(self.scope, digest), b"durable source")

    def test_legacy_memo_payload_migration_still_preserves_exact_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "legacy.sqlite")
            raw = canonical_bytes({"legacy": [1, 2]})
            digest = hashlib.sha256(raw).hexdigest()
            db = sqlite3.connect(path)
            db.executescript("""
                CREATE TABLE beast_objects(scope TEXT,digest TEXT,body BLOB,PRIMARY KEY(scope,digest));
                CREATE TABLE beast_memo(scope TEXT,key TEXT,digest TEXT,negative INTEGER,
                    expires REAL,accessed INTEGER,PRIMARY KEY(scope,key));
            """)
            db.execute("INSERT INTO beast_objects VALUES(?,?,?)", (self.scope.key, digest, raw))
            db.execute("INSERT INTO beast_memo VALUES(?,?,?,?,?,?)",
                       (self.scope.key, "legacy", digest, 0, 200.0, 1))
            db.commit()
            db.close()
            with ArtifactStore(path, clock=lambda: self.now) as store:
                self.assertEqual(store.memo_get(self.scope, "legacy").value, {"legacy": [1, 2]})
                self.assertEqual(store.get_object(self.scope, digest), raw)

    def test_two_store_connections_share_capacity_and_expiry_truth(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "shared.sqlite")
            with ArtifactStore(path, max_memo_entries=2, clock=lambda: self.now) as first, \
                    ArtifactStore(path, max_memo_entries=2, clock=lambda: self.now) as second:
                first.memo_put(self.scope, "a", 1, ttl=5)
                second.memo_put(self.scope, "b", 2, ttl=20)
                first.memo_get(self.scope, "a")
                second.memo_put(self.scope, "c", 3, ttl=20)
                self.assertFalse(first.memo_get(self.scope, "b").hit)
                self.now = 105
                second.memo_put(self.scope, "d", 4, ttl=20)
                self.assertFalse(first.memo_get(self.scope, "a").hit)
                self.assertEqual(first.db.execute("SELECT COUNT(*) FROM beast_memo").fetchone()[0], 2)

    def test_warmed_scope_identity_does_not_memoize_payload_integrity(self):
        digest = self.store.put_object(self.scope, b"source")
        self.assertEqual(self.store.get_object(self.scope, digest), b"source")
        with self.store.db:
            self.store.db.execute("UPDATE beast_objects SET body=?", (b"tampered",))
        with self.assertRaises(IntegrityError):
            self.store.batch_get(self.scope, [digest, digest])
        self.store.memo_put(self.scope, "m", {"correct": True})
        self.assertTrue(self.store.memo_get(self.scope, "m").hit)
        with self.store.db:
            self.store.db.execute("UPDATE beast_memo SET body=? WHERE key='m'", (b'{"correct":false}',))
        counter = self.store.db.execute("SELECT value FROM beast_counter WHERE id=1").fetchone()[0]
        with self.assertRaises(IntegrityError):
            self.store.memo_get(self.scope, "m")
        self.assertEqual(self.store.db.execute("SELECT value FROM beast_counter WHERE id=1").fetchone()[0], counter)

    def test_invalidation_uses_current_scope_after_a_valid_mutation(self):
        self.store.set_dependencies(self.scope, "derived", ["root"])
        self.store.memo_put(self.scope, "derived", {"namespace": "original"})
        original_principal = self.scope.principal
        object.__setattr__(self.scope, "principal", "new-principal")
        self.store.set_dependencies(self.scope, "derived", ["root"])
        self.store.memo_put(self.scope, "derived", {"namespace": "changed"})
        self.assertEqual(self.store.invalidate(self.scope, ["root"]), ["derived", "root"])
        self.assertFalse(self.store.memo_get(self.scope, "derived").hit)
        object.__setattr__(self.scope, "principal", original_principal)
        self.assertEqual(self.store.memo_get(self.scope, "derived").value, {"namespace": "original"})


if __name__ == "__main__":
    unittest.main()

