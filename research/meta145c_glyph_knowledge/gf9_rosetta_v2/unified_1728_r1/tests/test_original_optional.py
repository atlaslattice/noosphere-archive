"""Optional owner-source provenance tests; skip clean public CI without private inputs."""
import os,unittest
from pathlib import Path
from atlas1728.source import Corpus,ARIADNE_SHA,OPENALEX_SHA
from atlas1728.index import SourceIndex

ROOT=os.environ.get('ATLAS_ORIGINAL_ARIADNE_PATH','')
TOPIC=os.environ.get('ATLAS_ORIGINAL_OPENALEX_PATH','')
READY=bool(ROOT and TOPIC and Path(ROOT).is_file() and Path(TOPIC).is_file())

@unittest.skipUnless(READY,'Owner-private exact original source bytes not installed')
class SourceIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.c=Corpus.original(ROOT,TOPIC);cls.index=SourceIndex(cls.c)
    def test_input_exact_shas(self):self.assertEqual(self.c.registry_sha,ARIADNE_SHA);self.assertEqual(self.c.topic_sha,OPENALEX_SHA)
    def test_scope_counts(self):self.assertEqual(len(self.c.topics),4516);self.assertEqual(sum(map(len,self.c.topic_edges.values())),22580)
    def test_false_friend_not_promoted(self):
        n=self.c.nodes['H08.S01.N10'];self.assertIn('instrument',n['name'].lower())
        self.assertTrue(all(not self.c.topics[e['topic_id']]['accepted'] for e in self.c.topic_edges['H08.S01.N10']))
    def test_topic_denominator_203(self):self.assertEqual(len(self.c.topic_edges['H04.S01.N02']),203)
    def test_topic_denominator_32(self):self.assertEqual(len(self.c.topic_edges['H10.S05.N12']),32)
    def test_method_nodes_not_forced_equivalent(self):
        self.assertEqual(self.c.nodes['H08.S01.N10']['kind'],'DOMAIN_SPECIALIZATION')
        self.assertEqual(self.c.nodes['H01.S08.N01']['kind'],'EPISTEMIC_META')
        self.assertFalse(self.c.topics[next(iter(self.c.topics))]['accepted'])
