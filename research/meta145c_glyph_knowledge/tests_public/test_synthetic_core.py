"""Source-free synthetic boundary and full 144×1728 exact-path tests."""
import unittest,tempfile,json,hashlib,sqlite3
from pathlib import Path
from src.core import SourceSnapshot,SearchIndex,initialize_db,compute_circuit,benchmark,tokens
from src.knowledge import topic_view,shared_topic_neighbors,source_card
from src.memory import LocalMemory

def synthetic():
 houses={};spheres={};nodes={}
 for h in range(1,13):
  hid=f'H{h:02d}';houses[hid]={'id':hid,'name':f'SYNTHETIC House {h}','children':[]}
  for s in range(1,13):
   sid=f'{hid}.S{s:02d}';houses[hid]['children'].append(sid)
   spheres[sid]={'id':sid,'name':f'SYNTHETIC Sphere {h}-{s} program', 'parent':hid,'children':[]}
   for n in range(1,13):
    nid=f'{sid}.N{n:02d}';spheres[sid]['children'].append(nid)
    nodes[nid]={'id':nid,'name':f'SYNTHETIC node {h} {s} {n} program', 'parent':sid,
                'kind':'DOMAIN_SPECIALIZATION' if s<=7 else 'EPISTEMIC_META',
                'source_record_sha256':hashlib.sha256(nid.encode()).hexdigest()}
 return {'houses':houses,'spheres':spheres,'nodes':nodes}

class SyntheticSourceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();p=Path(cls.tmp.name)/'synthetic.json'
  raw=json.dumps(synthetic(),sort_keys=True).encode();p.write_bytes(raw)
  cls.s=SourceSnapshot(p,expected_sha=hashlib.sha256(raw).hexdigest());cls.idx=SearchIndex(cls.s)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_cardinality(self):self.assertEqual((len(self.s.spheres),len(self.s.nodes)),(144,1728))
 def test_lens_all_144_unique(self):self.assertEqual(len(set(self.s.spheres[s]['name'] for s in self.s.sphere_ids)),144)
 def test_parity_full(self):
  for sid in self.s.sphere_ids:self.assertEqual(self.idx.indexed(self.idx.perspective_terms(sid)),self.idx.linear(self.idx.perspective_terms(sid)))
 def test_full_circuit_with_12_houses(self):
  with tempfile.TemporaryDirectory() as d:
   r=compute_circuit(self.s,self.idx,d)
   self.assertEqual(r['comparisons'],248832);self.assertEqual(len(r['sphere_reviews']),144);self.assertEqual(len(r['house_followups']),12)
   self.assertEqual(len(set(x['receipt_sha256'] for x in r['sphere_reviews'])),144)
   self.assertTrue(all(x['status'].endswith('NOT_SEMANTICALLY_APPROVED') for x in r['sphere_reviews']))
 def test_circuit_deterministic_gzip_and_receipts(self):
  with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
   ra=compute_circuit(self.s,self.idx,a);rb=compute_circuit(self.s,self.idx,b)
   self.assertEqual(ra['terminal_sphere_digest'],rb['terminal_sphere_digest'])
   self.assertEqual(Path(a,'sphere_node_pair_matrix_248832.csv.gz').read_bytes(),Path(b,'sphere_node_pair_matrix_248832.csv.gz').read_bytes())
 def test_db_roles(self):
  with tempfile.TemporaryDirectory() as d:
   db=initialize_db(Path(d)/'x.sqlite',self.s)
   self.assertEqual(db.execute('select count(*) from nodes').fetchone()[0],1728)
   self.assertEqual(db.execute('select count(*) from spheres').fetchone()[0],144)
   self.assertEqual(db.execute('select count(*) from topics').fetchone()[0],0)
   db.close()
 def test_source_card(self):
  with tempfile.TemporaryDirectory() as d:
   db=initialize_db(Path(d)/'x.sqlite',self.s)
   c=source_card(db,'H01.S01.N01',self.s.registry_sha)
   self.assertIn('AXG1',c['display']['authored_axg1']);self.assertFalse(c['display']['gf7_model']['atlas_semantic_equivalence']);db.close()
 def test_topic_view_typed_with_memory(self):
  with tempfile.TemporaryDirectory() as d:
   db=initialize_db(Path(d)/'db.sqlite',self.s)
   db.executemany('INSERT INTO topics VALUES(?,?,?)',[('T10','synthetic topic A','UNREVIEWED'),('T11','synthetic topic B','UNREVIEWED')]);db.executemany('INSERT INTO topic_candidates VALUES(?,?,?,?)',[('T10','H01.S01.N01',1,'UNREVIEWED'),('T11','H01.S01.N01',2,'UNREVIEWED'),('T11','H02.S01.N01',1,'UNREVIEWED')]);db.commit()
   m=LocalMemory(Path(d)/'m.sqlite')
   checkpoint={'expected_tip':'0'*64,'expected_count':0}
   prior=topic_view(db,'H01.S01.N01',m,memory_checkpoint=checkpoint);self.assertEqual(prior['items'][0]['topic_id'],'T10')
   receipt=m.append({'event_id':'note1','mode':'WORK','scope':'SYNTHETIC_LOCAL_REVIEW','coordinate':'H01.S01.N01','topic_id':'T11','action':'NOTE','source_ref':'urn:atlas:synthetic:test','source_digest':'a'*64},**checkpoint)
   checkpoint={'expected_tip':receipt['event_hash'],'expected_count':receipt['count']}
   after=topic_view(db,'H01.S01.N01',m,memory_checkpoint=checkpoint)
   self.assertEqual(after['items'][0]['topic_id'],'T11')
   self.assertFalse(after['semantic_equivalence_approved'])
   near=shared_topic_neighbors(db,'H01.S01.N01');self.assertEqual(near['total_candidate_paths'],1);self.assertFalse(near['subject_equivalence'])
   m.close();db.close()
 def test_benchmark_no_hosted_claim(self):
  b=benchmark(self.idx,repeat=5);self.assertTrue(b['paired_output_parity']);self.assertFalse(b['hosted_swarmchat_measured'])
 def test_view_validation(self):
  with tempfile.TemporaryDirectory() as d:
   db=initialize_db(Path(d)/'x.sqlite',self.s)
   with self.assertRaises(ValueError):source_card(db,'H00.S00.N00',self.s.registry_sha)
   with self.assertRaises(ValueError):topic_view(db,'H01.S01.N01',limit=1000)
   with self.assertRaises(ValueError):shared_topic_neighbors(db,'H01.S01.N01',limit=0)
   db.close()
