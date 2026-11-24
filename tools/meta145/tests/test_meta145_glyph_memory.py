from __future__ import annotations
import json, tempfile, unittest, sys, hashlib, pathlib, shutil, sqlite3, os
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import meta145_glyph_memory as m

SOURCE=pathlib.Path(os.environ.get('ATLAS_ARIADNE_ORIGINAL_FILE','__OWNER_PRIVATE_SOURCE_NOT_CONFIGURED__'))
OUT=pathlib.Path(os.environ.get('ATLAS_META145_GLYPH_OUTPUT','__SOURCE_ONLY_OUTPUT_NOT_CONFIGURED__'))

@unittest.skipUnless(SOURCE.exists() and (OUT/'META145_GLYPH_MEMORY.json').exists(),'owner-private pinned original and generated artifacts required')
class SourceAndGlyph(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.data=m.load_registry(SOURCE);cls.ps=json.loads((OUT/'perspectives_144.json').read_text());cls.nodes=json.loads((OUT/'node_glyphs_1728.json').read_text())
 def test_original_source_pinned(self):self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),m.SOURCE_SHA)
 def test_census(self):self.assertEqual(tuple(map(len,[self.data['houses'],self.data['spheres'],self.data['nodes']])),(12,144,1728))
 def test_roles_sphere_not_node(self):
  self.assertEqual(self.data['nodes']['H01.S01.N08']['kind'],'DOMAIN_SPECIALIZATION')
  self.assertEqual(self.data['nodes']['H01.S08.N01']['kind'],'EPISTEMIC_META')
 def test_bad_source_bytes_fail(self):
  with tempfile.TemporaryDirectory() as d:
   b=bytearray(SOURCE.read_bytes());b[-3]^=1;p=pathlib.Path(d)/'changed.json';p.write_bytes(b)
   with self.assertRaisesRegex(m.Held,'ORIGINAL_SOURCE_HASH_MISMATCH'):m.load_registry(p)
 def test_perspective_total(self):self.assertEqual(len(self.ps),144)
 def test_unique_weighted_perspectives(self):self.assertEqual(len({tuple(x['weightedTerms'].items()) for x in self.ps}),144)
 def test_unique_top_twelve_terms(self):self.assertEqual(len({tuple(x['anchorTerms']) for x in self.ps}),144)
 def test_perspective_digest_integrity(self):
  for p in self.ps:
   x=dict(p);h=x.pop('perspectiveSha256');self.assertEqual(m.digest(x),h)
 def test_same_source_nodes_twelve_per_sphere(self):
  for p in self.ps:
   self.assertEqual(len(p['homeNodes']),12)
   self.assertEqual([self.data['nodes'][x]['source_record_sha256'] for x in p['homeNodes']],p['homeNodeDigests'])
 def test_all_1728_glyphs_reversible(self):
  for row in self.nodes:
   self.assertEqual(m.parse_glyph(row['glyphQ']),row['coordinate'])
   self.assertEqual(m.parse_glyph(row['glyphS']),row['coordinate'])
   self.assertEqual(m.parse_gf7(row['cymaticAddress']),row['coordinate'])
 def test_known_live_glyph_alias(self):
  self.assertEqual(m.gid(8,1,10),'KG8Q:07533cf7a6b6:tiri.sala.turu')
  self.assertEqual(m.gid(8,1,10,'S'),'KG8S:07533cf7a6b6:nil.gal.nul')
  self.assertEqual(m.gf7(8,1,10)['coordinate'],'GF7.B08.M01.C10')
 def test_broker_synced_end_glyph(self):self.assertEqual(m.gid(12,12,12),'KG8Q:07533cf7a6b6:mere.mere.mere')
 def test_glyph_refuses_wrong_edition(self):
  with self.assertRaises(m.Held):m.parse_glyph('KG8Q:aaaaaaaaaaaa:tiri.sala.turu')
 def test_glyph_refuses_gf7_namespace(self):
  with self.assertRaises(m.Held):m.parse_glyph('Q:tiri.sala.turu')
 def test_gf7_refuses_hsn(self):
  with self.assertRaises(m.Held):m.parse_gf7('H08.S01.N10')
 def test_gf7_not_physics(self):
  x=m.gf7(1,5,9)
  self.assertFalse(x['actualPlateMeasured']);self.assertFalse(x['physicalCouplingDemonstrated']);self.assertEqual(x['relation'],'POSITIONAL_VISUAL_INDEX_ONLY')
 def test_all_role_sources_and_144_spheres(self):
  counts={'DOMAIN_SPECIALIZATION':0,'EPISTEMIC_META':0}
  for p in self.ps:
   counts[p['sourceRole']]+=1;self.assertEqual(p['sourceRole'],'DOMAIN_SPECIALIZATION' if int(p['sphere'][5:])<=7 else 'EPISTEMIC_META')
  self.assertEqual(counts,{'DOMAIN_SPECIALIZATION':84,'EPISTEMIC_META':60})
 def test_music_false_friend_remains_music(self):
  self.assertEqual(self.data['nodes']['H08.S01.N10']['name'],'Instrument design')
  self.assertIn('musical instruments',self.data['nodes']['H08.S01.N10']['definition'])
 def test_semantic_edges_are_all_review_only(self):
  edges=json.loads((OUT/'candidate_edges.json').read_text())
  self.assertGreater(len(edges),0)
  self.assertTrue(all(x['semanticAcceptance']=='NOT_ADJUDICATED' for x in edges))
  self.assertTrue(all(x['typedRelation'] in ('LEXICAL_REVIEW_CANDIDATE_ONLY','METHOD_LENS_APPLICABILITY_CANDIDATE') for x in edges))
  self.assertTrue(all(x['requiresExplicitDomainSubject'] and x['domainSubjectCoordinate'] is None for x in edges if x['fromRole']!=x['toRole']))
  self.assertGreater(sum(x['fromRole']!=x['toRole'] for x in edges),0)
 def test_all_144_scorer_parity(self):
  ids,docs,posting,df=m.node_index(self.data)
  for p in self.ps:self.assertEqual(m.score_brute(p,docs),m.score_indexed(p,posting))
 def test_all_1728_housesphere_review_questions(self):
  rows=[json.loads(x) for x in (OUT/'house_sphere_followups_1728.jsonl').read_text().splitlines()]
  self.assertEqual(len(rows),1728);self.assertEqual(len({x['id'] for x in rows}),1728)
  for h in range(144):
   self.assertEqual(len({x['reviewHouse'] for x in rows[h*12:h*12+12]}),12)
   self.assertTrue(all(x['sourceSphere']==self.ps[h]['sphere'] for x in rows[h*12:h*12+12]))
 def test_house_followups_reuse_not_new_computations(self):
  rows=[json.loads(x) for x in (OUT/'house_sphere_followups_1728.jsonl').read_text().splitlines()]
  self.assertEqual(sum(x['logicalSourceNodeReferencesReused'] for x in rows),2985984)
  self.assertEqual(sum(x['newIndependentEvaluations'] for x in rows),0)
  self.assertTrue(all(x['semanticStatus']=='UNREVIEWED' and x['rightsGranted'] is False for x in rows))
 def test_matrix_248832(self):
  db=sqlite3.connect(OUT/'sphere_node_matrix_248832.sqlite3')
  try:self.assertEqual(db.execute('select count(*) from score').fetchone()[0],248832)
  finally:db.close()
 def test_meta145_receipt(self):
  h=json.loads((OUT/'META145_GLYPH_MEMORY.json').read_text())
  self.assertEqual(h['computedPairEvaluations'],248832);self.assertEqual(h['semanticAcceptanceCount'],0)
  self.assertFalse(h['siteDeployed']);self.assertFalse(h['canonAltered'])
 def test_independent_verify(self):self.assertEqual(m.verify_build(SOURCE,OUT)['status'],'PASS_LOCAL_REPRODUCIBLE')

