"""Portable Meta145 candidate-only controls; NO private source bytes required."""
from __future__ import annotations
import sys,unittest,tempfile,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import meta145_glyph_memory as m

class DisplayOnly(unittest.TestCase):
 def test_exact_source_edition(self):self.assertEqual(m.SOURCE_SHA,'07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6')
 def test_reversible_all_1728_coordinates(self):
  gs=set();xs=set()
  for h in range(1,13):
   for s in range(1,13):
    for n in range(1,13):
     coord=f'H{h:02d}.S{s:02d}.N{n:02d}'
     g=m.gid(h,s,n);p=m.gf7(h,s,n)
     self.assertEqual(m.parse_glyph(g),coord);self.assertEqual(m.parse_gf7(p['coordinate']),coord)
     gs.add(g);xs.add(p['coordinate'])
  self.assertEqual(len(gs),1728);self.assertEqual(len(xs),1728)
 def test_wrong_glyph_source_held(self):
  for x in ['KG8Q:000000000000:sala.sala.sala','Q:sala.sala.sala','KG8Q:07533cf7a6b6:nosuch.sala.sala']:
   with self.assertRaises(m.Held):m.parse_glyph(x)
 def test_gf7_visual_not_physics(self):
  p=m.gf7(5,6,7);self.assertEqual(p['relation'],'POSITIONAL_VISUAL_INDEX_ONLY');self.assertFalse(p['physicalCouplingDemonstrated'])
 def test_scoring_parity_on_public_synthetic_docs(self):
  p={'weightedTerms':{'music':7,'methods':5,'matter':12}}
  docs=[{'music','matter'},{'methods'},{'music','matter','methods'},set()]
  postings={'music':[0,2],'methods':[1,2],'matter':[0,2]}
  self.assertEqual(m.score_brute(p,docs),m.score_indexed(p,postings,4))
 def test_source_free_empty_memory_chooses_baseline(self):
  with tempfile.TemporaryDirectory() as d:
   mem=m.FunctionalMemory(pathlib.Path(d)/'events.jsonl');self.assertEqual(mem.policy()['selected'],'BASELINE_SCAN')
 def test_unverified_speedup_not_persisted(self):
  event={'eventId':'bad','kind':'SCORING_INDEX_REPLAY','mode':'WORK','sourceSHA256':m.SOURCE_SHA,'sourceInputDigest':'0'*64,
   'outputsMatch':False,'benchmark':{'baselineMedianMs':20,'optimizedMedianMs':10,'medianSpeedup':2},
   'authorityEffect':'NONE','privateModeIngested':False,'status':'VERIFIED_LOCAL_PERFORMANCE'}
  with tempfile.TemporaryDirectory() as d:
   mem=m.FunctionalMemory(pathlib.Path(d)/'events.jsonl')
   with self.assertRaises(m.Held):mem.append(event)
 def test_work_memory_never_reads_private_play(self):
  event={'eventId':'bad','kind':'SCORING_INDEX_REPLAY','mode':'PLAY','sourceSHA256':m.SOURCE_SHA,'sourceInputDigest':'0'*64,
   'outputsMatch':False,'benchmark':{},'authorityEffect':'NONE','privateModeIngested':True,'status':'REVIEW_CANDIDATE'}
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(m.Held):m.FunctionalMemory(pathlib.Path(d)/'events.jsonl').append(event)
 def test_stale_feedback_does_not_select(self):
  with tempfile.TemporaryDirectory() as d:
   mem=m.FunctionalMemory(pathlib.Path(d)/'events.jsonl')
   event={'eventId':'old','kind':'SCORING_INDEX_REPLAY','mode':'WORK','sourceSHA256':m.SOURCE_SHA,'sourceInputDigest':'a'*64,
    'outputsMatch':True,'benchmark':{'baselineMedianMs':20,'optimizedMedianMs':10,'medianSpeedup':2},
    'authorityEffect':'NONE','privateModeIngested':False,'status':'VERIFIED_LOCAL_PERFORMANCE'}
   mem.append(event)
   self.assertEqual(mem.policy('b'*64)['selected'],'BASELINE_SCAN')
   self.assertEqual(mem.policy('a'*64)['selected'],'POSTINGS_INDEX')
if __name__=='__main__':unittest.main()
