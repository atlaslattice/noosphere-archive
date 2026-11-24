import unittest, copy, json, hashlib
from pathlib import Path
from src.protocol import *
from src.linguistics import *
from src.compiler import *
from src.ontology import bind_registry

class TestProtocol(unittest.TestCase):
 def test_144_by_12(self):
  for m in range(144):
   for c in range(12):
    v=make_message(m,c,Policy(3,6))
    self.assertTrue(valid_message(v,m,c),(m,c))
 def test_source_prefix(self):
  self.assertTrue(make_message(0,7,Policy(1,8))['a']==ANCHOR[:12])
  self.assertFalse(valid_message({**make_message(0,7,Policy(1,8)),'a':'deadbeef1234'},0,7))
 def test_each_script_reference_is_distinct_from_translation(self):
  self.assertEqual(len(PROFILES),18)
  for p in PROFILES:
   row=script_record(p.code)
   self.assertIsNone(row['translation'])
   self.assertEqual(row['script_code'],p.code)
 def test_sumerian_is_transliteration_not_meaning(self):
  x=script_record('Xsux','𒀀','a')
  self.assertEqual(ord('𒀀'),0x12000)
  self.assertIsNone(x['translation'])
  with self.assertRaises(ValueError):script_record('Xsux','𒀀','a',asserted_translation='steel')
 def test_maya_unencoded_sign_not_forged(self):
  with self.assertRaises(ValueError):script_record('Maya','abc')
 def test_unknown_script(self):
  with self.assertRaises(ValueError):script_record('ALIEN_KG8')
 def test_unicode_nfc(self):
  with self.assertRaises(ValueError):normalize_grapheme_label('e\u0301')
  self.assertEqual(normalize_grapheme_label('e\u0301',strict=False),'é')
  with self.assertRaises(ValueError):normalize_grapheme_label('\ud800')
 def test_gf9_original_style(self):
  s=original_style_grammar()
  self.assertFalse(s['phonetic_translation_claim'])
  self.assertIn('NO_TOLKIEN_SCRIPT_COPY',s['rights'])
 def test_repetition_higher_recovery_in_synthetic_case(self):
  m,c=17,9;rate=0.025;seeds=tuple(range(200,250))
  a=evaluate(Policy(1,6),m,c,seeds,rate)
  b=evaluate(Policy(5,6),m,c,seeds,rate)
  self.assertGreater(b['passes'],a['passes'])
 def test_crc_fail_closed(self):
  p=Policy(1,6);raw=bytearray(encode(make_message(0,7,p),p));raw[19]^=1
  msg,status=recover(bytes(raw),p)
  self.assertIsNone(msg);self.assertEqual(status,'HOLD_CRC')
 def test_recovered_packet_not_crypto_authenticated(self):
  p=Policy(3,6);raw=encode(make_message(0,7,p),p)
  msg,reason=recover(physical_noise(raw,p,23,0),p)
  self.assertTrue(valid_message(msg,0,7))
  self.assertIn('NOT_AUTHENTICATED',reason)
 def test_12_chapter_packet_holds(self):
  for c in range(12):
   self.assertEqual(make_message(0,c,Policy(3,6))['status']=='HOLD',c in [0,8,11])
 def test_mode_and_grid_real_calculations(self):
  p=physical_3d_glyph(17,7,grid=9)
  self.assertEqual(len(p['payload']['xyz']),9)
  self.assertTrue(validate_glyph(p))
  b=copy.deepcopy(p);b['payload']['xyz'][0][0][2]=0.5
  with self.assertRaises(ValueError):validate_glyph(b)
 def test_two_independent_notation_roundtrip(self):
  p=physical_3d_glyph(33,9,9)
  x=bridge_equivalence(p,serialized_earth(p),serialized_imperial_fiction(p))
  self.assertTrue(x['mathematics_reproduced'])
  self.assertFalse(x['script_lexicon_learned'])
  with self.assertRaises(ValueError):bridge_equivalence(p,serialized_earth(p),'GF7.B01.M01.C01')
 def test_sonification_explicit(self):
  x=sonify_metadata(0,7)
  self.assertAlmostEqual(x['input_hz']*x['sonification_scale'],x['rendered_hz'],7)
  self.assertTrue(x['no_audio_generated'])
 def test_12_chapter_exchange(self):
  data=twelve_chapter_synthetic_exchange(0)
  self.assertEqual(data['count'],12)
  self.assertFalse(data['actual_AI_to_AI_contact'])
 def test_original_registry_sha_only_private(self):
  path=Path(__file__).parents[1]/'private_inputs'/'ariadne_v07_atlas.json'
  if not path.exists():self.skipTest('exact private source absent')
  mods=bind_registry(path)
  self.assertEqual(len(mods),144)
  self.assertEqual(len(mods[0]['chapters']),12)
  self.assertEqual(sum(x['role']=='DOMAIN_SPECIALIZATION' for x in mods),84)
  corrupt=Path(__file__).parents[1]/'outputs'/'corrupt-test.json'
  try:
   corrupt.write_text('{}')
   with self.assertRaises(ValueError):bind_registry(corrupt)
  finally:corrupt.unlink(missing_ok=True)

if __name__=='__main__':unittest.main()
