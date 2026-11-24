from __future__ import annotations
import unittest,copy,hashlib,tempfile,sqlite3
from pathlib import Path
from atlas1728 import Corpus,compile_build,verify_build,benchmark_lookup
from atlas1728.source import check_registry,ARIADNE_SHA,OPENALEX_SHA
from atlas1728.index import SourceIndex
from atlas1728.shared import identity_address,reverse_address,strict_wire,read_wire,synthetic_plate_frequency
from atlas1728.modules import ALL,NAMES
from atlas1728.engine import persist_sqlite
from atlas1728.gf9_cache import CompiledGF9Packets

class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=Corpus.synthetic();cls.idx=SourceIndex(cls.c);cls.build=compile_build(cls.c)
    def test_twelve_executable_house_modules(self):self.assertEqual(len(ALL),12);self.assertEqual(len(NAMES),12)
    def test_counts(self):
        b=self.build
        self.assertEqual((len(b['nodes']),len(b['pathways']),len(b['modules']),len(b['metrics'])),(1728,144,12,1728))
        self.assertEqual(b['summary']['module_node_checks'],20736)
    def test_exact_registry_roles(self):
        self.assertEqual(sum(n['kind']=='EPISTEMIC_META' for n in self.c.nodes.values()),720)
        self.assertEqual(sum(n['kind']=='DOMAIN_SPECIALIZATION' for n in self.c.nodes.values()),1008)
    def test_all_node_metadata_and_digest(self):self.assertTrue(verify_build(self.build,self.c))
    def test_all_144_pathways_twelve_works(self):
        self.assertTrue(all(len(p['node_upgrade_digests'])==12 for p in self.build['pathways']))
        self.assertEqual(len(set(p['lens_digest'] for p in self.build['pathways'])),144)
    def test_1728_unique_upgrade_ids(self):
        self.assertEqual(len(set(x['change_id'] for x in self.build['nodes'])),1728)
        self.assertTrue(all(len(x['module_output_digests'])==12 for x in self.build['nodes']))
    def test_all_modules_have_real_outputs(self):
        for n in self.build['nodes']:
            self.assertEqual([m['result']['pass'] for m in n['module_outputs']],[True]*12)
    def test_1727_comparison_improvements_not_fake_1728(self):
        self.assertEqual(sum(x['strict_improvement'] for x in self.build['metrics']),1727)
        self.assertEqual(self.build['summary']['baseline_lookup_comparisons'],1493856)
        self.assertEqual(self.build['summary']['indexed_lookup_comparisons'],1728)
    def test_every_node_indexed_exact(self):
        for nid in self.idx.ids:self.assertEqual(self.idx.linear_find(nid)[0],self.idx.indexed_find(nid)[0])
    def test_all_sphere_search_parity(self):
        for sid in self.c.spheres:
            query=self.c.spheres[sid]['name']
            self.assertEqual(self.idx.search(query),self.idx.linear_search(query))
    def test_domain_and_epistemic_filter_parity(self):
        for role in ('DOMAIN','METHOD'):
            self.assertEqual(self.idx.search('Synthetic coordinate',role),self.idx.linear_search('Synthetic coordinate',role))
    def test_1728_reversible_glyph(self):
        for nid in self.c.nodes:
            g=identity_address(nid,self.c.registry_sha)
            self.assertEqual(reverse_address(g,self.c.registry_sha),nid)
    def test_wrong_edition_held(self):
        x=identity_address('H01.S01.N01',self.c.registry_sha)
        with self.assertRaises(ValueError):reverse_address(x,'a'*64)
    def test_wrong_glyph_namespace_held(self):
        with self.assertRaises(ValueError):reverse_address('GF7.B01.M01.C01',self.c.registry_sha)
    def test_crc_tamper_held(self):
        b=strict_wire({'hsn':'H01.S01.N01','scope':'SIMULATION_ONLY'})
        self.assertEqual(read_wire(b)['hsn'],'H01.S01.N01')
        bad=bytearray(b);bad[9]^=1
        with self.assertRaises(ValueError):read_wire(bytes(bad))
    def test_source_shape_tamper(self):
        d=copy.deepcopy(self.c.nodes)
        d.pop('H01.S01.N01')
        with self.assertRaises(ValueError):check_registry({'houses':self.c.houses,'spheres':self.c.spheres,'nodes':d,'catalog':{}})
    def test_source_pin_tamper(self):
        a=self.build.copy();b=copy.deepcopy(self.build);b['summary']['source_sha256']='f'*64
        with self.assertRaises(ValueError):verify_build(b,self.c)
    def test_node_output_tamper(self):
        b=copy.deepcopy(self.build);b['nodes'][7]['module_outputs'][1]['result']['balance']=99999
        with self.assertRaises(ValueError):verify_build(b,self.c)
    def test_private_mode_not_transferred(self):
        for n in self.build['nodes']:
            self.assertFalse(n['private_creative_import'])
            self.assertFalse(n['gpt_weights_changed'])
    def test_canon_and_host_held(self):
        self.assertEqual(self.build['summary']['genuinely_measured_civilizational_gains'],0)
        self.assertFalse(self.build['summary']['host_deployed'])
    def test_sqlite_integrity(self):
        with tempfile.TemporaryDirectory() as td:
            r=persist_sqlite(self.build,Path(td)/'v.sqlite')
            self.assertEqual(r['nodes'],1728)
            with sqlite3.connect(r['database']) as db:
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                self.assertEqual(db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0],1728)
    def test_benchmark_same_results(self):
        b=benchmark_lookup(self.c,passes=5)
        self.assertTrue(b['exact_source_result_parity'])
        self.assertEqual(b['query_count_per_pass'],1728)
    def test_144_sphere_lens_digest_chain(self):
        x=self.build['pathways'];self.assertEqual(x[0]['previous_path_digest'],'0'*64)
        for i in range(1,144):self.assertEqual(x[i]['previous_path_digest'],x[i-1]['digest_sha256'])
    def test_h10_cultural_scope_specific(self):
        first=next(x for x in self.build['nodes'] if x['coordinate']=='H10.S01.N01')
        self.assertTrue(first['module_outputs'][9]['result']['indigenous_specific_review'])
    def test_model_not_measurement(self):
        ref=synthetic_plate_frequency(0,0)
        self.assertEqual(ref['status'],'ANALYTIC_SSSS_NOMINAL_NOT_MEASURED')
    def test_invalid_research_role(self):
        with self.assertRaises(ValueError):self.idx.search('xy','NONSENSE')

