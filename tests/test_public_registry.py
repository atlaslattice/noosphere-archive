"""Offline, synthetic negative tests. No GitHub API, private data or deployment."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from registry.public_registry import validate_catalog, lookup_public_repo, route_public_issue, RegistryError


def record(name: str = "noosphere-archive", repo_id: str = "1"):
    return {
        "repo_full_name": f"atlaslattice/{name}",
        "repository_id": repo_id,
        "url": f"https://github.com/atlaslattice/{name}",
        "visibility": "public",
        "archived": False,
        "default_branch": "main",
        "role_candidate": "core_substrate",
        "sensitivity_name_flag": "UNREVIEWED",
        "readiness": "HOLD_FOR_SOURCE_AND_RIGHTS_REVIEW",
        "provenance_status": "GITHUB_PUBLIC_METADATA_OBSERVED",
        "runtime_status": "NOT_VERIFIED",
        "canon_status": "NOT_CANON",
        "sphere144_tags": [],
        "related_core_repos": [],
        "notes": None,
    }


def catalog():
    return {
        "schema": "atlas.public-repository-registry/v0.1",
        "source": "GitHub repository search through connected account",
        "source_query": "org:atlaslattice",
        "source_pages": [1, 2],
        "observed_date_utc": "2026-11-22",
        "coverage": "PUBLIC_SEARCH_ENUMERATION_ONLY_NOT_FULL_ACCOUNT_OR_PRIVATE_CENSUS",
        "public_only": True,
        "source_page_lengths": [2, 0],
        "records_count": 2,
        "excluded_nonpublic_count": 0,
        "notes": ["Synthetic public-only cut"],
        "records": [record(), record("Atlas-Intelligence", "2")],
    }


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.r = catalog()

    def held(self, reason=None):
        with self.assertRaises(RegistryError) as cm:
            validate_catalog(self.r)
        if reason:
            self.assertEqual(str(cm.exception), reason)

    def test_valid_summary_never_claims_host(self):
        p = validate_catalog(self.r)
        self.assertEqual(p["record_count"], 2)
        self.assertEqual(p["host_or_canon_authority"], "NONE")
        self.assertEqual(p["status"], "PUBLIC_METADATA_STRUCTURALLY_VALID_NOT_LIVE_VERIFIED")
        self.assertFalse(p["private_repo_names_returned"])

    def test_exact_lookup_pointer_only(self):
        x = lookup_public_repo(self.r, "atlaslattice/noosphere-archive")
        self.assertEqual(x["source_status"], "PUBLIC_POINTER_ONLY")
        self.assertEqual(x["rights_to_content_or_deploy"], "NONE")
        self.assertEqual(x["hsn_semantic_mapping"], "UNREVIEWED")

    def test_missing_lookup_never_enumerates_private(self):
        with self.assertRaisesRegex(RegistryError, "PUBLIC_REPO_NOT_IN_SOURCE_CUT"):
            lookup_public_repo(self.r, "atlaslattice/invisible")

    def test_issue_url_only_pointer(self):
        x = route_public_issue(self.r, "https://github.com/atlaslattice/noosphere-archive/issues/4")
        self.assertEqual(x["resource_type"], "ISSUE")
        self.assertEqual(x["resource_number"], 4)
        self.assertFalse(x["can_close_or_merge"])
        self.assertEqual(x["resource_existence"], "NOT_CHECKED")

    def test_pr_url_only_pointer(self):
        x = route_public_issue(self.r, "https://github.com/atlaslattice/noosphere-archive/pull/20")
        self.assertEqual(x["resource_type"], "PR")
        self.assertFalse(x["can_close_or_merge"])

    def test_nonpublic_excluded_count_allowed_without_name(self):
        self.r["excluded_nonpublic_count"] = 1
        self.r["source_page_lengths"] = [3, 0]
        self.assertEqual(validate_catalog(self.r)["excluded_nonpublic_count"], 1)

    def test_private_record_forbidden(self):
        self.r["records"][0]["visibility"] = "private"
        self.held("NONPUBLIC_RECORD")

    def test_ambiguous_visibility_forbidden(self):
        self.r["records"][0]["visibility"] = "internal"
        self.held("NONPUBLIC_RECORD")

    def test_allows_zero_observed_private_only(self):
        self.assertEqual(validate_catalog(self.r)["excluded_nonpublic_count"], 0)

    def test_unknown_row_field_forbidden(self):
        self.r["records"][0]["private_brain_pointer"] = "sensitive"
        self.held("RECORD_FIELDS_UNEXPECTED_OR_MISSING")

    def test_unknown_catalog_field_forbidden(self):
        self.r["secret_source"] = "hidden"
        self.held("CATALOG_FIELDS_UNEXPECTED_OR_MISSING")

    def test_missing_row_field_forbidden(self):
        del self.r["records"][0]["visibility"]
        self.held("RECORD_FIELDS_UNEXPECTED_OR_MISSING")

    def test_count_mismatch(self):
        self.r["records_count"] = 50
        self.held("RECORD_COUNT_MISMATCH")

    def test_false_complete_pages(self):
        self.r["source_page_lengths"] = [2, 1]
        self.held("INCOMPLETE_PAGE_FRONTIER")

    def test_missing_source_page(self):
        self.r["source_pages"] = [1, 3]
        self.held("PAGE_SEQUENCE_INVALID")

    def test_source_page_sum(self):
        self.r["source_page_lengths"] = [1, 0]
        self.held("SOURCE_PAGE_RECONCILIATION_MISMATCH")

    def test_bool_not_accepted_as_count(self):
        self.r["excluded_nonpublic_count"] = False
        self.held("COUNTS_NOT_INTEGER")

    def test_duplicate_repo_name(self):
        self.r["records"][1]["repo_full_name"] = self.r["records"][0]["repo_full_name"]
        self.held("REPO_NAME_INVALID_OR_DUPLICATE")

    def test_duplicate_repo_id(self):
        self.r["records"][1]["repository_id"] = "1"
        self.held("REPO_ID_INVALID_OR_DUPLICATE")

    def test_malicious_repo_name(self):
        self.r["records"][0]["repo_full_name"] = "atlaslattice/../secrets"
        self.held("REPO_NAME_INVALID_OR_DUPLICATE")

    def test_url_homograph(self):
        self.r["records"][0]["url"] = "https://github.com.evil/atlaslattice/noosphere-archive"
        self.held("NON_CANONICAL_PUBLIC_URL")

    def test_url_credentials(self):
        self.r["records"][0]["url"] = "https://user:password@github.com/atlaslattice/noosphere-archive"
        self.held("NON_CANONICAL_PUBLIC_URL")

    def test_url_query_and_fragment(self):
        for end in ("?token=a", "#secret"):
            with self.subTest(end=end):
                temp = copy.deepcopy(self.r)
                temp["records"][0]["url"] += end
                with self.assertRaises(RegistryError):
                    validate_catalog(temp)

    def test_branch_traversal(self):
        self.r["records"][0]["default_branch"] = "../../private"
        self.held("BRANCH_INVALID")

    def test_archived_string_forbidden(self):
        self.r["records"][0]["archived"] = "false"
        self.held("NONPUBLIC_RECORD")

    def test_unreviewed_hsn_link_forbidden(self):
        self.r["records"][0]["sphere144_tags"] = ["H01.S01"]
        self.held("UNREVIEWED_LINKAGE_OR_PRIVATE_CONTENT")

    def test_unreviewed_cross_repo_link_forbidden(self):
        self.r["records"][0]["related_core_repos"] = ["atlaslattice/A2A"]
        self.held("UNREVIEWED_LINKAGE_OR_PRIVATE_CONTENT")

    def test_user_supplied_canon_forbidden(self):
        self.r["records"][0]["canon_status"] = "CANON"
        self.held("AUTHORITY_OVERCLAIM")

    def test_user_supplied_deployed_forbidden(self):
        self.r["records"][0]["runtime_status"] = "DEPLOYED"
        self.held("AUTHORITY_OVERCLAIM")

    def test_release_ready_claim_forbidden(self):
        self.r["records"][0]["readiness"] = "safe_public"
        self.held("READINESS_OVERCLAIM")

    def test_source_status_forbidden(self):
        self.r["records"][0]["provenance_status"] = "HOSTED_VERIFIED"
        self.held("PROVENANCE_OVERCLAIM")

    def test_role_not_authority(self):
        self.r["records"][0]["role_candidate"] = "CANON_ROOT"
        self.held("UNREVIEWED_ROLE_UNSAFE")

    def test_unhashable_role_fails_closed(self):
        self.r["records"][0]["role_candidate"] = ["core_substrate"]
        self.held("UNREVIEWED_ROLE_UNSAFE")

    def test_unhashable_flag_fails_closed(self):
        self.r["records"][0]["sensitivity_name_flag"] = ["UNREVIEWED"]
        self.held("SENSITIVITY_FLAG_UNSAFE")

    def test_nonfinite_number_rejected_by_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "catalog.json"
            p.write_text(json.dumps(self.r).replace('"records_count": 2', '"records_count": NaN'), encoding="utf-8")
            a = subprocess.run([sys.executable, "-m", "registry.public_registry", "--input", str(p)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(a.returncode, 2)
            self.assertIn("NONFINITE_NUMBER", a.stdout)

    def test_invalid_issue_url(self):
        for url in ("https://github.com/atlaslattice/noosphere-archive/pull/0",
                    "https://github.com/atlaslattice/noosphere-archive/pull/1?token=redacted",
                    "https://github.com/evil/noosphere-archive/issues/1",
                    "https://github.com/atlaslattice/noosphere-archive/actions/1"):
            with self.subTest(url=url), self.assertRaises(RegistryError):
                route_public_issue(self.r, url)

    def test_malformed_json_is_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "catalog.json"
            p.write_text('{"bad":', encoding="utf-8")
            a = subprocess.run([sys.executable, "-m", "registry.public_registry", "--input", str(p)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(a.returncode, 2)
            self.assertEqual(json.loads(a.stdout)["status"], "HOLD")

    def test_cli_synthetic(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "catalog.json"
            p.write_text(json.dumps(self.r), encoding="utf-8")
            a = subprocess.run([sys.executable, "-m", "registry.public_registry", "--input", str(p)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(a.returncode, 0, a.stderr + a.stdout)
            self.assertEqual(json.loads(a.stdout)["record_count"], 2)

    def test_cli_exact_issue(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "catalog.json"
            p.write_text(json.dumps(self.r), encoding="utf-8")
            a = subprocess.run([sys.executable, "-m", "registry.public_registry", "--input", str(p), "--issue", "https://github.com/atlaslattice/noosphere-archive/issues/3"], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(a.returncode, 0, a.stderr + a.stdout)
            self.assertFalse(json.loads(a.stdout)["can_close_or_merge"])


if __name__ == "__main__":
    unittest.main()