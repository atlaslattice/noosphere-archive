"""Local candidate-only source-mode and authority classification regression tests."""
import copy
import unittest
from core import validate_ingestion, Sentinel

BASE={'source_root':'synthetic:approved','raw_export_status':'raw_partial'}

class SourceModeBoundaryTests(unittest.TestCase):
    def test_source_class_rejects_nonwork_modes(self):
        for mode in ('Play','Social','Imagine','Dream','Quiet','Rest','Habitat','Brain','Palace','Other','private'):
            with self.subTest(mode=mode):
                v=validate_ingestion(dict(BASE,source_class=mode))
                self.assertEqual(v.state,'QUARANTINED')
                self.assertIn('untrusted_source_mode',v.reasons)

    def test_source_mode_rejects_nonwork_modes(self):
        for mode in ('play','social','imagine','dream','quiet','rest','habitat','brain','palace','PRIVATE'):
            with self.subTest(mode=mode):
                v=validate_ingestion(dict(BASE,source_mode=mode))
                self.assertEqual(v.state,'QUARANTINED')
                self.assertIn('untrusted_source_mode',v.reasons)

    def test_mode_rejects_nonwork_modes(self):
        for mode in ('Brain','Quiet','Play'):
            v=validate_ingestion(dict(BASE,mode=mode))
            self.assertEqual(v.state,'QUARANTINED')

    def test_authority_cannot_self_assert(self):
        for authority in ('CANON','host','HOST_VERIFIED',True,1,[],{},None):
            with self.subTest(authority=repr(authority)):
                v=validate_ingestion(dict(BASE,authority=authority))
                self.assertEqual(v.state,'QUARANTINED')
                self.assertIn('untrusted_authority_claim',v.reasons)

    def test_additional_host_claims_not_self_authorizing(self):
        for field in ('ratified','host_attested','rights_verified'):
            for claim in (True,'yes',1,{},None):
                with self.subTest(field=field,claim=repr(claim)):
                    v=validate_ingestion(dict(BASE,**{field:claim}))
                    self.assertEqual(v.state,'QUARANTINED')
                    self.assertIn('untrusted_authority_claim',v.reasons)

    def test_allowed_annotations_are_not_host_authentication(self):
        for annotation in ({'source_class':'Work'}, {'source_class':'Public'}, {'source_class':'Synthetic'},
                           {'source_mode':'public'}, {'source_mode':'consented_work'}, {'source_mode':'synthetic'},
                           {'mode':'Work'}, {'mode':'work'}, {'authority':'none'},
                           {'ratified':False,'host_attested':False,'rights_verified':False}):
            v=validate_ingestion(dict(BASE,**annotation))
            self.assertEqual(v.state,'SOURCE_REPORTED_ONLY')
            self.assertEqual(v.authority,'none')

    def test_retains_original_rejected_payload_without_mutation(self):
        original=dict(BASE,source_mode='play',authority='CANON',claim_complete=True)
        snapshot=copy.deepcopy(original)
        v=validate_ingestion(original)
        self.assertEqual(v.state,'QUARANTINED')
        self.assertEqual(v.payload,snapshot)
        self.assertEqual(original,snapshot)
        self.assertIn('claim_complete_without_hashed_export',v.reasons)
        self.assertIn('untrusted_source_mode',v.reasons)
        self.assertIn('untrusted_authority_claim',v.reasons)

    def test_sentinel_does_not_grant_any_authority(self):
        p=dict(BASE,kind='IngestionPacket',source_class='Work',canon=False,deployment=False,authority='none',requested_action='PREPARE')
        r=Sentinel().review_packet(p)
        self.assertEqual(r['authority'],'none')
        self.assertTrue(r['allowed'])
        p['source_mode']='play'
        r=Sentinel().review_packet(p)
        self.assertFalse(r['allowed'])

if __name__=='__main__':
 unittest.main()
