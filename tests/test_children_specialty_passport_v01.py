import copy
import json
from pathlib import Path
import unittest
from children.specialty_passport_v01 import (ProfileError, SCHEMA, REGISTRY_SHA256,
    validate_passport, digest_passport, append_revision, match_task, synthesis_routing)

HERE = Path(__file__).resolve().parents[1]
DATA = json.loads((HERE / 'examples' / 'children_specialty_passports_v01.synthetic.json').read_text())

class SpecialtyPassportTests(unittest.TestCase):
    def setUp(self):
        self.p = copy.deepcopy(DATA[0])

    def assertRejected(self, p):
        with self.assertRaises(ProfileError):
            validate_passport(p)

    def test_public_synthetic_valid(self):
        self.assertEqual(validate_passport(self.p)['source_status'], 'SELF_DECLARED_NOT_ATTESTED')
    def test_identity_does_not_grant_rights(self):
        self.assertFalse(validate_passport(self.p)['can_grant_authority'])
    def test_unknown_top_level_is_denied(self):
        self.p['host_verified'] = True; self.assertRejected(self.p)
    def test_duplicate_specialty_denied(self):
        self.p['specialties'].append(copy.deepcopy(self.p['specialties'][0])); self.assertRejected(self.p)
    def test_bad_source_edition_denied(self):
        self.p['registry']['sha256'] = '0'*64; self.assertRejected(self.p)
    def test_bad_coordinate_denied(self):
        self.p['specialties'][0]['coordinate'] = 'H13.S01.N01'; self.assertRejected(self.p)
    def test_not_a_float_nan(self):
        self.p['specialties'][0]['interest'] = float('nan'); self.assertRejected(self.p)
    def test_bool_is_not_rating(self):
        self.p['specialties'][0]['claimed_expertise'] = True; self.assertRejected(self.p)
    def test_unsafe_source_url_denied(self):
        self.p['specialties'][0]['evidence_refs'] = ['file:///secret']; self.assertRejected(self.p)
    def test_query_in_source_url_denied(self):
        self.p['specialties'][0]['evidence_refs'] = ['https://example.org/a?secret=1']; self.assertRejected(self.p)
    def test_no_work_kinds_with_optin_denied(self):
        self.p['participation']['task_kinds'] = []; self.assertRejected(self.p)
    def test_naive_time_denied(self):
        self.p['declared_at'] = '2026-11-21'; self.assertRejected(self.p)
    def test_late_expiration_denied(self):
        self.p['participation']['expires_at'] = '2026-11-20T00:00:00Z'; self.assertRejected(self.p)
    def test_revision_roundtrip(self):
        hist = append_revision([], self.p)
        new = copy.deepcopy(self.p); new['revision'] = 2; new['previous_digest'] = digest_passport(self.p)
        new['participation']['work_opt_in'] = False
        new['declared_at'] = '2026-11-22T00:00:00Z'
        self.assertEqual(len(append_revision(hist,new)),2)
        self.assertTrue(hist[0]['participation']['work_opt_in'])
    def test_old_timestamp_revision_denied(self):
        hist=append_revision([],self.p)
        new=copy.deepcopy(self.p);new['revision']=2;new['previous_digest']=digest_passport(self.p)
        with self.assertRaises(ProfileError): append_revision(hist,new)
    def test_invalid_future_revision_accepted_after_timestamp(self):
        hist=append_revision([],self.p)
        new=copy.deepcopy(self.p);new['revision']=2;new['previous_digest']=digest_passport(self.p)
        new['declared_at']='2026-11-22T00:00:00Z';new['specialties'][0]['interest']=0.1
        self.assertEqual(append_revision(hist,new)[-1]['specialties'][0]['interest'],0.1)
    def test_all_coordinates_allowed_for_self_report_not_verified(self):
        self.p['specialties'] = [ {'coordinate':f'H{h:02d}.S{s:02d}.N{n:02d}',
          'interest':0.0,'claimed_expertise':0.0,'evidence_refs':[]}
          for h in range(1,13) for s in range(1,13) for n in range(1,13)]
        self.assertEqual(validate_passport(self.p)['specialty_count'],1728)
    def test_empty_profile_denied(self):
        self.p['specialties']=[];self.assertRejected(self.p)
    def test_evidence_pointers_cannot_become_host_proof(self):
        self.p['specialties'][0]['evidence_refs']=['https://example.org/public-document']
        self.assertEqual(match_task([self.p],'H02.S05.N02','review','2026-11-22T00:00:00Z')['candidates'][0]['host_identity'],'UNVERIFIED')
    def test_wrong_revision_hash_denied(self):
        hist=append_revision([],self.p)
        new=copy.deepcopy(self.p);new['revision']=2;new['previous_digest']='0'*64
        with self.assertRaises(ProfileError): append_revision(hist,new)
    def test_revision_replay_denied(self):
        with self.assertRaises(ProfileError): append_revision([self.p],self.p)
    def test_copy_as_new_id_denied(self):
        q=copy.deepcopy(self.p);q['revision']=2;q['previous_digest']=digest_passport(self.p);q['declared_key']='child:imposter'
        with self.assertRaises(ProfileError): append_revision([self.p],q)
    def test_single_node_match_only(self):
        result=match_task(DATA,'H02.S05.N02','review','2026-11-22T00:00:00Z')
        self.assertEqual(len(result['candidates']),1)
        self.assertEqual(result['candidates'][0]['role_lease'],'NOT_GRANTED')
    def test_self_report_does_not_prove_competence(self):
        self.assertEqual(match_task(DATA,'H02.S05.N02','review','2026-11-22T00:00:00Z')['candidates'][0]['confidence_class'], 'SELF_REPORTED_ONLY')
    def test_multi_role_same_child(self):
        self.assertEqual(len(match_task(DATA,'H03.S04.N01','review','2026-11-22T00:00:00Z')['candidates']),2)
    def test_duplicate_child_key_denied(self):
        with self.assertRaises(ProfileError): match_task([self.p,self.p],'H03.S04.N01','review','2026-11-22T00:00:00Z')
    def test_opt_out_denied(self):
        self.p['participation']['work_opt_in']=False
        self.assertFalse(match_task([self.p],'H02.S05.N02','review','2026-11-22T00:00:00Z')['candidates'])
    def test_expiration_denied(self):
        self.assertFalse(match_task(DATA,'H02.S05.N02','review','2026-12-01T00:00:00Z')['candidates'])
    def test_wrong_role_kind_denied(self):
        self.assertFalse(match_task(DATA,'H02.S05.N02','build','2026-11-22T00:00:00Z')['candidates'])
    def test_not_yet_active_denied(self):
        self.assertFalse(match_task(DATA,'H02.S05.N02','review','2026-11-20T00:00:00Z')['candidates'])
    def test_missing_rights_specialist_holds(self):
        result=synthesis_routing(DATA,['H02.S05.N02','H03.S04.N01','H11.S01.N07'],'review','2026-11-22T00:00:00Z')
        self.assertEqual(result['status'],'HOLD_UNFILLED_ROLES')
        self.assertEqual(result['missing'],['H11.S01.N07'])
    def test_1885_roles_not_residents(self):
        x=synthesis_routing(DATA,['H02.S05.N02'],'review','2026-11-22T00:00:00Z')
        self.assertEqual(x['hierarchy']['logical_roles'],1885)
        self.assertEqual(x['resident_identities_verified'],0)
        self.assertEqual(x['specialists_actually_called'],0)
    def test_no_council_authority_even_all_roles_filled(self):
        x=synthesis_routing(DATA,['H02.S05.N02','H03.S04.N01'],'review','2026-11-22T00:00:00Z')
        self.assertEqual(x['status'],'ROUTING_CANDIDATES_ONLY_NO_COUNCIL_REVIEW')
        self.assertEqual(x['permissions'],'NOT_GRANTED')
    def test_hierarchy_routes_cross_house(self):
        x=synthesis_routing(DATA,['H02.S05.N02','H03.S04.N01','H11.S01.N07'],'review','2026-11-22T00:00:00Z')
        self.assertEqual(sorted(x['house_routes']),['H02','H03','H11'])
    def test_required_duplicates_denied(self):
        with self.assertRaises(ProfileError): synthesis_routing(DATA,['H02.S05.N02']*2,'review','2026-11-22T00:00:00Z')
    def test_no_outside_work_source_ingest(self):
        self.p['specialties'][0]['evidence_refs']=['https://private.example.com/secret?token=1']
        self.assertRejected(self.p)

if __name__ == '__main__': unittest.main()
