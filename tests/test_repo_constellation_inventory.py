"""Executable source-only checks: one 100-row public metadata snapshot, NOT full org coverage."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "registry"
RECORD_FIELDS = {
    "repo_full_name", "url", "visibility", "default_branch", "archived",
    "role", "risk_tier", "public_readiness", "provenance_status",
    "runtime_status", "canon_status", "sphere144_tags",
    "related_core_repos", "evidence_scope", "heuristic_role_unreviewed",
}
ROOT_FIELDS = {
    "schema", "collection", "observed_at_date", "source", "scope",
    "snapshot_complete_for_all_org_repos", "unobserved_repositories",
    "privacy", "authority", "canon", "deployment", "records",
}
NAME = re.compile(r"^atlaslattice/[A-Za-z0-9._-]+$")


class RegistryEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "atlas-repo-inventory-2026-11-22.json").read_text(encoding="utf-8"))
        cls.schema = json.loads((ROOT / "atlas-repo-record.schema.json").read_text(encoding="utf-8"))

    def test_no_claim_of_complete_inventory_or_release(self):
        d = self.data
        self.assertEqual(set(d), ROOT_FIELDS)
        self.assertEqual(d["schema"], "atlas.repo-constellation-inventory/v0.1")
        self.assertEqual(d["collection"], "atlaslattice")
        self.assertEqual(d["source"], "CONNECTED_GITHUB_METADATA")
        self.assertEqual(d["scope"], "FIRST_ACCESSIBLE_PAGE_UP_TO_100")
        self.assertIs(d["snapshot_complete_for_all_org_repos"], False)
        self.assertEqual(d["unobserved_repositories"], "UNKNOWN")
        self.assertEqual(d["privacy"], "PUBLIC_REPOSITORY_METADATA_ONLY")
        self.assertEqual((d["authority"], d["canon"], d["deployment"]),
                         ("NONE", "NOT_CANON", "NONE"))

    def test_records_unique_and_urls_match_names_exactly(self):
        records = self.data["records"]
        self.assertEqual(len(records), 100)  # historical page size, NOT full organization count
        seen = set()
        for n, row in enumerate(records):
            with self.subTest(index=n):
                self.assertEqual(set(row), RECORD_FIELDS)
                name = row["repo_full_name"]
                self.assertIs(type(name), str)
                self.assertRegex(name, NAME)
                self.assertNotIn(name, seen)
                seen.add(name)
                self.assertEqual(row["url"], "https://github.com/" + name)
                self.assertIs(type(row["archived"]), bool)
                self.assertIs(type(row["heuristic_role_unreviewed"]), bool)
                self.assertIs(row["heuristic_role_unreviewed"], True)
                self.assertTrue(type(row["default_branch"]) is str and row["default_branch"])

    def test_all_roles_remain_unreviewed_nonruntime_candidates(self):
        for n, row in enumerate(self.data["records"]):
            with self.subTest(index=n):
                self.assertEqual(row["visibility"], "public")
                self.assertIn(row["role"], {"core_substrate", "archive", "domain_research", "public_seed"})
                self.assertIn(row["risk_tier"], {"medium", "high"})
                self.assertIn(row["public_readiness"], {"HOLD_FOR_REVIEW", "NEEDS_CONTEXT_REVIEW"})
                self.assertEqual(row["provenance_status"], "INVENTORIED_METADATA_ONLY")
                self.assertEqual(row["runtime_status"], "UNVERIFIED")
                self.assertEqual(row["canon_status"], "NOT_CANON")
                self.assertEqual(row["evidence_scope"], "GITHUB_REPOSITORY_METADATA_ONLY")
                for key in ("sphere144_tags", "related_core_repos"):
                    self.assertIs(type(row[key]), list)
                    self.assertTrue(all(type(x) is str for x in row[key]))

    def test_schema_fields_and_optional_jsonschema(self):
        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(set(self.schema["required"]), RECORD_FIELDS)
        self.assertEqual(set(self.schema["properties"]), RECORD_FIELDS)
        self.assertIs(self.schema["additionalProperties"], False)
        try:
            import jsonschema
        except ImportError:
            return  # stdlib structural assertions still execute
        validator = jsonschema.Draft202012Validator(self.schema)
        for row in self.data["records"]:
            self.assertEqual(list(validator.iter_errors(row)), [])


if __name__ == "__main__":
    unittest.main()