class PacketCacheTests(unittest.TestCase):
    def _factory(self,mod,ch):
        return {'m':f'H{mod//12+1:02d}.S{mod%12+1:02d}','c':ch+1,'op':('CONSENT','COUNT','RATIO','ROTATE','CLOCK','ELEMENT','LATTICE','RESONANCE','HOLD','TRANSFORM','SONIFY','TEACH')[ch],
                'a':ARIADNE_SHA[:12],'scope':'SYNTHETIC_WORK','numerical':'1.0'}
    def test_cache_inherits_original_generator(self):
        c=CompiledGF9Packets(factory=self._factory,root_sha=ARIADNE_SHA,generator_sha='a'*64)
        self.assertEqual(len(c.packets),1728)
        self.assertEqual(c.get('H11.S08.N02',root_sha=ARIADNE_SHA,generator_sha='a'*64),self._factory(127,1))
    def test_cache_rejects_stale_code(self):
        c=CompiledGF9Packets(factory=self._factory,root_sha=ARIADNE_SHA,generator_sha='a'*64)
        with self.assertRaises(ValueError):c.get('H01.S01.N01',root_sha=ARIADNE_SHA,generator_sha='b'*64)
    def test_cache_rejects_claimed_host_grants(self):
        c=CompiledGF9Packets(factory=self._factory,root_sha=ARIADNE_SHA,generator_sha='a'*64)
        with self.assertRaises(ValueError):c.get('H01.S01.N01',root_sha=ARIADNE_SHA,generator_sha='a'*64,host_rights={'allow':True})
    def test_cache_rejects_private_mode(self):
        c=CompiledGF9Packets(factory=self._factory,root_sha=ARIADNE_SHA,generator_sha='a'*64)
        with self.assertRaises(ValueError):c.get('H01.S01.N01',root_sha=ARIADNE_SHA,generator_sha='a'*64,request_mode='PALACE')

if __name__=='__main__':unittest.main()
