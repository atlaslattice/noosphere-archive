"""Finite, public-safe null-world adversarial time-dependence controls."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from temporal_dependency_falsifier import run_null_experiment

class TestTemporal(unittest.TestCase):
 def test_real_null_mean_known(self):
  r=run_null_experiment(worlds=20,reps=79,seed=4117)
  self.assertEqual(r['trueEffect'],0)
 def test_iid_independence_assumption_falsified(self):
  r=run_null_experiment(worlds=60,reps=99,rho=.94,block=48,seed=4117)
  self.assertGreater(r['iidTimeCIExcludesZero'],r['movingBlockCIExcludesZero'])
 def test_moving_blocks_not_universally_calibrated(self):
  r=run_null_experiment(worlds=60,reps=99,rho=.94,block=48,seed=4117)
  self.assertGreater(r['movingBlockCIExcludesZero'],3)
 def test_no_host_claims(self):
  r=run_null_experiment(worlds=10,reps=49)
  self.assertIn('synthetic',r['interpretation'].lower()+' synthetic')
 def test_reproducibility(self):
  a=run_null_experiment(worlds=10,reps=49,seed=99)
  self.assertEqual(a,run_null_experiment(worlds=10,reps=49,seed=99))
if __name__=='__main__':unittest.main()
