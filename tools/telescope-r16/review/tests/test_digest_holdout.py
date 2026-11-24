import hashlib
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_family_holdout import prepare_holdout


def item(key, split, coord='H01.S01.N01'):
    return dict(id=key, coord=coord, split=split, family='f-'+key,
                prior='p-'+key, shock='s-'+key, series='t-'+key, tick=20,
                sourceSha=hashlib.sha256(key.encode()).hexdigest(), scope='PUBLIC_WORK')


def check(records, links=None):
    return prepare_holdout(records, links or [], lineage_complete=True)


class DigestTests(unittest.TestCase):
    def test_duplicate_digest(self):
        a,b=item('a','TRAIN'),item('b','HOLDOUT')
        b['sourceSha']=a['sourceSha']
        self.assertEqual(check([a,b]).get('reason'),'CROSS_SPLIT_SOURCE_DEPENDENCE')

    def test_distinct_digest(self):
        a,b=item('a','TRAIN'),item('b','HOLDOUT')
        r=check([a,b])
        self.assertEqual(r['status'],'PREPARED_NOT_AUTHORIZED')
        self.assertFalse(r['independentHoldoutVerified'])
        self.assertFalse(r['releaseEligible'])

    def test_same_split_digest(self):
        a,b,c=item('a','TRAIN'),item('b','TRAIN'),item('c','HOLDOUT')
        b['sourceSha']=a['sourceSha']
        r=check([a,b,c])
        self.assertEqual(r['status'],'PREPARED_NOT_AUTHORIZED')
        self.assertEqual(r['declaredComponents'],2)

    def test_transitive_digest_alias(self):
        a,b,c=item('a','TRAIN'),item('b','TRAIN'),item('c','HOLDOUT')
        b['sourceSha']=a['sourceSha']
        r=check([a,b,c],[dict({'from':'b','to':'c','relation':'SOURCE_ALIAS'})])
        self.assertEqual(r.get('reason'),'CROSS_SPLIT_SOURCE_DEPENDENCE')

    def test_full_address_sweep(self):
        for h in range(1,13):
            for s in range(1,13):
                for n in range(1,13):
                    coord=f'H{h:02}.S{s:02}.N{n:02}'
                    with self.subTest(coord=coord):
                        a,b=item('a','TRAIN',coord),item('b','HOLDOUT',coord)
                        self.assertEqual(check([a,b])['status'],'PREPARED_NOT_AUTHORIZED')
                        b['sourceSha']=a['sourceSha']
                        self.assertEqual(check([a,b]).get('reason'),'CROSS_SPLIT_SOURCE_DEPENDENCE')

    def test_no_digest_echo(self):
        a,b=item('a','TRAIN'),item('b','HOLDOUT')
        b['sourceSha']=a['sourceSha']
        self.assertNotIn(a['sourceSha'],str(check([a,b])))


if __name__=='__main__':
    unittest.main()
