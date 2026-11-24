import unittest,tempfile,json
from pathlib import Path
from src.bridges import inspect_r10_evidence_db,inspect_iron_empire_overlay
from src.glyph import REGISTRY_SHA
class PublicBridgeTests(unittest.TestCase):
 def test_missing_r10_fails(self):
  with self.assertRaises(Exception):inspect_r10_evidence_db('/no/such/file.sqlite')
 def test_invalid_iron_version(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'x.json';f.write_text(json.dumps({'schema':'bogus','registryDigest':REGISTRY_SHA}))
   with self.assertRaises(ValueError):inspect_iron_empire_overlay(f)
 def test_no_canon_forgery(self):
  with tempfile.TemporaryDirectory() as d:
   j={'schema':'iron-empire.ariadne-house-review-overlay/v0.9','registryDigest':REGISTRY_SHA,'totalHouseSlots':12,'totalSphereSlots':144,'totalNodePositions':1728,'canonChanged':True,'status':'AUTHOR_REVIEW_REQUIRED','completedFilmEdits':0,'approvedTopicLinks':0,'houses':[]}
   f=Path(d)/'x.json';f.write_text(json.dumps(j))
   with self.assertRaises(ValueError):inspect_iron_empire_overlay(f)
