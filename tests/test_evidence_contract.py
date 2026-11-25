"""Self-contained tests: no production identities, provider calls or third-party deps."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from validate_evidence_graph import validate_graph, SCHEMA_VERSION, NODE_TYPES, EDGE_TYPES


class EvidenceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.example = json.loads((ROOT / "examples/evidence_graph_v0_1.synthetic.json").read_text())
        cls.schema = json.loads((ROOT / "schemas/evidence_graph_v0_1.schema.json").read_text())

    def broken(self, transform):
        data = copy.deepcopy(self.example)
        transform(data)
        return {e["code"] for e in validate_graph(data)}

    def test_example_passes_offline_only(self):
        self.assertEqual(validate_graph(self.example), [])
        self.assertEqual(self.example["schema_version"], SCHEMA_VERSION)
        self.assertTrue(self.schema["$schema"].endswith("draft/2020-12/schema"))

    def test_node_types_covered(self):
        self.assertEqual(set(self.schema["$defs"]["node"]["properties"]["type"]["enum"]), NODE_TYPES)

    def test_edge_types_covered(self):
        self.assertEqual(set(self.schema["$defs"]["edge"]["properties"]["type"]["enum"]), set(EDGE_TYPES))

    def test_broken_version(self):
        self.assertIn("SCHEMA_VERSION", self.broken(lambda d: d.update(schema_version="wrong")))

    def test_wrong_purpose(self):
        self.assertIn("PURPOSE_BOUNDARY", self.broken(lambda d: d.update(purpose="PLAY_TO_WORK")))

    def test_duplicate_ids(self):
        self.assertIn("DUPLICATE_NODE_ID", self.broken(lambda d: d["nodes"].append(copy.deepcopy(d["nodes"][0]))))

    def test_dangling(self):
        self.assertIn("DANGLING_EDGE", self.broken(lambda d: d["edges"][0].update(to="missing")))

    def test_self_edge(self):
        self.assertIn("SELF_EDGE", self.broken(lambda d: d["edges"][0].update(to="manifest:demo")))

    def test_wrong_edge_direction(self):
        self.assertIn("INVALID_EDGE_DIRECTION", self.broken(lambda d: d["edges"][4].update(**{"from": "review:demo"})))

    def test_duplicate_edge(self):
        self.assertIn("DUPLICATE_EDGE", self.broken(lambda d: d["edges"].append(copy.deepcopy(d["edges"][0]))))

    def test_unsupported_edge(self):
        self.assertIn("UNKNOWN_EDGE_TYPE", self.broken(lambda d: d["edges"][0].update(type="auto_ratifies")))

    def test_missing_evidence_link(self):
        self.assertIn("CLAIM_LACKS_EVIDENCE_LINK", self.broken(lambda d: d["edges"].pop(4)))

    def test_missing_source_link(self):
        self.assertIn("EVIDENCE_LACKS_SOURCE_LINK", self.broken(lambda d: d["edges"].pop(3)))

    def test_missing_rights(self):
        self.assertIn("RIGHTS_UNKNOWN", self.broken(lambda d: d["nodes"][0]["source"].update(rights="")))

    def test_private_source(self):
        self.assertIn("PRIVATE_OR_UNVERIFIED_SOURCE", self.broken(lambda d: d["nodes"][0]["source"].update(scope="PRIVATE_BRAIN")))

    def test_no_http_plaintext(self):
        self.assertIn("HTTPS_SOURCE_REQUIRED", self.broken(lambda d: d["nodes"][0]["source"].update(url="http://example.org")))

    def test_sha_required(self):
        self.assertIn("SOURCE_HASH_REQUIRED", self.broken(lambda d: d["nodes"][0]["source"].update(sha256="fake")))

    def test_canon_held(self):
        for state in ("RATIFIED", "CANON", "DEPLOYED"):
            with self.subTest(state=state):
                self.assertIn("HOST_ATTESTATION_REQUIRED", self.broken(lambda d: d["nodes"][3].update(state=state)))

    def test_unknown_flag(self):
        self.assertIn("INVALID_FLAGS", self.broken(lambda d: d["nodes"][3].update(flags=["APPROVED"])))

    def test_duplicate_flag(self):
        self.assertIn("DUPLICATE_FLAG", self.broken(lambda d: d["nodes"][3].update(flags=["CONTRADICTED", "CONTRADICTED"])))

    def test_raw_export_status_missing(self):
        self.assertIn("RAW_EXPORT_STATUS_REQUIRED", self.broken(lambda d: d["nodes"][1].pop("raw_export_status")))

    def test_unhashed_export_forced_quarantine(self):
        self.assertIn("INCOMPLETE_RAW_REQUIRES_QUARANTINE", self.broken(lambda d: d["nodes"][1].update(raw_export_status="raw_complete_unhashed")))

    def test_malformed_manifest_flags_are_held_not_exceptions(self):
        # Regression: older implementation did membership on None/int/bool and could crash.
        for raw_status in ("raw_missing", "raw_partial", "raw_complete_unhashed", "raw_source_unavailable"):
            for bad_flags in (None, 0, False, {}, "QUARANTINED"):
                with self.subTest(raw_status=raw_status, bad_flags=repr(bad_flags)):
                    data = copy.deepcopy(self.example)
                    data["nodes"][1]["raw_export_status"] = raw_status
                    data["nodes"][1]["flags"] = bad_flags
                    errors = {e["code"] for e in validate_graph(data)}
                    self.assertIn("INVALID_FLAGS", errors)
                    self.assertIn("INCOMPLETE_RAW_REQUIRES_QUARANTINE", errors)

    def test_quarantined_partial_preserved(self):
        data = copy.deepcopy(self.example)
        data["nodes"][1].update(raw_export_status="raw_partial", flags=["QUARANTINED"])
        self.assertEqual(validate_graph(data), [])

    def test_completed_export_requires_digest(self):
        self.assertIn("COMPLETE_EXPORT_REQUIRES_HASH", self.broken(lambda d: d["nodes"][1].update(manifest_digest_sha256="not-a-digest")))

    def test_completed_export_requires_source_ref(self):
        self.assertIn("INVALID_SOURCE_ROOT_REF", self.broken(lambda d: d["nodes"][1].update(source_root_ref="other:missing")))

    def test_completed_export_requires_receipt_ref(self):
        self.assertIn("INVALID_HASH_RECEIPT_REF", self.broken(lambda d: d["nodes"][1].update(hash_receipt_ref="other:missing")))

    def test_json_schema_requires_raw_export_status(self):
        import importlib.util
        if not importlib.util.find_spec("jsonschema"):
            self.skipTest("optional jsonschema not installed")
        from jsonschema import Draft202012Validator
        Draft202012Validator.check_schema(self.schema)
        validate = Draft202012Validator(self.schema)
        self.assertEqual(list(validate.iter_errors(self.example)), [])
        broken = copy.deepcopy(self.example)
        broken["nodes"][1].pop("raw_export_status")
        self.assertTrue(list(validate.iter_errors(broken)))

    def test_no_network_imports(self):
        source = (ROOT / "tools/validate_evidence_graph.py").read_text()
        for forbidden in ("requests", "urllib.request", "subprocess", "os.system"):
            self.assertNotIn("import " + forbidden, source)


    def test_malformed_node_types_fail_closed(self):
        for value in ([], {}, ["SourceSurface"], True):
            with self.subTest(value=repr(value)):
                self.assertIn("UNKNOWN_NODE_TYPE", self.broken(
                    lambda d: d["nodes"][0].update(type=value)))

    def test_malformed_workflow_states_fail_closed(self):
        for value in ([], {}, ["RAW"]):
            with self.subTest(value=repr(value)):
                self.assertIn("UNKNOWN_STATE", self.broken(
                    lambda d: d["nodes"][3].update(state=value)))

    def test_malformed_raw_export_status_fail_closed(self):
        for value in ([], {}, ["raw_complete_hashed"]):
            with self.subTest(value=repr(value)):
                self.assertIn("RAW_EXPORT_STATUS_REQUIRED", self.broken(
                    lambda d: d["nodes"][1].update(raw_export_status=value)))

    def test_malformed_source_scope_fail_closed(self):
        for value in ([], {}, ["PUBLIC_METADATA"]):
            with self.subTest(value=repr(value)):
                self.assertIn("PRIVATE_OR_UNVERIFIED_SOURCE", self.broken(
                    lambda d: d["nodes"][0]["source"].update(scope=value)))

    def test_malformed_manifest_reference_keys_fail_closed(self):
        for field, code in (("source_root_ref", "INVALID_SOURCE_ROOT_REF"),
                            ("hash_receipt_ref", "INVALID_HASH_RECEIPT_REF")):
            for value in ([], {}, ["source:demo"]):
                with self.subTest(field=field, value=repr(value)):
                    self.assertIn(code, self.broken(
                        lambda d: d["nodes"][1].update({field: value})))

    def test_malformed_edge_fields_fail_closed(self):
        for key in ("from", "to", "type"):
            for value in ([], {}, ["derived_from"], True):
                with self.subTest(key=key, value=repr(value)):
                    self.assertIn("EDGE_FIELDS_MUST_BE_STRINGS", self.broken(
                        lambda d: d["edges"][0].update({key: value})))

    def test_malformed_edge_node_types_do_not_crash(self):
        errors = self.broken(lambda d: d["nodes"][0].update(type=[]))
        self.assertIn("UNKNOWN_NODE_TYPE", errors)
        self.assertIn("INVALID_EDGE_DIRECTION", errors)

    def test_cli_rejects_decoded_duplicate_json_keys(self):
        import io
        import tempfile
        from contextlib import redirect_stdout
        from validate_evidence_graph import main
        cases = (
            '{"purpose":"PLAY_TO_WORK","purpose":"PUBLIC_EVIDENCE_REVIEW"}',
            '{"purpose":"PLAY_TO_WORK","\\u0070urpose":"PUBLIC_EVIDENCE_REVIEW"}',
            '{"source":{"scope":"PRIVATE_BRAIN","scope":"PUBLIC_METADATA"}}',
        )
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "duplicate.json"
            for raw in cases:
                with self.subTest(raw=raw):
                    target.write_text(raw, encoding="utf-8")
                    sink = io.StringIO()
                    with redirect_stdout(sink):
                        rc = main([str(target)])
                    self.assertEqual(rc, 2)
                    self.assertEqual(json.loads(sink.getvalue())["status"], "INVALID")

    def test_cli_still_accepts_the_synthetic_fixture(self):
        import io
        from contextlib import redirect_stdout
        from validate_evidence_graph import main
        sink = io.StringIO()
        with redirect_stdout(sink):
            rc = main([str(ROOT / "examples/evidence_graph_v0_1.synthetic.json")])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(sink.getvalue())["status"], "LOCAL_SHAPE_PASS_NOT_APPROVED")



if __name__ == "__main__":
    unittest.main()