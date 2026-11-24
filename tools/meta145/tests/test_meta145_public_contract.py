"""Portable, synthetic, source-safe tests; no private Ariadne corpus required."""
from __future__ import annotations
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from build_fast_observatory import transform
from run_meta145 import make_four_proposals

SYNTHETIC_HTML='''<!doctype html><html><head><title>Atlas Turbo ×12 · 1,728 / 144 / 12 / 1</title></head><body>
ATLAS TURBO ×12 · CIVILIZATION CIRCUIT Search all 1,728 nodes
<div class="entries" id="entries" role="listbox" aria-label="Filtered knowledge nodes"></div>
<script>function filter(){const xs=all.filter(Boolean);for(const n of xs.slice(0,650))container.appendChild(n)}
for(let i=1;i<=12;i++){}</script></body></html>'''

class FastUIContract(unittest.TestCase):
 def test_injects_window_and_source_pager(self):
  result=transform(SYNTHETIC_HTML)
  self.assertIn('const RESULT_PAGE_SIZE=48',result)
  self.assertIn('Show next',result)
  self.assertIn('aria-label="Load more knowledge nodes"',result)
  self.assertNotIn('xs.slice(0,650)',result)
 def test_refuses_ambiguous_baseline(self):
  with self.assertRaises(ValueError):transform('function filter(){}')
 def test_keeps_other_markup(self):
  result=transform(SYNTHETIC_HTML)
  self.assertIn('<!doctype html>',result)
  self.assertIn('for(let i=1;i<=12;i++)',result)
 def test_rewrite_is_not_idempotently_doubled(self):
  result=transform(SYNTHETIC_HTML)
  with self.assertRaises(ValueError):transform(result)
 def test_avoids_rendering_raw_search_html(self):
  result=transform(SYNTHETIC_HTML)
  self.assertIn('create(\'b\',n.id)',result)
  self.assertIn('document.createTextNode',result)
  self.assertNotIn('innerHTML',result)
 def test_source_regression_requires_frozen_marker(self):
  with self.assertRaises(ValueError):transform(SYNTHETIC_HTML.replace('xs.slice(0,650)','xs.slice(0,800)'))

class ProposalContract(unittest.TestCase):
 def setUp(self):self.work=make_four_proposals('H01.S01','A synthetic physics sphere','Synthetic subject','DOMAIN','0'*64)
 def test_exact_four_systems(self):self.assertEqual(len(self.work),4)
 def test_all_non_authorizing(self):
  self.assertTrue(all(x['status'].startswith('PROPOSED_') or x['status'].startswith('AUTHOR_') for x in self.work.values()))
 def test_no_automatic_semantic_promotion(self):
  self.assertIn('never creates',self.work['Ariadne']['negative_test'])
 def test_no_fiction_canon_claim(self):
  self.assertIn('NOT_CANON',self.work['Iron Empire']['status'])

if __name__=='__main__':unittest.main()
