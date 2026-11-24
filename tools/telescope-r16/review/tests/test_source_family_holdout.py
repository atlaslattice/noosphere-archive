import unittest,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source_family_holdout import prepare_holdout

def item(id,coord,split,family,prior,shock,series,tick):
    return dict(id=id,coord=coord,split=split,family=family,prior=prior,
                shock=shock,series=series,tick=tick,scope='PUBLIC_WORK',sourceSha=hashlib.sha256(id.encode()).hexdigest())

def fixture():
    return [item('a','H01.S01.N01','TRAIN','fam-a','prior-a','shock-a','series-a',10),
            item('b','H02.S01.N01','TRAIN','fam-b','prior-b','shock-b','series-b',20),
            item('c','H03.S01.N01','HOLDOUT','fam-c','prior-c','shock-c','series-c',100)]

class Tests(unittest.TestCase):
    def prep(self,a=None,links=None,**kw):
        return prepare_holdout(fixture() if a is None else a,[] if links is None else links,lineage_complete=True,**kw)
    def test_01_distinct_declared_groups_provisional_only(self):
        r=self.prep();self.assertEqual(r['status'],'PREPARED_NOT_AUTHORIZED');self.assertFalse(r['independentHoldoutVerified'])
    def test_02_transitive_alias_leak(self):
        l=[{'from':'a','to':'b','relation':'SOURCE_ALIAS'},{'from':'b','to':'c','relation':'SOURCE_ALIAS'}]
        self.assertEqual(self.prep(links=l)['reason'],'CROSS_SPLIT_SOURCE_DEPENDENCE')
    def test_03_same_family(self):
        a=fixture();a[2]['family']='fam-a';self.assertEqual(self.prep(a)['reason'],'CROSS_SPLIT_SOURCE_DEPENDENCE')
    def test_04_shared_prior(self):
        a=fixture();a[2]['prior']='prior-a';self.assertEqual(self.prep(a)['reason'],'CROSS_SPLIT_SOURCE_DEPENDENCE')
    def test_05_shared_shock(self):
        a=fixture();a[2]['shock']='shock-a';self.assertEqual(self.prep(a)['reason'],'CROSS_SPLIT_SOURCE_DEPENDENCE')
    def test_06_temporal_embargo(self):
        a=fixture();a[2]['series']='series-a';a[2]['tick']=22
        self.assertEqual(self.prep(a)['reason'],'TEMPORAL_EMBARGO_OVERLAP')
    def test_07_embargo_boundary(self):
        a=fixture();a[2]['series']='series-a';a[2]['tick']=23
        self.assertEqual(self.prep(a)['status'],'PREPARED_NOT_AUTHORIZED')
    def test_08_missing_lineage_declaration(self):
        self.assertEqual(prepare_holdout(fixture(),[])['reason'],'LINEAGE_NOT_DECLARED_COMPLETE')
    def test_09_private_scope_rejected(self):
        a=fixture();a[0]['scope']='PALACE';self.assertEqual(self.prep(a)['status'],'HOLD')
    def test_10_malformed_source(self):
        a=fixture();a[0]['sourceSha']='forged';self.assertEqual(self.prep(a)['status'],'HOLD')
    def test_11_extra_body_rejected(self):
        a=fixture();a[0]['privateBody']='secret';self.assertEqual(self.prep(a)['status'],'HOLD')
    def test_12_no_id_output(self):
        r=self.prep();self.assertNotIn('fam-a',str(r));self.assertNotIn(hashlib.sha256(b'a').hexdigest(),str(r))
    def test_13_unknown_link_rejected(self):
        self.assertEqual(self.prep(links=[{'from':'a','to':'c','relation':'CERTIFIED_SAME_AS'}])['status'],'HOLD')
    def test_14_denied_on_missing_test(self):
        a=fixture();a=a[:2];self.assertEqual(self.prep(a)['status'],'HOLD')
    def test_15_non_bool_declared_lineage(self):
        self.assertEqual(prepare_holdout(fixture(),[],lineage_complete=1)['status'],'HOLD')
    def test_16_unhashable_relation_rejected(self):
        self.assertEqual(self.prep(links=[{'from':'a','to':'c','relation':[]}])['status'],'HOLD')
    def test_17_bad_split_type_rejected(self):
        a=fixture();a[0]['split']=[];self.assertEqual(self.prep(a)['status'],'HOLD')
    def test_18_no_release_from_declared_identity(self):
        r=self.prep();self.assertFalse(r['releaseEligible']);self.assertFalse(r['hostAuthenticated'])

if __name__=='__main__':unittest.main()
