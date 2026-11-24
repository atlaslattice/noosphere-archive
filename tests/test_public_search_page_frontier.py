"""GitHub search-page boundary regressions; public metadata only.

The frozen registry is a dated source cut, NOT a live privacy/rights census.
No network requests, private repository names, or external providers.
"""
import copy
import json
import unittest
from pathlib import Path

from registry.public_registry import RegistryError, validate_catalog


class SearchPageFrontierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(__file__).resolve().parents[1] / "registry" / "public_repo_inventory_2026-11-22.json"
        cls.snapshot = json.loads(source.read_text(encoding="utf-8"))

    def assert_page_hold(self, page_lengths):
        candidate = copy.deepcopy(self.snapshot)
        candidate["source_pages"] = list(range(1, len(page_lengths) + 1))
        candidate["source_page_lengths"] = page_lengths
        # Keep original 272 records + one omitted nonpublic search result,
        # so a rejection is attributable to the page frontier, not totals.
        self.assertEqual(sum(page_lengths),
                         candidate["records_count"] + candidate["excluded_nonpublic_count"])
        with self.assertRaisesRegex(RegistryError, "^PAGE_LENGTH_INVALID$"):
            validate_catalog(candidate)

    def test_original_recorded_source_cut_still_valid(self):
        result = validate_catalog(self.snapshot)
        self.assertEqual(result["source_page_lengths"], [100, 100, 73, 0])
        self.assertEqual(result["record_count"], 272)
        self.assertEqual(result["host_or_canon_authority"], "NONE")

    def test_reject_impossible_101_result_page(self):
        self.assert_page_hold([101, 100, 72, 0])

    def test_reject_fake_273_result_single_page(self):
        self.assert_page_hold([273, 0])

    def test_reject_nonfinal_empty_first_page(self):
        self.assert_page_hold([0, 100, 100, 73, 0])

    def test_reject_nonfinal_empty_middle_page(self):
        self.assert_page_hold([100, 0, 100, 73, 0])

    def test_reject_empty_page_followed_by_more_results(self):
        self.assert_page_hold([100, 100, 0, 73, 0])


if __name__ == "__main__":
    unittest.main()
