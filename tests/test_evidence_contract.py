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


if __name__ == "__main__":
    unittest.main()