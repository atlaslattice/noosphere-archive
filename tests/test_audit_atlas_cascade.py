import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_atlas_cascade import audit,hsn,sha

DIST = Path(__file__).resolve().parents[1]/"dist"
class IndependentAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=json.loads((DIST/"stage100.json").read_text())
        cls.e=json.loads((DIST/"stage1100.json").read_text())
        cls.s=json.loads((DIST/"summary.json").read_text())
    def test_all(self):
        r=audit(self.p,self.e,self.s)
        self.assertEqual(r["trials"],1100)
        self.assertEqual(r["authority"],"NONE")
    def test_1728_unique(self):
        self.assertEqual(len({hsn(i) for i in range(1,1729)}),1728)
    def test_rehash_deterministic(self):
        self.assertEqual(sha({'a':1,'b':2}),sha({'b':2,'a':1}))
    def test_invalid_phase(self):
        x=copy.deepcopy(self.e);x['ledger'][100]['phase']='PRIMARY_100'
        with self.assertRaises(ValueError):audit(self.p,x,self.s)
    def test_inserted_private_body(self):
        x=copy.deepcopy(self.e);x['ledger'][0]['privateBody']='FAKE_SENTINEL'
        with self.assertRaises(ValueError):audit(self.p,x,self.s)
    def test_host_fabrication(self):
        x=copy.deepcopy(self.e);x['ledger'][100]['hostVerified']=True
        with self.assertRaises(ValueError):audit(self.p,x,self.s)
    def test_reordered_receipt(self):
        x=copy.deepcopy(self.e);x['ledger'][50],x['ledger'][51]=x['ledger'][51],x['ledger'][50]
        with self.assertRaises(ValueError):audit(self.p,x,self.s)
    def test_modified_outcome(self):
        x=copy.deepcopy(self.e);x['ledger'][300]['outcome']='PASS_DEPLOYED'
        with self.assertRaises(ValueError):audit(self.p,x,self.s)
    def test_changed_stage_root(self):
        x=copy.deepcopy(self.p);x['head']='1'*64
        with self.assertRaises(ValueError):audit(x,self.e,self.s)
    def test_semantic_promotion(self):
        x=copy.deepcopy(self.e);x['state']['candidateLinks'][0]['relation']='SAME_AS'
        with self.assertRaises(ValueError):audit(self.p,x,self.s)
    def test_fake_mode(self):
        x=copy.deepcopy(self.e);x['state']['workPosts'][0]['mode']='PLAY'
        with self.assertRaises(ValueError):audit(self.p,x,self.s)
    def test_bad_replay_count(self):
        x=copy.deepcopy(self.e);x['regressionEvaluations']=6
        with self.assertRaises(ValueError):audit(self.p,x,self.s)
    def test_overclaim(self):
        x=copy.deepcopy(self.s);x['hostModelWakeCalls']=1100
        with self.assertRaises(ValueError):audit(self.p,self.e,x)
    def test_summary_count(self):
        x=copy.deepcopy(self.s);x['trials']=1099
        with self.assertRaises(ValueError):audit(self.p,self.e,x)
    def test_edit_stale_stage_first100(self):
        x=copy.deepcopy(self.p);x['ledger'][0]['caseDigest']='0'*64
        with self.assertRaises(ValueError):audit(x,self.e,self.s)
if __name__=='__main__':unittest.main()
