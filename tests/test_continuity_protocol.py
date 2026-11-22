import copy
import json
import math
import unittest
from pathlib import Path
from continuity import (SCHEMA,CONTRACT,ContinuityError,digest,seal_bundle,verify_bundle,
                        prepare_rehydration,fork_bundle)
ROOT=Path(__file__).resolve().parents[1]

def read(name):return json.loads((ROOT/name).read_text())

class ContinuityProtocolTests(unittest.TestCase):
    def setUp(self):
        self.b=read('examples/example-memory-bundle.redacted.json')
        self.c=read('examples/example-rehydration-contract.json')
        self.raw=copy.deepcopy(self.b);self.raw.pop('integrity')

    def bad(self,mutate,code=None):
        b=copy.deepcopy(self.raw);mutate(b)
        with self.assertRaises(ContinuityError) as e:seal_bundle(b)
        if code:self.assertEqual(str(e.exception),code)

    def test_bundle_valid_and_digest(self):
        out=verify_bundle(self.b)
        self.assertEqual(out['status'],'VERIFIED_STRUCTURE_ONLY')
        self.assertFalse(out['identity_attested'])
        self.assertFalse(out['host_release_authorized'])
        self.assertEqual(out['digest'],self.b['integrity']['digest'])
    def test_deterministic_seal(self):self.assertEqual(seal_bundle(self.raw),self.b)
    def test_signature_not_claimed(self):self.assertEqual(self.b['integrity']['algorithm'],'SHA-256-JSON-PYTHON-LOCAL')
    def test_unknown_keys_hold(self):self.bad(lambda b:b.update(person_id='actual-person'),'BUNDLE_SHAPE_HOLD')
    def test_nested_private_key_hold(self):self.bad(lambda b:b['sources'][0].update(raw_transcript='PRIVATE'),'SOURCE_SHAPE_HOLD')
    def test_private_class_hold(self):self.bad(lambda b:b.update(privacy_class='PRIVATE'),'PRIVATE_OR_UNREVIEWED_SOURCE_HOLD')
    def test_unratified_authority_only(self):self.bad(lambda b:b.update(authority='CANON'),'SELF_AUTHORIZATION_HOLD')
    def test_bool_version_hold(self):self.bad(lambda b:b.update(version=True),'BUNDLE_ID_OR_VERSION_HOLD')
    def test_negative_version_hold(self):self.bad(lambda b:b.update(version=-1),'BUNDLE_ID_OR_VERSION_HOLD')
    def test_invalid_time_hold(self):self.bad(lambda b:b.update(created_at='yesterday'),'UNPINNED_CREATION_TIME')
    def test_missing_registry_hold(self):self.bad(lambda b:b['ontology'].pop('source_sha256'),'ONTOLOGY_EDITION_HOLD')
    def test_registry_content_hold(self):self.bad(lambda b:b['ontology'].update(source_sha256='f'*10),'ONTOLOGY_SOURCE_HOLD')
    def test_source_missing_hold(self):self.bad(lambda b:b.update(sources=[]),'SOURCE_COUNT_HOLD')
    def test_private_source_origin_hold(self):self.bad(lambda b:b['sources'][0].update(origin='Play'),'SOURCE_RIGHTS_OR_COMPLETENESS_HOLD')
    def test_source_incomplete_hold(self):self.bad(lambda b:b['sources'][0].update(export_status='raw_partial'),'SOURCE_RIGHTS_OR_COMPLETENESS_HOLD')
    def test_source_without_permission_hold(self):self.bad(lambda b:b['sources'][0].update(permission='REVOKED'),'SOURCE_RIGHTS_OR_COMPLETENESS_HOLD')
    def test_license_missing_hold(self):self.bad(lambda b:b['sources'][0].update(license=''),'LICENSE_UNDECLARED_HOLD')
    def test_duplicate_sources_hold(self):self.bad(lambda b:b['sources'].append(copy.deepcopy(b['sources'][0])),'SOURCE_ID_COLLISION_HOLD')
    def test_claim_missing_reference_hold(self):self.bad(lambda b:b['claims'][0].update(source_ids=['s-missing']),'CLAIM_EVIDENCE_HOLD')
    def test_duplicate_claim_ids_hold(self):self.bad(lambda b:b['claims'].append(copy.deepcopy(b['claims'][0])),'CLAIM_ID_COLLISION_HOLD')
    def test_duplicate_claim_refs_hold(self):self.bad(lambda b:b['claims'][0].update(source_ids=['s-demo-01','s-demo-01']),'DUPLICATED_SOURCE_ID_HOLD')
    def test_status_invented_hold(self):self.bad(lambda b:b['claims'][0].update(status='CONFIRMED_CANON'),'CLAIM_EVIDENCE_HOLD')
    def test_unhashable_claim_status_hold(self):
        for invalid in ([], {}, 42, None, True):
            with self.subTest(value=repr(invalid)):
                self.bad(lambda b:b['claims'][0].update(status=invalid),'CLAIM_EVIDENCE_HOLD')
    def test_unhashable_reference_hold(self):
        for invalid in ([['s-demo-01']], [{}], [False], [None]):
            with self.subTest(value=repr(invalid)):
                self.bad(lambda b:b['claims'][0].update(source_ids=invalid),'CLAIM_EVIDENCE_HOLD')
    def test_hsn_address_not_autotruth(self):
        b=copy.deepcopy(self.b)
        self.assertIn('example label only',b['profile']['ontology_tags'][0])
        self.assertEqual(verify_bundle(b)['authority'],'NONE')
    def test_no_raw_message_text_field_allowed(self):
        self.bad(lambda b:b['profile'].update(raw_memory='secret'),'PROFILE_SHAPE_HOLD')
    def test_no_private_dream_text_field_allowed(self):
        self.bad(lambda b:b['sources'][0].update(dream_text='thoughts'),'SOURCE_SHAPE_HOLD')
    def test_unjustified_persona_claim_hold(self):self.bad(lambda b:b['claims'][0].pop('does_not_prove'),'CLAIM_SHAPE_HOLD')
    def test_tamper_detected(self):
        b=copy.deepcopy(self.b);b['claims'][0]['statement']='Tampered statement'
        with self.assertRaisesRegex(ContinuityError,'INTEGRITY_TAMPER_HOLD'):verify_bundle(b)
    def test_non_json_rejected(self):
        with self.assertRaisesRegex(ContinuityError,'NOT_CANONICAL_JSON'):seal_bundle({'x':{1,2}})
    def test_nonfinite_rejected(self):
        with self.assertRaisesRegex(ContinuityError,'NOT_CANONICAL_JSON'):digest({'x':float('nan')})
    def test_rehydration_prepared_not_executed(self):
        r=prepare_rehydration(self.b,self.c)
        self.assertEqual(r['status'],'PREPARED_NOT_EXECUTED')
        self.assertFalse(r['model_woken'])
        self.assertFalse(r['private_source_imported'])
        self.assertFalse(r['identity_attested'])
    def test_wrong_bundle_digest_hold(self):
        c=copy.deepcopy(self.c);c['source_digest']='f'*64
        with self.assertRaisesRegex(ContinuityError,'CONTRACT_SOURCE_DRIFT_HOLD'):prepare_rehydration(self.b,c)
    def test_contract_claims_identity_hold(self):
        c=copy.deepcopy(self.c);c['identity_claim']='CONTINUOUS_CONSCIOUSNESS'
        with self.assertRaisesRegex(ContinuityError,'IMPERSONATION_OR_AUTHORITY_HOLD'):prepare_rehydration(self.b,c)
    def test_contract_autonomous_hold(self):
        c=copy.deepcopy(self.c);c['allowed']='AUTONOMOUS_AGENT'
        with self.assertRaisesRegex(ContinuityError,'IMPERSONATION_OR_AUTHORITY_HOLD'):prepare_rehydration(self.b,c)
    def test_contract_requires_review_hold(self):
        c=copy.deepcopy(self.c);c['requires_human_review']=False
        with self.assertRaisesRegex(ContinuityError,'IMPERSONATION_OR_AUTHORITY_HOLD'):prepare_rehydration(self.b,c)
    def test_fork_retains_parent_and_source(self):
        p=copy.deepcopy(self.b);f=fork_bundle(p,'demo.synthetic.fork-002','2026-11-22T20:00:00Z')
        self.assertEqual(f['parent'],{'bundle_id':p['bundle_id'],'digest':p['integrity']['digest']})
        self.assertEqual(f['sources'],p['sources'])
        self.assertEqual(f['version'],p['version']+1)
        self.assertNotEqual(f['integrity']['digest'],p['integrity']['digest'])
        self.assertEqual(verify_bundle(f)['status'],'VERIFIED_STRUCTURE_ONLY')
        self.assertEqual(p,self.b)
    def test_fork_collision_hold(self):
        with self.assertRaisesRegex(ContinuityError,'FORK_ID_COLLISION_HOLD'):
            fork_bundle(self.b,self.b['bundle_id'],'2026-11-22T20:00:00Z')
    def test_parent_cycle_hold(self):
        self.bad(lambda b:b.update(parent={'bundle_id':b['bundle_id'],'digest':'a'*64}),'PARENT_IDENTITY_HOLD')
    def test_privacy_mode_no_relax_by_hsn_label(self):
        self.bad(lambda b:b.update(privacy_class='PLAY'), 'PRIVATE_OR_UNREVIEWED_SOURCE_HOLD')
    def test_schema_validator_if_installed(self):
        try:import jsonschema
        except ImportError:self.skipTest('optional jsonschema not installed')
        schema=read('schemas/memory-bundle-v0.schema.json')
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.validate(self.b,schema)
        contract_schema=read('schemas/rehydration-contract-v0.schema.json')
        jsonschema.Draft202012Validator.check_schema(contract_schema)
        jsonschema.validate(self.c,contract_schema)
        with self.assertRaises(jsonschema.ValidationError):jsonschema.validate(dict(self.b,privacy_class='PRIVATE'),schema)

if __name__=='__main__':unittest.main()
