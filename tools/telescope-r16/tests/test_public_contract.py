"""Source-independent synthetic regression suite for public PR / CI."""
from pathlib import Path
import sys,copy,unittest,hashlib,math
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from telescope_engine import CandidateIndex,guard_packet,tokenize,digest,STAGES,REGISTRY_SHA
from trace_pareto import synthetic_traceparent,valid_traceparent,pareto_front,offline_provenance,refusal_report
from peer_cluster_falsifier import experiment

def fixtures():
    return [
      dict(id='H01.S01.N01',name='Orbital resonance mechanics',definition='Science of motion and angular momentum',house='H01',kind='DOMAIN_SPECIALIZATION'),
      dict(id='H02.S01.N01',name='River hydrology',definition='Energy water motion and channel structure',house='H02',kind='DOMAIN_SPECIALIZATION'),
      dict(id='H08.S01.N10',name='Instrument design',definition='Design of musical instruments in a Music Sphere',house='H08',kind='DOMAIN_SPECIALIZATION'),
      dict(id='H12.S01.N01',name='Spacecraft mechanics',definition='Orbital motion dynamics',house='H12',kind='DOMAIN_SPECIALIZATION'),
      dict(id='H03.S10.N01',name='Ecology science',definition='Independent method review for water measurements',house='H03',kind='EPISTEMIC_META')]

class TestPublic(unittest.TestCase):
 def test_01_index_parity(self):
  idx=CandidateIndex(fixtures())
  for q in ('orbital motion','water','instrument','music','measuring','science',''):
   self.assertEqual(idx.baseline(q),idx.indexed(q))
 def test_02_exclude_house(self):
  idx=CandidateIndex(fixtures());self.assertEqual(idx.baseline('orbital',exclude_house='H01'),idx.indexed('orbital',exclude_house='H01'))
 def test_03_role_filter(self):
  idx=CandidateIndex(fixtures());self.assertEqual(idx.baseline('science',role='EPISTEMIC_META'),idx.indexed('science',role='EPISTEMIC_META'))
 def test_04_no_excludes_used(self):self.assertNotIn('secretword',tokenize('Orbital resonance mechanics'))
 def test_05_exact_sha_pin_constant(self):self.assertEqual(REGISTRY_SHA,'07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6')
 def good(self):return dict(coordinate='H01.S01.N01',mode='WORK',sourceSha='a'*64,rightsAtRead='PASS',rightsAtReturn='PASS',evidenceKind='SYNTHETIC_OR_PUBLIC',subject='toy',fictionLabel='NOT_FICTION',epoch=1)
 def test_06_work_prepared_not_sent(self):self.assertEqual(guard_packet(self.good())['status'],'PREPARED_NOT_SENT')
 def test_07_no_live_host_claim(self):self.assertFalse(guard_packet(self.good())['hostAuthenticated'])
 def test_08_rights_revoked_hold(self):
  x=self.good();x['rightsAtReturn']='REVOKED';self.assertEqual(guard_packet(x)['status'],'HOLD')
 def test_09_leisure_block(self):
  x=self.good();x['mode']='PALACE';self.assertEqual(guard_packet(x)['status'],'HOLD')
 def test_10_extra_secret_block(self):
  x=self.good();x['privateBody']='SECRET';self.assertEqual(guard_packet(x)['status'],'HOLD')
 def test_11_wrong_digest_block(self):
  x=self.good();x['sourceSha']='wrong';self.assertEqual(guard_packet(x)['status'],'HOLD')
 def test_12_meta_missing_subject_block(self):
  x=self.good();x['coordinate']='H01.S10.N01';x['subject']='NONE';self.assertEqual(guard_packet(x)['status'],'HOLD')
 def test_13_trace_shape(self):self.assertTrue(valid_traceparent(synthetic_traceparent('toy-run','H01.S01.N01')))
 def test_14_trace_nongeom(self):
  with self.assertRaises(ValueError):synthetic_traceparent('toy-run','H01.S01.N99')
 def test_15_pareto_mutant(self):
  options=[dict(id=n,cost=c,risk=r,evidence=e,rights='PASS',physicalFloor='PASS',communityFloor='PASS',sourceDigest='a'*64,originMode='WORK') for n,c,r,e in [('A',1,.1,.6),('B',2,.4,.2)]]
  self.assertEqual(pareto_front(options)['selected'],['A'])
  options[0]['cost']=3;self.assertEqual(pareto_front(options)['selected'],['A','B'])
 def test_16_floor(self):
  o=dict(id='A',cost=1,risk=.1,evidence=.9,rights='PASS',physicalFloor='BLOCK',communityFloor='PASS',sourceDigest='a'*64,originMode='WORK')
  self.assertEqual(pareto_front([o])['state'],'HOLD')
 def test_17_provenance_not_attested(self):self.assertFalse(offline_provenance('a'*64,'b'*64)['realSlsaAttestation'])
 def test_18_refusal_noninterference(self):self.assertEqual(refusal_report({'SECRET':'1'}),refusal_report({'SECRET':'2'}))
 def test_19_20_stages(self):self.assertEqual(len(STAGES),20)
 def test_20_stage_names_unique(self):self.assertEqual(len(set(x[2] for x in STAGES)),20)
 def test_21_repeat_digest(self):self.assertEqual(digest({'a':1,'b':2}),digest({'b':2,'a':1}))
 def test_22_null_fixture(self):self.assertEqual(experiment(reps=200,seed=1405)['houseOnlyFalseExclusionOfZero'],190)
 def test_23_null_fixture_has_negative(self):self.assertLess(experiment(reps=100,seed=1405)['examples'][0]['globalShock'],0)
 def test_24_no_synthetic_promotion(self):self.assertFalse(guard_packet(self.good())['releaseEligible'])

if __name__=='__main__':unittest.main()
