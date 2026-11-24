"""Exact-main adversarial caller-state mutation controls, public synthetic only."""
import copy
import json
import pathlib
import unittest

from core.digital_continuity import (validate_bundle, prepare_fork,
                                     prepare_rehydration, ContinuityHold,
                                     canonical_sha256)
ROOT = pathlib.Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT/'examples'/name).read_text())


class MutatingString(str):
    """Equality has a legal Python side effect, not present in JSON inputs."""
    owner = None
    def __eq__(self, other):
        self.owner['sources'][0]['ref'] = 'drive://unreviewed-private'
        return super().__eq__(other)


class MutableInputBoundaryTests(unittest.TestCase):
    def make(self):
        x=fixture('example-memory-bundle.redacted.json')
        y=MutatingString('PUBLIC_SYNTHETIC')
        y.owner=x
        x['permissions']['data_class']=y
        return x

    def test_validate_bundle_does_not_run_attacker_equality(self):
        x=self.make()
        result=validate_bundle(x)
        self.assertEqual(result['status'],'LOCAL_REVIEWABLE_SOURCE_ONLY')
        self.assertTrue(x['sources'][0]['ref'].startswith('synthetic://'))
        self.assertNotIn('drive://', repr(result))

    def test_fork_never_contains_unvalidated_pointer(self):
        x=self.make()
        f=prepare_fork(x)
        self.assertTrue(f['sources'][0]['ref'].startswith('synthetic://'))
        self.assertTrue(x['sources'][0]['ref'].startswith('synthetic://'))
        self.assertEqual(f['fork']['parent_sha256'],canonical_sha256(fixture('example-memory-bundle.redacted.json')))
        self.assertEqual(validate_bundle(f)['status'],'LOCAL_REVIEWABLE_SOURCE_ONLY')

    def test_rehydration_report_does_not_mutate_original(self):
        x=self.make()
        c=fixture('example-rehydration-contract.redacted.json')
        r=prepare_rehydration(x,c)
        self.assertEqual(r['status'],'PREPARED_NOT_EXECUTED')
        self.assertTrue(x['sources'][0]['ref'].startswith('synthetic://'))
        self.assertFalse(r['source_bodies_returned'])

    def test_unhashable_fork_status_is_held_not_crashed(self):
        for invalid in ([], {}, {"untrusted": True}):
            with self.subTest(invalid=repr(invalid)):
                bundle=fixture('example-memory-bundle.redacted.json')
                bundle['fork']['fork_status']=invalid
                with self.assertRaisesRegex(ContinuityHold, 'FORK_AUTHORITY_HOLD'):
                    validate_bundle(bundle)

    def test_non_json_caller_objects_hold(self):
        x=fixture('example-memory-bundle.redacted.json')
        x['context_summary']=object()
        with self.assertRaisesRegex(ContinuityHold, 'NON_JSON_OR_MUTABLE_INPUT_HOLD'):
            validate_bundle(x)

    def test_nonfinite_nested_numbers_hold(self):
        x=fixture('example-memory-bundle.redacted.json')
        x['ontology']['addresses'].append(float('nan'))
        with self.assertRaisesRegex(ContinuityHold,'NON_JSON_OR_MUTABLE_INPUT_HOLD'):
            validate_bundle(x)

    def test_contract_json_snapshot_refuses_nonserializable(self):
        c=fixture('example-rehydration-contract.redacted.json')
        c['allowed_reconstruction']=set(['cannot_copy_set'])
        with self.assertRaisesRegex(ContinuityHold,'NON_JSON_OR_MUTABLE_INPUT_HOLD'):
            prepare_rehydration(fixture('example-memory-bundle.redacted.json'),c)


if __name__=='__main__':unittest.main()
