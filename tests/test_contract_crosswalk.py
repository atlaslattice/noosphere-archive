"""Synthetic, no-network crosswalk tests. Never imports protected source bodies."""
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.contract_crosswalk import inspect,compare,load_raw


def raw(o):return json.dumps(o,sort_keys=True).encode()
def a():return {'schema_version':'atlas.evidence.graph/v0.1','purpose':'PUBLIC_EVIDENCE_REVIEW','graph_id':'fixture-a',
                  'nodes':[{'id':'src','type':'SourceSurface'}],'edges':[{'source':'src','target':'src','type':'derived_from'}]}
def b():return {'schema_version':'0.1.0','source_mode':'consented_work','raw_export_status':'raw_complete_hashed',
                 'source_roots':[{'id':'fictional-root'}],'lifecycle':{'stage':'CANDIDATE'},
                 'nodes':[{'id':'src','type':'SourceSurface'}],'edges':[{'source':'src','target':'src','type':'derived_from'}]}
class CrosswalkTests(unittest.TestCase):
    def test_a_variant(self):self.assertEqual(inspect(raw(a()),'PR14_GRAPH')['status'],'HOLD_CONTRACT_RECONCILIATION')
    def test_b_variant(self):self.assertEqual(inspect(raw(b()),'PR17_PACKET')['status'],'HOLD_CONTRACT_RECONCILIATION')
    def test_a_missing_graphid(self):
        p=a();p.pop('graph_id');self.assertIn('MISSING_VARIANT_FIELDS',inspect(raw(p),'PR14_GRAPH')['reasons'])
    def test_b_missing_rawstatus(self):
        p=b();p.pop('raw_export_status');self.assertIn('RAW_EXPORT_NOT_COMPLETE_HASHED',inspect(raw(p),'PR17_PACKET')['reasons'])
    def test_wrong_pr14_version(self):
        p=a();p['schema_version']='x';self.assertIn('WRONG_PR14_EDITION',inspect(raw(p),'PR14_GRAPH')['reasons'])
    def test_wrong_pr17_version(self):
        p=b();p['schema_version']='x';self.assertIn('WRONG_PR17_EDITION',inspect(raw(p),'PR17_PACKET')['reasons'])
    def test_pr14_no_work_rights(self):self.assertEqual(inspect(raw(a()),'PR14_GRAPH')['boundary_notes']['rights_field'],'NOT_DEFINED_AT_GRAPH_ROOT')
    def test_source_mode_not_string(self):
        p=b();p['source_mode']=42;self.assertIn('SOURCE_MODE_NOT_PERMITTED',inspect(raw(p),'PR17_PACKET')['reasons'])
    def test_private_play_redacted(self):
        p=b();p['source_mode']='play';p['protected_body']='secret-token'
        self.assertNotIn('secret-token',json.dumps(inspect(raw(p),'PR17_PACKET')))
    def test_private_imagine(self):
        p=b();p['source_mode']='imagine';self.assertEqual(inspect(raw(p),'PR17_PACKET')['status'],'HOLD_PRIVATE_BOUNDARY')
    def test_private_palace(self):
        p=b();p['source_mode']='palace';self.assertEqual(inspect(raw(p),'PR17_PACKET')['status'],'HOLD_PRIVATE_BOUNDARY')
    def test_unknown_variant(self):
        with self.assertRaises(ValueError):inspect(raw(a()),'AUTO')
    def test_duplicate_key(self):
        with self.assertRaises(ValueError):load_raw(b'{"canon":false,"canon":true}')
    def test_nonfinite(self):
        with self.assertRaises(ValueError):load_raw(b'{"score":NaN}')
    def test_bad_utf8(self):self.assertEqual(inspect(b'\xff\xfe','PR14_GRAPH')['status'],'HOLD_INVALID_SOURCE')
    def test_nonobject(self):self.assertEqual(inspect(b'[]','PR17_PACKET')['status'],'HOLD_INVALID_SOURCE')
    def test_bad_nodes(self):
        p=a();p['nodes']={};self.assertIn('MISSING_NODE_OR_EDGE_LIST',inspect(raw(p),'PR14_GRAPH')['reasons'])
    def test_bad_edges(self):
        p=b();p['edges']=None;self.assertIn('MISSING_NODE_OR_EDGE_LIST',inspect(raw(p),'PR17_PACKET')['reasons'])
    def test_partial_not_pass(self):
        p=b();p['raw_export_status']='raw_partial';self.assertIn('RAW_EXPORT_NOT_COMPLETE_HASHED',inspect(raw(p),'PR17_PACKET')['reasons'])
    def test_equal_counts_not_equality(self):
        v=compare(raw(a()),raw(b()));self.assertFalse(v['semantic_equal']);self.assertFalse(v['migration_authorized'])
    def test_mismatched_counts(self):
        p=b();p['nodes'].append({'id':'different'});self.assertIn('NODE_CARDINALITY_DIVERGES',compare(raw(a()),raw(p))['holds'])
    def test_mismatched_edges(self):
        p=b();p['edges']=[];self.assertIn('EDGE_CARDINALITY_DIVERGES',compare(raw(a()),raw(p))['holds'])
    def test_nonlethal_non_authority(self):
        x=compare(raw(a()),raw(b()));self.assertEqual(x['authority_effect'],'NONE');self.assertFalse(x['deployment'])
    def test_preserves_distinct_digests(self):
        x=compare(raw(a()),raw(b()));self.assertNotEqual(x['variant_digests']['PR14_GRAPH'],x['variant_digests']['PR17_PACKET'])
    def test_ignores_same_label_inference(self):
        p=b();p['nodes']=[{'id':'src','name':'same as a'}];self.assertFalse(compare(raw(a()),raw(p))['semantic_equal'])
    def test_source_content_not_exported(self):
        p=a();p['notes']='PRIVATE TEST FOO';self.assertNotIn('PRIVATE TEST FOO',json.dumps(inspect(raw(p),'PR14_GRAPH')))
    def test_missing_source_hold(self):
        p=b();p.pop('lifecycle');self.assertEqual(inspect(raw(p),'PR17_PACKET')['status'],'HOLD_SOURCE_SHAPE')
    def test_edit_original_not_mutated(self):
        p=a();original=json.dumps(p);inspect(raw(p),'PR14_GRAPH');self.assertEqual(json.dumps(p),original)

if __name__=='__main__':unittest.main()