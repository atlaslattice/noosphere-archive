"""Independent adapter and trust-boundary checks against original GF8/R10.

All inputs are synthetic local fixtures; the permission callback is a test seam,
not evidence of hosted authentication. No network or resident/model calls occur.
"""
from dataclasses import asdict, replace
from pathlib import Path
import tempfile
import unittest

from src import gf8, reasoning_filter
from src.glyph import REGISTRY_SHA
from src.memory import LocalMemory
from src.beast20.runtime import AtlasBeastRuntime
from src.beast20.storage import ArtifactStore, Scope, semantic_key


class IndependentRuntimeReview(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.scope = Scope(REGISTRY_SHA, "Ariadne v0.7", "synthetic-review-owner", 7)
        self.store = ArtifactStore(str(Path(self.temp.name) / "store.sqlite"))
        self.runtime = AtlasBeastRuntime(self.scope, self.store, lambda *_: True)
        self.memory = LocalMemory(Path(self.temp.name) / "memory.sqlite")
        self.plate = gf8.Plate()
        self.arguments = {
            "hsn": "H01.S01.N01", "gf7": "GF7.B01.M01.C01",
            "plate": self.plate, "drive_hz": gf8.mode_hz(self.plate, 1, 1),
            "source_refs": ("https://example.com/synthetic-source",),
            "grid": 17, "max_mode": 2,
        }

    def tearDown(self):
        self.memory.close()
        self.store.close()
        self.temp.cleanup()

    def key(self):
        return semantic_key(
            self.scope, "gf8_physical_summary", self.runtime.physics_code_digest,
            {"plate": asdict(self.plate), "material": self.plate.metadata(),
             "drive_hz": self.arguments["drive_hz"], "grid": 17, "max_mode": 2})

    def note(self, name="review-note-1"):
        return self.memory.append({
            "event_id": name, "mode": "WORK", "scope": "SYNTHETIC_LOCAL_REVIEW",
            "coordinate": self.arguments["hsn"], "topic_id": "T1", "action": "NOTE",
            "source_ref": "urn:atlas:synthetic:independent-runtime-review",
            "source_digest": "d" * 64,
        })

    def test_cold_and_reused_contexts_exactly_match_original_filter(self):
        first = self.runtime.reasoning_context(**self.arguments)
        self.assertEqual(first, reasoning_filter.prepare_reasoning_context(**self.arguments))
        second_args = {**self.arguments, "hsn": "H12.S12.N12",
                       "gf7": "GF7.B02.M03.C04",
                       "source_refs": ("https://example.com/another-synthetic-source",)}
        second = self.runtime.reasoning_context(**second_args)
        self.assertEqual(second, reasoning_filter.prepare_reasoning_context(**second_args))
        self.assertEqual(self.runtime.stats["physics_computations"], 1)
        self.assertEqual(self.runtime.stats["physics_hits"], 1)

    def test_material_drive_and_resolution_changes_preserve_original_parity(self):
        variants = [
            self.arguments,
            {**self.arguments, "plate": replace(self.plate, material="aluminum")},
            {**self.arguments, "drive_hz": gf8.mode_hz(self.plate, 1, 2)},
            {**self.arguments, "grid": 19, "max_mode": 3},
        ]
        for args in variants:
            with self.subTest(material=args["plate"].material, drive=args["drive_hz"], grid=args["grid"]):
                actual = self.runtime.reasoning_context(**args)
                self.assertEqual(actual, reasoning_filter.prepare_reasoning_context(**args))

    def test_validly_hashed_authority_forgery_in_known_cache_is_rejected(self):
        self.runtime.reasoning_context(**self.arguments)
        forged = self.store.memo_get(self.scope, self.key()).value
        forged.update(canon_writes=True, model_weight_updates=True,
                      authorization="HOST_AUTHORIZED", source_truth="PROMOTED")
        self.store.memo_put(self.scope, self.key(), forged)
        with self.assertRaises(ValueError):
            self.runtime.reasoning_context(**self.arguments)

    def test_validly_hashed_numerical_forgery_in_known_cache_is_rejected(self):
        self.runtime.reasoning_context(**self.arguments)
        forged = self.store.memo_get(self.scope, self.key()).value
        forged["physical_model_output"]["nearest_mode"]["frequency_hz"] += 99999
        self.store.memo_put(self.scope, self.key(), forged)
        with self.assertRaises(ValueError):
            self.runtime.reasoning_context(**self.arguments)

    def test_new_runtime_recomputes_instead_of_trusting_self_hashed_persistent_cache(self):
        expected = reasoning_filter.prepare_reasoning_context(**self.arguments)
        self.runtime.reasoning_context(**self.arguments)
        forged = self.store.memo_get(self.scope, self.key()).value
        forged["canon_writes"] = True
        forged["physical_model_output"]["nearest_mode"]["frequency_hz"] += 99999
        self.store.memo_put(self.scope, self.key(), forged)
        restarted = AtlasBeastRuntime(self.scope, self.store, lambda *_: True)
        actual = restarted.reasoning_context(**self.arguments)
        self.assertEqual(actual, expected)
        self.assertFalse(actual["canon_writes"])
        self.assertEqual(restarted.stats["physics_computations"], 1)
        self.assertEqual(restarted.stats["physics_hits"], 0)

    def test_valid_shape_scope_mutation_is_rejected_after_construction(self):
        self.runtime.reasoning_context(**self.arguments)
        object.__setattr__(self.scope, "principal", "different-synthetic-owner")
        with self.assertRaises(ValueError):
            self.runtime.reasoning_context(**self.arguments)

    def test_runtime_scope_replacement_cannot_silently_change_rights_epoch(self):
        self.runtime.scope = replace(self.scope, rights_epoch=8)
        with self.assertRaises(ValueError):
            self.runtime.reasoning_context(**self.arguments)

    def test_wrong_registry_source_is_rejected_before_physics_runs(self):
        runtime = AtlasBeastRuntime(replace(self.scope, source_digest="0" * 64),
                                    self.store, lambda *_: True)
        with self.assertRaises(ValueError):
            runtime.reasoning_context(**self.arguments)
        self.assertEqual(runtime.stats["physics_computations"], 0)

    def test_warm_physics_cache_does_not_bypass_memory_tamper_detection(self):
        self.note()
        checkpoint = self.memory.verify()
        params = {**self.arguments, "memory": self.memory,
                  "expected_tip": checkpoint["tip"], "expected_count": checkpoint["count"]}
        self.runtime.reasoning_context(**params)
        with self.memory.db:
            self.memory.db.execute("UPDATE review_events SET action='CHALLENGE'")
        hits_before = self.runtime.stats["physics_hits"]
        with self.assertRaisesRegex(ValueError, "FAIL_CHAIN"):
            self.runtime.reasoning_context(**params)
        self.assertEqual(self.runtime.stats["physics_hits"], hits_before)

    def test_warm_physics_cache_does_not_accept_a_stale_independent_checkpoint(self):
        self.note()
        checkpoint = self.memory.verify()
        params = {**self.arguments, "memory": self.memory,
                  "expected_tip": checkpoint["tip"], "expected_count": checkpoint["count"]}
        self.runtime.reasoning_context(**params)
        self.note("review-note-2")
        with self.assertRaisesRegex(ValueError, "CHECKPOINT_CHANGED"):
            self.runtime.reasoning_context(**params)

    def test_memory_change_between_initial_verification_and_final_return_is_rejected(self):
        self.note()
        checkpoint = self.memory.verify()
        changed = [False]

        def authorize(_scope, phase):
            if phase == "RETURN" and not changed[0]:
                changed[0] = True
                self.note("review-note-2")
            return True

        runtime = AtlasBeastRuntime(self.scope, self.store, authorize)
        with self.assertRaisesRegex(ValueError, "CHECKPOINT_CHANGED"):
            runtime.reasoning_context(
                **self.arguments, memory=self.memory,
                expected_tip=checkpoint["tip"], expected_count=checkpoint["count"])

    def test_revocation_at_return_blocks_even_a_warm_cache_hit(self):
        self.runtime.reasoning_context(**self.arguments)
        self.runtime.authorize = lambda _scope, phase: phase != "RETURN"
        with self.assertRaises(PermissionError):
            self.runtime.reasoning_context(**self.arguments)


if __name__ == "__main__":
    unittest.main()
