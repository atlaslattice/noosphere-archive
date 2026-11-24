"""Provenance framing, complete changes and adversarial input contracts."""
from copy import deepcopy
import hashlib
import json
from types import MappingProxyType
import unittest

from src.beast20.synthesis_provenance import (
    MAX_KEY_LENGTH, MAX_MAP_ENTRIES, SCHEMA, make_provenance,
    stale_causes, validate_provenance,
)


A, B, C, D = (hashlib.sha256(word.encode()).hexdigest()
              for word in ("code", "input", "changed", "check"))


def record(**changes):
    values = {"code_sha256": A, "inputs": {"source": B},
              "dependencies": {"build": B}, "peer_evidence": {"review": C},
              "checks": {"positive": D}}
    values.update(changes)
    return make_provenance(**values)


class SynthesisProvenanceTests(unittest.TestCase):
    def test_key_order_is_stable_in_every_map_and_on_validation(self):
        left = {"z": B, "a": C}
        right = {"a": C, "z": B}
        first = make_provenance(code_sha256=A, inputs=left, dependencies=left,
                                peer_evidence=left, checks=left)
        second = make_provenance(code_sha256=A, inputs=right, dependencies=right,
                                 peer_evidence=right, checks=right)
        self.assertEqual(first, second)
        self.assertEqual(validate_provenance(dict(reversed(list(first.items())))), first)
        self.assertEqual(stale_causes(first, second), [])
        self.assertTrue(all(list(first[key]) == ["a", "z"] for key in
                            ("inputs", "dependencies", "peer_evidence", "checks")))

    def test_exact_schema_and_canonical_seal_round_trip(self):
        actual = record()
        self.assertEqual(set(actual), {"schema", "code_sha256", "inputs",
                                      "dependencies", "peer_evidence", "checks", "sha256"})
        self.assertEqual(actual["schema"], SCHEMA)
        body = {k: v for k, v in actual.items() if k != "sha256"}
        wire = json.dumps(body, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        self.assertEqual(actual["sha256"], hashlib.sha256(wire.encode("ascii")).hexdigest())
        self.assertEqual(validate_provenance(json.loads(json.dumps(actual))), actual)

    def test_empty_reference_maps_are_valid_but_not_acceptance(self):
        actual = make_provenance(code_sha256=A, inputs={}, dependencies={}, peer_evidence={}, checks={})
        self.assertEqual(validate_provenance(actual), actual)
        self.assertNotIn("verified", actual)
        self.assertNotIn("passed", actual)
        self.assertNotIn("authorized", actual)

    def test_ambiguous_raw_string_split_counterexample_is_rejected(self):
        self.assertEqual("ab" + "c", "a" + "bc")
        for code, data in (("ab", "c"), ("a", "bc")):
            with self.assertRaises(ValueError):
                record(code_sha256=code, inputs={"source": data})

    def test_key_boundaries_distinguish_equal_value_sequences(self):
        first = record(inputs={"a": B, "bc": C})
        second = record(inputs={"ab": B, "c": C})
        self.assertNotEqual(first["sha256"], second["sha256"])
        self.assertEqual([r["key"] for r in stale_causes(first, second)], ["a", "ab", "bc", "c"])

    def test_dependency_rename_changes_identity_even_with_same_digest(self):
        first, second = record(dependencies={"old": B}), record(dependencies={"new": B})
        self.assertNotEqual(first["sha256"], second["sha256"])
        self.assertEqual(stale_causes(first, second), [
            {"category": "DEPENDENCIES", "key": "new", "before": None, "after": B},
            {"category": "DEPENDENCIES", "key": "old", "before": B, "after": None},
        ])

    def test_same_values_in_different_domains_have_distinct_identity(self):
        first = record(inputs={"x": B}, dependencies={})
        second = record(inputs={}, dependencies={"x": B})
        self.assertNotEqual(first["sha256"], second["sha256"])
        self.assertEqual([r["category"] for r in stale_causes(first, second)], ["DATA", "DEPENDENCIES"])

    def test_every_changed_cause_is_retained_in_fixed_order(self):
        first = record(inputs={"z": B, "a": B}, dependencies={"z": B, "a": B},
                       peer_evidence={"z": B, "a": B}, checks={"z": B, "a": B})
        second = record(code_sha256=C, inputs={"z": C, "a": C},
                        dependencies={"z": C, "a": C}, peer_evidence={"z": C, "a": C},
                        checks={"z": C, "a": C})
        changes = stale_causes(first, second)
        expected = [("CODE", "code_sha256")] + [
            (category, key) for category in ("DATA", "DEPENDENCIES", "PEER_EVIDENCE", "CHECKS")
            for key in ("a", "z")]
        self.assertEqual([(r["category"], r["key"]) for r in changes], expected)
        self.assertEqual(len(changes), 9)
        self.assertTrue(all(set(r) == {"category", "key", "before", "after"} for r in changes))
        self.assertTrue(all(r["after"] == C for r in changes))

    def test_added_and_removed_entries_are_visible_in_every_domain(self):
        first = record(inputs={"removed": B}, dependencies={"removed": B},
                       peer_evidence={"removed": B}, checks={"removed": B})
        second = record(inputs={"added": C}, dependencies={"added": C},
                        peer_evidence={"added": C}, checks={"added": C})
        changes = stale_causes(first, second)
        self.assertEqual(len(changes), 8)
        for i in range(0, len(changes), 2):
            self.assertEqual((changes[i]["before"], changes[i]["after"]), (None, C))
            self.assertEqual((changes[i + 1]["before"], changes[i + 1]["after"]), (B, None))

    def test_removing_peer_or_negative_check_reference_is_not_silent(self):
        first = record(peer_evidence={"unresolved-dissent": C}, checks={"negative-result": D})
        changes = stale_causes(first, record(peer_evidence={}, checks={}))
        self.assertEqual([(r["category"], r["key"], r["after"]) for r in changes],
                         [("PEER_EVIDENCE", "unresolved-dissent", None),
                          ("CHECKS", "negative-result", None)])

    def test_input_maps_and_shared_aliases_are_detached(self):
        shared = {"source": B}
        actual = make_provenance(code_sha256=A, inputs=shared, dependencies=shared,
                                 peer_evidence=shared, checks=shared)
        shared["source"] = C
        self.assertEqual(actual["inputs"], {"source": B})
        actual["inputs"]["source"] = D
        self.assertEqual(actual["dependencies"], {"source": B})
        self.assertEqual(actual["peer_evidence"], {"source": B})
        self.assertEqual(actual["checks"], {"source": B})

    def test_validation_copy_is_detached_and_later_tampering_is_rejected(self):
        original = record()
        detached = validate_provenance(original)
        self.assertIsNot(original, detached)
        for field in ("inputs", "dependencies", "peer_evidence", "checks"):
            self.assertIsNot(original[field], detached[field])
        original["checks"]["positive"] = B
        self.assertEqual(detached["checks"]["positive"], D)
        with self.assertRaisesRegex(ValueError, "HASH_MISMATCH"):
            validate_provenance(original)

    def test_forged_seal_and_mutated_fields_are_rejected(self):
        for field in ("code_sha256", "sha256"):
            value = record()
            value[field] = "f" * 64
            with self.assertRaisesRegex(ValueError, "HASH_MISMATCH"):
                validate_provenance(value)
        for field in ("inputs", "dependencies", "peer_evidence", "checks"):
            value = record()
            value[field]["new"] = B
            with self.assertRaisesRegex(ValueError, "HASH_MISMATCH"):
                validate_provenance(value)

    def test_comparison_validates_both_records_before_returning_causes(self):
        good = record()
        bad = deepcopy(good)
        bad["inputs"]["source"] = C
        for first, second in ((bad, good), (good, bad)):
            with self.assertRaises(ValueError):
                stale_causes(first, second)
        before = deepcopy(good)
        stale_causes(good, record(code_sha256=C))
        self.assertEqual(good, before)

    def test_missing_and_unknown_record_fields_are_rejected(self):
        good = record()
        for key in good:
            value = dict(good)
            del value[key]
            with self.assertRaises(ValueError):
                validate_provenance(value)
        for key in ("body", "permissions", "authorized", "resident_verified", "passed"):
            value = {**good, key: True}
            with self.assertRaises(ValueError):
                validate_provenance(value)

    def test_wrong_schema_and_schema_subclass_are_rejected(self):
        class StringSubclass(str):
            pass
        for schema in (None, True, 1, "atlas.beast20.synthesis-provenance/v2", StringSubclass(SCHEMA)):
            with self.assertRaises(ValueError):
                validate_provenance({**record(), "schema": schema})

    def test_all_digest_positions_require_exact_lowercase_hex(self):
        class StringSubclass(str):
            pass
        invalid = (None, True, False, 1, 1.0, b"a" * 64, [], {}, "", "a" * 63,
                   "a" * 65, "A" * 64, "g" * 64, "a" * 64 + "\n", StringSubclass(A))
        for value in invalid:
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(ValueError):
                    record(code_sha256=value)
                for field in ("inputs", "dependencies", "peer_evidence", "checks"):
                    with self.assertRaises(ValueError):
                        record(**{field: {"key": value}})
                with self.assertRaises(ValueError):
                    validate_provenance({**record(), "sha256": value})

    def test_reference_key_bounds_and_reserved_names(self):
        for key in ("", "x" * (MAX_KEY_LENGTH + 1), "contains space", "\x00", "é",
                    "x\n", "__proto__", "prototype", "constructor", True, 1, None):
            with self.assertRaises(ValueError):
                record(inputs={key: B})
        for key in ("x" * MAX_KEY_LENGTH, "EX.H01.S01.N01", "source/path.py:revision-1"):
            self.assertEqual(record(inputs={key: B})["inputs"], {key: B})

    def test_each_map_has_a_finite_admission_bound(self):
        maximum = {f"ref{i}": B for i in range(MAX_MAP_ENTRIES)}
        for field in ("inputs", "dependencies", "peer_evidence", "checks"):
            self.assertEqual(len(record(**{field: maximum})[field]), MAX_MAP_ENTRIES)
            with self.assertRaises(ValueError):
                record(**{field: {**maximum, "overflow": B}})

    def test_non_dict_maps_and_record_containers_are_rejected(self):
        for value in (None, True, [], (), (("x", B),), MappingProxyType({"x": B})):
            for field in ("inputs", "dependencies", "peer_evidence", "checks"):
                with self.assertRaises(ValueError):
                    record(**{field: value})
            with self.assertRaises(ValueError):
                validate_provenance(value)

    def test_dict_subclass_hooks_are_never_invoked(self):
        class Trap(dict):
            def __len__(self):
                raise AssertionError("custom len called")
            def items(self):
                raise AssertionError("custom items called")
            def __iter__(self):
                raise AssertionError("custom iteration called")
        for field in ("inputs", "dependencies", "peer_evidence", "checks"):
            with self.assertRaises(ValueError):
                record(**{field: Trap(x=B)})
        with self.assertRaises(ValueError):
            validate_provenance(Trap(record()))

    def test_string_subclass_hooks_are_not_used_for_keys_or_values(self):
        calls = []
        class Trap(str):
            def __hash__(self):
                calls.append("hash")
                return str.__hash__(self)
            def __eq__(self, other):
                calls.append("eq")
                return str.__eq__(self, other)
        unusual_map = {Trap("source"): B}
        unusual_record = {**record(), Trap("schema"): SCHEMA}
        # A same-valued builtin key can retain its original object on assignment;
        # explicitly remove/reinsert to exercise an actual subclass record key.
        del unusual_record["schema"]
        unusual_record[Trap("schema")] = SCHEMA
        calls.clear()
        for operation in (lambda: record(inputs=unusual_map),
                          lambda: record(code_sha256=Trap(A)),
                          lambda: record(checks={"check": Trap(D)}),
                          lambda: validate_provenance(unusual_record)):
            with self.assertRaises(ValueError):
                operation()
        self.assertEqual(calls, [])

    def test_reference_labels_do_not_create_identity_or_permissions(self):
        value = record(peer_evidence={"owner": C, "independent-peer": B},
                       checks={"grant-admin": D})
        self.assertEqual(validate_provenance(value), value)
        self.assertEqual(set(value), {"schema", "code_sha256", "inputs",
                                    "dependencies", "peer_evidence", "checks", "sha256"})
        self.assertEqual(stale_causes(value, value), [])
        with self.assertRaises(ValueError):
            validate_provenance({**value, "authorized": True})


if __name__ == "__main__":
    unittest.main()
