import unittest,tempfile,json,hashlib
from pathlib import Path
from src.evolution import *
from src.promotion import *

class TestEvolution(unittest.TestCase):
 def test_default_144(self):
  x=new_state();self.assertEqual(len(x['policies']),144);check_state(x)
 def test_proposal_bounds(self):
  self.assertNotEqual(mutate(Policy(1,3),0),Policy(1,3))
  with self.assertRaises(ValueError):Policy(4,6)
 def test_no_chained_false_authority(self):
  x=new_state();x['resident_visits']=1
  with self.assertRaises(ValueError):check_state(x)
 def test_one_actual_trial_then_replay(self):
  with tempfile.TemporaryDirectory() as d:
   x=new_state();f=Path(d)/'trial.jsonl';run_phase(x,4,f,'PHASE_TEST')
   self.assertEqual(x['counts']['evaluated'],4)
   self.assertEqual(verify_log(x,[f])['status'],'CHAIN_AND_POLICY_REPLAY_PASS')
   lines=f.read_text().splitlines();body=json.loads(lines[0]);body['event']['accepted']=not body['event']['accepted'];lines[0]=json.dumps(body)
   f.write_text('\n'.join(lines)+'\n')
   self.assertEqual(verify_log(x,[f])['status'],'FAIL')
 def test_cannot_run_infinite_future(self):
  with self.assertRaises(ValueError):run_phase(new_state(),10001,Path('/tmp/should-not-write'),'PHASE_TEST')
 def test_all_12_chapter_numerical_gate(self):
  self.assertTrue(numerical_safety(Policy(3,6),0))
  self.assertFalse(numerical_safety(Policy(3,2),0))
 def test_source_free_seed_separation(self):
  self.assertNotEqual(seed_set('train',0,0,3),seed_set('blind',0,0,3))
 def test_bad_encoding_held(self):
  a={'false_accepted':0,'postflight_holds':0,'passes':1,'score':.2}
  b={'false_accepted':0,'postflight_holds':1,'passes':1,'score':1.0}
  self.assertFalse(acceptance(a,b,Policy(1,4),Policy(3,2))[0])
 def test_15000_receipt_present_when_available(self):
  f=Path(__file__).parents[1]/'outputs'/'CHECKPOINT_15000.json'
  if not f.exists():self.skipTest('phase dataset omitted')
  x=load_state(f);self.assertEqual(x['next_index'],15000)
  self.assertEqual(x['counts']['evaluated'],15000)
  self.assertEqual(x['counts']['accepted']+x['counts']['rejected'],15000)
  self.assertFalse(x['model_weights_modified'])

if __name__=='__main__':unittest.main()

class TestContinuation(unittest.TestCase):
 def test_no_unbounded_batch_id(self):
  from continue_batch import next_batch
  with self.assertRaises(ValueError):next_batch(Path('/tmp/nonexistent'),0)
 def test_no_overwrite_existing_batch(self):
  from continue_batch import next_batch
  with tempfile.TemporaryDirectory() as d:
   path=Path(d);(path/'CONTINUATION_BATCH_00001_144.jsonl').write_text('existing')
   with self.assertRaises(FileExistsError):next_batch(Path('/tmp/nonexistent'),1,path)
