"""Noosphere public metadata snapshot dates; synthetic-only independent acceptance."""
from __future__ import annotations
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from registry.public_registry import (SCHEMA,SOURCE_QUERY,COVERAGE,RegistryError,
    validate_catalog,load_catalog_text,lookup_public_repo,route_public_issue)


def synthetic_catalog(date='2026-11-22'):
    """Fictional public metadata only, not a private or live repo inventory."""
    name='atlaslattice/synthetic-fixture-repo'
    row={
        'repo_full_name':name,'repository_id':'1728',
        'url':'https://github.com/atlaslattice/synthetic-fixture-repo',
        'visibility':'public','archived':False,'default_branch':'main',
        'role_candidate':'unclassified_public_repo',
        'sensitivity_name_flag':'UNREVIEWED',
        'readiness':'HOLD_FOR_SOURCE_AND_RIGHTS_REVIEW',
        'provenance_status':'GITHUB_PUBLIC_METADATA_OBSERVED',
        'runtime_status':'NOT_VERIFIED','canon_status':'NOT_CANON',
        'sphere144_tags':[],'related_core_repos':[],'notes':None,
    }
    return dict(schema=SCHEMA,source='synthetic:public-metadata-fixture',
        source_query=SOURCE_QUERY,source_pages=[1,2],
        observed_date_utc=date,coverage=COVERAGE,public_only=True,
        source_page_lengths=[1,0],records_count=1,
        excluded_nonpublic_count=0,notes=['synthetic only'],records=[row])

class SnapshotDateTests(unittest.TestCase):
    def check_hold(self, date):
        doc=synthetic_catalog(date)
        with self.assertRaisesRegex(RegistryError,'MISSING_SNAPSHOT_PASSPORT'):
            validate_catalog(doc)
    def test_reject_impossible_february(self): self.check_hold('2026-02-29')
    def test_reject_month_13(self): self.check_hold('2026-13-01')
    def test_reject_zero_month(self): self.check_hold('2026-00-10')
    def test_reject_april_31(self): self.check_hold('2026-04-31')
    def test_valid_leap_date(self): self.assertEqual(validate_catalog(synthetic_catalog('2024-02-29'))['observed_date_utc'],'2024-02-29')
    def test_current_public_snapshot(self): self.assertEqual(validate_catalog(synthetic_catalog())['record_count'],1)
    def test_invalid_year_type(self): self.check_hold(20261122)
    def test_leading_zero_bizarre_date(self): self.check_hold('0000-01-01')
    def test_offline_lookup_preserves_public_pointer_not_rights(self):
        response=lookup_public_repo(synthetic_catalog(),'atlaslattice/synthetic-fixture-repo')
        self.assertEqual(response['rights_to_content_or_deploy'],'NONE')
    def test_issue_pointer_cannot_close(self):
        r=route_public_issue(synthetic_catalog(),'https://github.com/atlaslattice/synthetic-fixture-repo/issues/123')
        self.assertIs(r['can_close_or_merge'],False)
    def test_json_round_trip_valid(self):
        doc=synthetic_catalog()
        self.assertEqual(validate_catalog(load_catalog_text(json.dumps(doc)))['record_count'],1)
    def test_cli_invalid_date_holds(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'synthetic_public_metadata.json'
            path.write_text(json.dumps(synthetic_catalog('2026-02-29')),encoding='utf-8')
            run=subprocess.run([sys.executable,'-m','registry.public_registry','--input',str(path)],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,check=False)
            self.assertEqual(run.returncode,2)
            self.assertIn('MISSING_SNAPSHOT_PASSPORT',run.stdout)

if __name__=='__main__': unittest.main(verbosity=2)
