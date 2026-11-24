"""Synthetic source-passport and disclosure checks; no private data or services."""
import copy
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from core.digital_continuity import (
    ContinuityHold, prepare_fork, prepare_rehydration, validate_bundle,
    validate_contract,
)

ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT / 'examples' / name).read_text(encoding='utf-8'))


class ContinuityPassportContractTests(unittest.TestCase):
    def setUp(self):
        self.bundle = fixture('example-memory-bundle.redacted.json')
        self.contract = fixture('example-rehydration-contract.redacted.json')

    def test_real_calendar_dates_preserve_source_only_receipts(self):
        for value in ('0001-01-01', '2000-02-29', '2024-02-29', '9999-12-31'):
            with self.subTest(value=value):
                bundle = copy.deepcopy(self.bundle)
                bundle['recorded_at'] = value
                result = validate_bundle(bundle)
                self.assertEqual(result['status'], 'LOCAL_REVIEWABLE_SOURCE_ONLY')
                self.assertIs(result['host_verified'], False)
                self.assertIs(result['identity_attested'], False)

    def test_impossible_calendar_dates_hold(self):
        for value in ('0000-01-01', '1900-02-29', '2026-02-29',
                      '2026-04-31', '2026-13-01', '2026-00-10', '2026-01-00'):
            with self.subTest(value=value):
                bundle = copy.deepcopy(self.bundle)
                bundle['recorded_at'] = value
                with self.assertRaisesRegex(ContinuityHold, '^DATE_INVALID$'):
                    validate_bundle(bundle)

    def test_dates_require_ascii_fixed_width_and_plain_date_values(self):
        for value in ('２０２６-１１-２２', '٢٠٢٦-١١-٢٢', '2026-1-02',
                      '2026-11-22T00:00:00Z', None, 20261122, True, [], {}):
            with self.subTest(value=value):
                bundle = copy.deepcopy(self.bundle)
                bundle['recorded_at'] = value
                with self.assertRaisesRegex(ContinuityHold, '^DATE_INVALID$'):
                    validate_bundle(bundle)

    def test_invalid_date_cannot_enter_fork_or_rehydration_preparation(self):
        self.bundle['recorded_at'] = '2026-02-29'
        with self.assertRaisesRegex(ContinuityHold, '^DATE_INVALID$'):
            prepare_fork(self.bundle)
        with self.assertRaisesRegex(ContinuityHold, '^DATE_INVALID$'):
            prepare_rehydration(self.bundle, self.contract)

    def test_mandatory_uncertainties_reject_nontext_entries(self):
        for value in (None, False, 17, 0.5, {}, []):
            with self.subTest(value=value):
                contract = copy.deepcopy(self.contract)
                contract['uncertainty_mandatory'] = ['synthetic limitation', value]
                with self.assertRaisesRegex(ContinuityHold, '^CONTRACT_RECONSTRUCTION_HOLD$'):
                    validate_contract(contract)

    def test_mandatory_uncertainties_reject_empty_entries(self):
        for values in ([], [''], ['synthetic limitation', '']):
            with self.subTest(values=values):
                contract = copy.deepcopy(self.contract)
                contract['uncertainty_mandatory'] = values
                with self.assertRaisesRegex(ContinuityHold, '^CONTRACT_RECONSTRUCTION_HOLD$'):
                    validate_contract(contract)

    def test_mandatory_uncertainties_reject_ascii_whitespace_only_entries(self):
        for value in (' ', '\t', '\n', '\r', '\f', '\v', ' \t\n\r\f\v'):
            with self.subTest(value=repr(value)):
                contract = copy.deepcopy(self.contract)
                contract['uncertainty_mandatory'] = [value]
                with self.assertRaisesRegex(ContinuityHold, '^CONTRACT_RECONSTRUCTION_HOLD$'):
                    validate_contract(contract)

    def test_padded_substantive_disclosures_are_preserved(self):
        for value in (' \tSource custody remains unverified.\r\n',
                      ' Édition source non vérifiée. '):
            with self.subTest(value=value):
                contract = copy.deepcopy(self.contract)
                contract['uncertainty_mandatory'] = [value]
                before = copy.deepcopy(contract)
                self.assertEqual(validate_contract(contract)['status'],
                                 'LOCAL_CONTRACT_VALID_NOT_HOSTED')
                self.assertEqual(contract, before)

    def test_valid_text_disclosures_preserve_consent_and_execution_holds(self):
        self.contract['uncertainty_mandatory'] = ['Source custody remains unverified.']
        result = validate_contract(self.contract)
        self.assertIs(result['consent_granted'], False)
        self.assertIs(result['can_rehydrate_real_identity'], False)
        prepared = prepare_rehydration(self.bundle, self.contract)
        self.assertEqual(prepared['status'], 'PREPARED_NOT_EXECUTED')
        self.assertEqual(prepared['model_calls'], 0)
        self.assertIs(prepared['source_bodies_returned'], False)

    def test_invalid_disclosure_blocks_rehydration_preparation(self):
        self.contract['uncertainty_mandatory'] = [None]
        with self.assertRaisesRegex(ContinuityHold, '^CONTRACT_RECONSTRUCTION_HOLD$'):
            prepare_rehydration(self.bundle, self.contract)

    def test_published_schemas_declare_the_same_passport_and_text_contract(self):
        bundle_schema = json.loads((ROOT / 'schemas/memory-bundle-v0.schema.json').read_text())
        date = bundle_schema['properties']['recorded_at']
        self.assertEqual(date['type'], 'string')
        self.assertEqual(date['format'], 'date')
        self.assertIsNotNone(re.fullmatch(date['pattern'], '2024-02-29'))
        self.assertIsNone(re.fullmatch(date['pattern'], '２０２４-０２-２９'))
        contract_schema = json.loads((ROOT / 'schemas/rehydration-contract-v0.schema.json').read_text())
        uncertainty = contract_schema['properties']['uncertainty_mandatory']
        self.assertEqual(uncertainty['minItems'], 1)
        self.assertEqual(uncertainty['items']['type'], 'string')
        self.assertEqual(uncertainty['items']['minLength'], 1)
        pattern = uncertainty['items']['pattern']
        for value in ('', ' \t\n\r\f\v'):
            self.assertIsNone(re.search(pattern, value))
        for value in ('Source custody remains unverified.', ' \tSource text\n'):
            self.assertIsNotNone(re.search(pattern, value))

    def test_cli_returns_structured_holds_for_invalid_date_and_disclosure(self):
        cases = []
        bundle = copy.deepcopy(self.bundle); bundle['recorded_at'] = '2026-04-31'
        cases.append((bundle, self.contract, 'DATE_INVALID'))
        contract = copy.deepcopy(self.contract); contract['uncertainty_mandatory'] = [None]
        cases.append((self.bundle, contract, 'CONTRACT_RECONSTRUCTION_HOLD'))
        for bundle, contract, reason in cases:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as temp:
                bundle_path = Path(temp) / 'synthetic-bundle.json'
                contract_path = Path(temp) / 'synthetic-contract.json'
                bundle_path.write_text(json.dumps(bundle), encoding='utf-8')
                contract_path.write_text(json.dumps(contract), encoding='utf-8')
                run = subprocess.run([sys.executable, '-m', 'core.digital_continuity',
                    '--bundle', str(bundle_path), '--contract', str(contract_path)],
                    cwd=ROOT, capture_output=True, text=True, timeout=10)
                self.assertEqual(run.returncode, 2, run.stderr)
                self.assertEqual(run.stderr, '')
                self.assertEqual(json.loads(run.stdout),
                    {'status': 'HOLD', 'reason': 'ContinuityHold: ' + reason})
                self.assertNotIn(str(temp), run.stdout)


if __name__ == '__main__':
    unittest.main()