@unittest.skipUnless(SOURCE.exists() and (OUT/'META145_GLYPH_MEMORY.json').exists(),'owner-private pinned original and generated artifacts required')
class FunctionalLearningMemory(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.p=pathlib.Path(self.tmp.name)/'events.jsonl'
 def tearDown(self):self.tmp.cleanup()
 def event(self,**updates):
  e={'eventId':'test-validated-gain-01','kind':'SCORING_INDEX_REPLAY','mode':'WORK','sourceSHA256':m.SOURCE_SHA,
     'sourceInputDigest':'a'*64,'outputsMatch':True,
     'benchmark':{'baselineMedianMs':40,'optimizedMedianMs':10,'medianSpeedup':4},
     'authorityEffect':'NONE','privateModeIngested':False,'status':'VERIFIED_LOCAL_PERFORMANCE'}
  e.update(updates);return e
 def test_new_memory_starts_on_baseline(self):self.assertEqual(m.FunctionalMemory(self.p).policy()['selected'],'BASELINE_SCAN')
 def test_validated_gain_changes_policy(self):
  memory=m.FunctionalMemory(self.p);memory.append(self.event());self.assertEqual(memory.policy()['selected'],'POSTINGS_INDEX')
 def test_stale_source_feedback_cannot_select_current_policy(self):
  mem=m.FunctionalMemory(self.p);mem.append(self.event());self.assertEqual(mem.policy('f'*64)['selected'],'BASELINE_SCAN')
 def test_persistent_replay(self):
  memory=m.FunctionalMemory(self.p);x=memory.append(self.event());y=m.FunctionalMemory(self.p)
  self.assertEqual(y.rows[0]['chainSHA256'],x['chainSHA256']);self.assertEqual(y.policy()['selected'],'POSTINGS_INDEX')
 def test_duplicate_event_cannot_double_count(self):
  memory=m.FunctionalMemory(self.p);memory.append(self.event())
  with self.assertRaisesRegex(m.Held,'MEMORY_EVENT_ID_REPLAY'):memory.append(self.event())
 def test_negative_speedup_cannot_promote(self):
  with self.assertRaisesRegex(m.Held,'UNVERIFIED_PERFORMANCE_PROMOTION'):
   m.FunctionalMemory(self.p).append(self.event(benchmark={'baselineMedianMs':10,'optimizedMedianMs':20,'medianSpeedup':.5}))
 def test_false_parity_cannot_promote(self):
  with self.assertRaisesRegex(m.Held,'UNVERIFIED_PERFORMANCE_PROMOTION'):m.FunctionalMemory(self.p).append(self.event(outputsMatch=False))
 def test_private_mode_not_work_memory(self):
  for bad in [self.event(mode='PLAY'),self.event(privateModeIngested=True)]:
   with self.assertRaisesRegex(m.Held,'MEMORY_SCOPE_VIOLATION'):m.FunctionalMemory(self.p).append(bad)
 def test_spoofed_source_not_memory(self):
  with self.assertRaisesRegex(m.Held,'MEMORY_SCOPE_VIOLATION'):m.FunctionalMemory(self.p).append(self.event(sourceSHA256='0'*64))
 def test_tamper_detected(self):
  m.FunctionalMemory(self.p).append(self.event());self.p.write_text(self.p.read_text().replace('POSTINGS','BANNERS').replace('SCORING_INDEX_REPLAY','SCORING_INDEX_MISREPLAY'))
  with self.assertRaisesRegex(m.Held,'MEMORY_HASH_MISMATCH'):m.FunctionalMemory(self.p)
 def test_memory_run_is_not_autonomous(self):
  b=json.loads((OUT/'META145_GLYPH_MEMORY.json').read_text())
  self.assertFalse(b['learning']['continuousBackgroundExecution']);self.assertFalse(b['learning']['externalSemanticsAccepted'])
 def test_real_stored_policy_replay(self):
  p=m.FunctionalMemory(OUT/'functional_memory.jsonl');self.assertGreaterEqual(len(p.rows),1)
  meta=json.loads((OUT/'META145_GLYPH_MEMORY.json').read_text());self.assertEqual(p.policy(meta['meta145Digest'])['selected'],'POSTINGS_INDEX')
 def test_benchmark_same_integer_results(self):
  b=json.loads((OUT/'bench_current.json').read_text());self.assertEqual(b['exactOutputParity'],True);self.assertGreater(b['medianSpeedup'],1)

if __name__=='__main__':unittest.main()
