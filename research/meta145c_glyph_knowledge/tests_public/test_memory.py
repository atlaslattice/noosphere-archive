import unittest,tempfile,hashlib,sqlite3
from pathlib import Path
from src.memory import LocalMemory

BASE={'mode':'WORK','scope':'SYNTHETIC_LOCAL_REVIEW','coordinate':'H01.S05.N10','topic_id':'T10346','source_ref':'urn:atlas:synthetic:fixture42','source_digest':'a'*64}
class MemoryTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'m.sqlite';self.mem=LocalMemory(self.path)
 def tearDown(self):self.mem.close();self.tmp.cleanup()
 def ev(self,event_id='note01',action='NOTE',**kwargs):return {**BASE,'event_id':event_id,'action':action,**kwargs}
 def test_empty_tip(self):self.assertEqual(self.mem.verify()['tip'],'0'*64)
 def test_note_restarts(self):
  self.mem.append(self.ev());self.assertEqual(self.mem.triage_delta('H01.S05.N10','T10346'),1)
  self.mem.close();self.mem=LocalMemory(self.path);self.assertEqual(self.mem.triage_delta('H01.S05.N10','T10346'),1)
 def test_challenge_deprioritizes(self):self.mem.append(self.ev(action='CHALLENGE'));self.assertEqual(self.mem.triage_delta('H01.S05.N10','T10346'),-1)
 def test_retraction_compensates(self):
  self.mem.append(self.ev());self.mem.append(self.ev('retract01','RETRACT',retract_event_id='note01'))
  self.assertEqual(self.mem.triage_delta('H01.S05.N10','T10346'),0);self.assertEqual(self.mem.verify()['count'],2)
 def test_duplicate_rejected(self):
  self.mem.append(self.ev());
  with self.assertRaises(ValueError):self.mem.append(self.ev())
 def test_second_retraction_rejected(self):
  self.mem.append(self.ev());self.mem.append(self.ev('retract01','RETRACT',retract_event_id='note01'))
  with self.assertRaises(ValueError):self.mem.append(self.ev('retract02','RETRACT',retract_event_id='note01'))
 def test_unlisted_retraction_rejected(self):
  with self.assertRaises(ValueError):self.mem.append(self.ev('retract01','RETRACT',retract_event_id='unknown'))
 def test_wrong_scope_rejected(self):
  for scope in ['PLAY','PALACE','IMAGINE','QUIET','HOSTED','PRODUCTION']:
   with self.subTest(scope=scope),self.assertRaises(ValueError):self.mem.append(self.ev(scope=scope))
 def test_private_mode_rejected(self):
  for mode in ['PLAY','SOCIAL','IMAGINE','DREAM','BRAIN','PALACE','HABITAT','QUIET']:
   with self.subTest(mode=mode),self.assertRaises(ValueError):self.mem.append(self.ev(mode=mode))
 def test_host_claim_rejected(self):
  for k in ['residentAuthenticated','hostApproved','canonRatified','privateContext','modelWeights','sourceBody']:
   with self.subTest(k=k),self.assertRaises(ValueError):self.mem.append(self.ev(**{k:True}))
 def test_no_model_training(self):self.assertFalse(self.mem.append(self.ev())['model_weights_updated'])
 def test_no_canon_effect(self):self.assertEqual(self.mem.append(self.ev())['canon_effect'],'NONE')
 def test_bad_hsn(self):
  with self.assertRaises(ValueError):self.mem.append(self.ev(coordinate='H99.S99.N99'))
 def test_bad_topic(self):
  with self.assertRaises(ValueError):self.mem.append(self.ev(topic_id='T?'))
 def test_source_ref(self):
  for src in ['file:///private','http://evil.test','javascript:alert(1)','', 's3://private']:
   with self.subTest(src=src),self.assertRaises(ValueError):self.mem.append(self.ev(source_ref=src))
 def test_sha_invalid(self):
  with self.assertRaises(ValueError):self.mem.append(self.ev(source_digest='NOT_SHA'))
 def test_tamper_detected(self):
  self.mem.append(self.ev());self.mem.db.execute("UPDATE review_events SET source_ref='urn:atlas:synthetic:tampered' WHERE seq=1");self.mem.db.commit();self.assertEqual(self.mem.verify()['status'],'FAIL_CHAIN')
 def test_wrong_node_retraction(self):
  self.mem.append(self.ev());
  with self.assertRaises(ValueError):self.mem.append(self.ev('retract01','RETRACT',coordinate='H01.S01.N01',retract_event_id='note01'))
 def test_chained_hash(self):
  self.mem.append(self.ev());self.mem.append(self.ev('challenge01','CHALLENGE'))
  self.assertEqual(self.mem.verify()['count'],2);self.assertEqual(self.mem.triage_delta('H01.S05.N10','T10346'),0)
 def test_wrong_topic_unaffected(self):
  self.mem.append(self.ev());self.assertEqual(self.mem.triage_delta('H01.S05.N10','T99999'),0)
 def test_no_score_transfer(self):
  self.mem.append(self.ev());self.assertEqual(self.mem.triage_delta('H01.S05.N11','T10346'),0)
