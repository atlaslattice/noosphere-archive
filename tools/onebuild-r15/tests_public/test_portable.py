"""Public-safe, dependency-free synthetic tests for R15 source patcher.
Does not require owner-private Ariadne registry or R14 viewer bytes.
"""
from pathlib import Path
import unittest,sys,subprocess,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from build_adaptive import transform,EXPECTED_R14_SHA256

START='const stableProfiles=new Map();\nfor(const n of all){'
END='// META145: CPU-microbenchmarkable, accessible 48-result window.'
INDEX="  indexText.set(n.id,[n.id,n.name,n.sphere,...Object.values(n.projects)].join(' ').toLowerCase());"
CALL="&&(!r||(r==='with'?n.reading:!n.reading))&&(!q||indexText.get(n.id).includes(q)));"

def fixture():
    return '<script id="dataset" type="application/json">SYNTHETIC_ONLY</script>\n'+START+'''
 const projects=new Map();
 const stableEdition=meta.editions.map(e=>'This edition: '+e.implementation);
 function renderNode(){stableTitle.textContent=n.title;x.baseline.textContent=line;}
}'''+END+'''
const indexText=new Map();for(const n of all){
'''+INDEX+'''
}
function filter(){const q='';const x=foo'''+CALL+'''}
<button id="metric-open">Inspect measured node latency</button>
'''+'// Read-only, local benchmark and same-HTML correctness hooks. These do NOT\n'

class PortableTests(unittest.TestCase):
 def test_transform_succeeds(self):self.assertIn('function getStableProfile',transform(fixture()))
 def test_bounded_cache(self):self.assertIn('MAX_STABLE_PROFILES=96;',transform(fixture()))
 def test_no_lru_hot_path_mutation(self):self.assertIn('if(old)return old;',transform(fixture()))
 def test_source_preserved(self):
  f=fixture();a=transform(f);self.assertIn('SYNTHETIC_ONLY',a);self.assertEqual(f.count('SYNTHETIC_ONLY'),a.count('SYNTHETIC_ONLY'))
 def test_search_prebuilt(self):self.assertIn(INDEX,transform(fixture()))
 def test_predicate_unchanged(self):self.assertIn(CALL,transform(fixture()))
 def test_no_new_tool_action(self):
  s=transform(fixture());self.assertNotIn('fetch(',s);self.assertNotIn('swarm_post_message',s)
 def test_must_have_single_anchor(self):
  with self.assertRaises(ValueError):transform(fixture()+START)
 def test_missing_navigation_anchor_rejected(self):
  with self.assertRaises(ValueError):transform(fixture().replace(END,'UNKNOWN'))
 def test_unexpected_render_contract_rejected(self):
  with self.assertRaises(ValueError):transform(fixture().replace('x.baseline.textContent=line;','noop'))
 def test_reject_without_real_source_digest(self):
  with tempfile.TemporaryDirectory() as d:
   inp=Path(d)/'mock.html';out=Path(d)/'out.html';inp.write_text(fixture())
   cmd=[sys.executable,str(Path(__file__).resolve().parents[1]/'src/build_adaptive.py'),str(inp),str(out)]
   r=subprocess.run(cmd,capture_output=True,text=True)
   self.assertNotEqual(r.returncode,0);self.assertIn('R14_SOURCE_DIGEST_MISMATCH',r.stderr)
 def test_source_digest_is_shaped(self):self.assertRegex(EXPECTED_R14_SHA256,r'^[0-9a-f]{64}$')

if __name__=='__main__':unittest.main()
