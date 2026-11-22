"""Synthetic, no-provider negative controls for source-only continuity."""
from __future__ import annotations
import copy, json, pathlib, subprocess, sys, tempfile, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.digital_continuity import (validate_bundle,validate_contract,prepare_rehydration,
    prepare_fork,canonical_sha256,parse_text,ContinuityHold,BUNDLE_FIELDS,CONTRACT_FIELDS)


def load(name):return json.loads((ROOT/'examples'/name).read_text())

class ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.b=load('example-memory-bundle.redacted.json')
        self.c=load('example-rehydration-contract.redacted.json')
    def hold(self,phrase=None):
        with self.assertRaises(ContinuityHold) as e:validate_bundle(self.b)
        if phrase:self.assertEqual(str(e.exception),phrase)

    def test_synthetic_valid_inert(self):
        r=validate_bundle(self.b)
        self.assertEqual(r['status'],'LOCAL_REVIEWABLE_SOURCE_ONLY')
        self.assertFalse(r['host_verified'] or r['canon'] or r['identity_attested'])
        self.assertFalse(r['source_bodies_returned'])
        self.assertEqual(r['rights_at_return'],'NOT_CHECKED')
    def test_contract_inert(self):
        r=validate_contract(self.c)
        self.assertFalse(r['can_rehydrate_real_identity'] or r['consent_granted'])
    def test_prepare_not_execute(self):
        r=prepare_rehydration(self.b,self.c)
        self.assertEqual(r['model_calls'],0)
        self.assertEqual(r['status'],'PREPARED_NOT_EXECUTED')
        self.assertEqual(r['identity_continuity'],'NOT_PROVEN')
    def test_fork_original_immutable(self):
        old=copy.deepcopy(self.b)
        f=prepare_fork(self.b)
        self.assertEqual(self.b,old)
        self.assertEqual(f['fork']['parent_sha256'],canonical_sha256(old))
        self.assertEqual(f['fork']['fork_status'],'FORK_PREPARED')
        self.assertFalse(f['fork']['parent_authority_inherited'])
        self.assertEqual(validate_bundle(f)['status'],'LOCAL_REVIEWABLE_SOURCE_ONLY')
    def test_persona_refused(self):
        self.b['subject']['kind']='PERSON'
        self.hold('PRIVATE_OR_PERSONA_SUBJECT_HOLD')
    def test_agent_refused(self):
        self.b['subject']['kind']='AGENT'
        self.hold('PRIVATE_OR_PERSONA_SUBJECT_HOLD')
    def test_private_source_refused(self):
        self.b['sources'][0]['ref']='drive://private-file'
        self.hold('NONPUBLIC_OR_UNVERIFIED_REF_HOLD')
    def test_private_scope_refused(self):
        self.b['sources'][0]['scope']='PRIVATE'
        self.hold('SOURCE_AUTHORITY_OR_SCOPE_HOLD')
    def test_body_smuggling_refused(self):
        self.b['sources'][0]['private_body']='secret'
        self.hold('SOURCE_FIELDS_INVALID')
    def test_extra_bundle_field_refused(self):
        self.b['hidden_persona']='person'
        self.hold('BUNDLE_FIELDS_INVALID')
    def test_missing_source_refused(self):
        self.b['sources']=[]
        self.hold('SOURCES_MISSING')
    def test_duplicate_source_refused(self):
        self.b['sources'].append(copy.deepcopy(self.b['sources'][0]))
        self.hold('DUPLICATE_OR_UNHASHED_SOURCE')
    def test_missing_hash_refused(self):
        self.b['sources'][0]['sha256']=''
        self.hold('DUPLICATE_OR_UNHASHED_SOURCE')
    def test_forged_provenance_refused(self):
        self.b['provenance']['author_claim']='HOST_VERIFIED'
        self.hold('OVERCLAIMED_SOURCE_PROVENANCE')
    def test_forged_grant_refused(self):
        self.b['permissions']['return_grant']='APPROVED'
        self.hold('UNATTESTED_PERMISSION_HOLD')
    def test_bogus_release_refused(self):
        self.b['permissions']['public_release_authorized']=True
        self.hold('UNATTESTED_PERMISSION_HOLD')
    def test_private_data_class_refused(self):
        self.b['permissions']['data_class']='PRIVATE_RESTRICTED'
        self.hold('PRIVATE_OR_EXTERNAL_PURPOSE_HOLD')
    def test_wrong_purpose_refused(self):
        self.b['permissions']['allowed_purposes']=['DEPLOY']
        self.hold('PRIVATE_OR_EXTERNAL_PURPOSE_HOLD')
    def test_boolean_epoch_refused(self):
        self.b['permissions']['revocation_epoch']=True
        self.hold('UNATTESTED_PERMISSION_HOLD')
    def test_ontology_drift_refused(self):
        self.b['ontology']['edition']='v1.0'
        self.hold('ONTOLOGY_EDITION_HOLD')
    def test_wrong_ontology_digest_refused(self):
        self.b['ontology']['digest_sha256']='1'*64
        self.hold('ONTOLOGY_EDITION_HOLD')
    def test_duplicate_hsn_refused(self):
        self.b['ontology']['addresses'].append('H02.S01.N01')
        self.hold('ONTOLOGY_ADDRESSES_INVALID')
    def test_invalid_hsn_refused(self):
        self.b['ontology']['addresses']=['H00.S00.N00']
        self.hold('ONTOLOGY_ADDRESS_INVALID')
    def test_no_personhood_false_refused(self):
        self.b['rehydration']['identity_claim']='SAME_PERSON'
        self.hold('IDENTITY_OR_PRIVACY_HOLD')
    def test_private_mode_import_refused(self):
        self.b['rehydration']['private_mode_import']=True
        self.hold('IDENTITY_OR_PRIVACY_HOLD')
    def test_false_human_confirmation_refused(self):
        self.b['rehydration']['human_confirmation_required']=False
        self.hold('IDENTITY_OR_PRIVACY_HOLD')
    def test_no_uncertainty_refused(self):
        self.b['rehydration']['uncertainties']=[]
        self.hold('UNCERTAINTY_MISSING')
    def test_fake_canon_refused(self):
        self.b['status']='CANON'
        self.hold('BUNDLE_SCHEMA_OR_STATUS_MISMATCH')
    def test_parent_grants_refused(self):
        self.b['fork']['parent_authority_inherited']=True
        self.hold('FORK_AUTHORITY_HOLD')
    def test_duplicate_json_keys_refused(self):
        with self.assertRaisesRegex(ContinuityHold,'DUPLICATE_JSON_KEY'):parse_text('{"a":1,"a":2}')
    def test_nan_refused(self):
        with self.assertRaisesRegex(ContinuityHold,'NONFINITE_JSON_NUMBER'):parse_text('{"a":NaN}')
    def test_schema_parity(self):
        b=json.loads((ROOT/'schemas/memory-bundle-v0.schema.json').read_text())
        c=json.loads((ROOT/'schemas/rehydration-contract-v0.schema.json').read_text())
        self.assertEqual(set(b['properties']),BUNDLE_FIELDS)
        self.assertEqual(set(b['required']),BUNDLE_FIELDS)
        self.assertEqual(set(c['properties']),CONTRACT_FIELDS)
        self.assertEqual(set(c['required']),CONTRACT_FIELDS)
        self.assertFalse(b['additionalProperties'] or c['additionalProperties'])
    def test_contract_personhood_promotion_refused(self):
        self.c['identity_claim']='RESURRECTION_CONFIRMED'
        with self.assertRaises(ContinuityHold):validate_contract(self.c)
    def test_contract_human_review_refused(self):
        self.c['human_confirmation_required']=False
        with self.assertRaises(ContinuityHold):validate_contract(self.c)
    def test_contract_rights_refused(self):
        self.c['source_rights_policy']='IGNORE_REVOKE'
        with self.assertRaises(ContinuityHold):validate_contract(self.c)
    def test_cli_default_safe(self):
        a=subprocess.run([sys.executable,'-m','core.digital_continuity'],cwd=ROOT,text=True,capture_output=True)
        self.assertEqual(a.returncode,0,a.stderr+a.stdout)
        self.assertEqual(json.loads(a.stdout)['status'],'PREPARED_NOT_EXECUTED')
    def test_cli_bad_private_holds_without_echo(self):
        with tempfile.TemporaryDirectory() as td:
            f=pathlib.Path(td)/'demo.json';self.b['context_summary']='private_secret_do_not_echo';self.b['subject']['kind']='PERSON'
            f.write_text(json.dumps(self.b))
            a=subprocess.run([sys.executable,'-m','core.digital_continuity','--bundle',str(f)],cwd=ROOT,text=True,capture_output=True)
            self.assertEqual(a.returncode,2)
            self.assertNotIn('private_secret_do_not_echo',a.stdout)
            self.assertEqual(json.loads(a.stdout)['status'],'HOLD')

if __name__=='__main__':unittest.main()