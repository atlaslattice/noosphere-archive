import json, tempfile, unittest, zlib
from pathlib import Path
from src.continuation_guard import *

class TestGuard(unittest.TestCase):
    def test_non_object_fails_closed(self):
        p=wire.Policy(1,6)
        for raw in (b'[]',b'null',b'{"x":NaN}',b'{"x":"\\ud800"}'):
            core=b'GF9R2'+len(raw).to_bytes(2,'big')+raw
            frame=core+zlib.crc32(core).to_bytes(4,'big')
            self.assertIsNone(recover_bit_majority(frame,p)[0])
    def test_two_distinct_bit_errors(self):
        p=wire.Policy(3,6);msg=wire.make_message(11,4,p);raw=wire.encode(msg,p)
        frame=bytearray(wire.serialize_repetition(raw,p));frame[0]^=1;frame[1]^=2
        self.assertIsNone(wire.recover(bytes(frame),p)[0])
        self.assertEqual(recover_bit_majority(bytes(frame),p)[0],msg)
    def test_wrong_crc_fails(self):
        p=wire.Policy(3,6);frame=bytearray(wire.serialize_repetition(wire.encode(wire.make_message(0,7,p),p),p))
        for i in (30,31,32):frame[i]^=1
        self.assertIsNone(recover_bit_majority(bytes(frame),p)[0])
    def test_twelve_fixture_boundaries(self):
        for m in (0,11,12,71,143):self.assertEqual(len(lesson_checks(m)),12)
    def test_external_tip_and_count_required(self):
        s=evo.new_state()
        with self.assertRaises(ValueError):strict_replay(s,[],expected_tip='a'*64,expected_count=0)
        self.assertEqual(strict_replay(s,[],expected_tip=evo.GENESIS,expected_count=0)['status'],'ANCHOR_AND_RECORDED_DECISION_REPLAY_PASS')
    def test_resealed_forged_decision_is_held(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'forged.jsonl';s=evo.new_state()
            # Build an explicitly fabricated record; no new experiment is executed.
            p=wire.BASE;q=evo.mutate(p,0);e={'trial':1,'module':'H01.S01','chapter':1,'old':{'repetition':p.repetition,'decimals':p.decimals},'proposed':{'repetition':q.repetition,'decimals':q.decimals},'new_policy':{'repetition':q.repetition,'decimals':q.decimals},'accepted':True,'trial_seed_sha256':'forged'}
            tip=evo.event_hash(evo.GENESIS,e);f.write_text(json.dumps({'prior':evo.GENESIS,'event':e,'hash':tip})+'\n');s['head']=tip;s['next_index']=1;s['counts']['evaluated']=1;s['counts']['accepted']=1;s['policies'][0]=e['new_policy']
            self.assertEqual(evo.verify_log(s,[f])['status'],'CHAIN_AND_POLICY_REPLAY_PASS')
            with self.assertRaises(ValueError):strict_replay(s,[f],expected_tip=tip,expected_count=1)
