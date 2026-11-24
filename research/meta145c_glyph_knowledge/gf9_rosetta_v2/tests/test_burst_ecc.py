import unittest
from itertools import combinations
from src import burst_ecc as b
from src import protocol as w
class ECC(unittest.TestCase):
    def test_distance(self): self.assertEqual(min((x^y).bit_count() for x,y in combinations(b.WORDS,2)),4)
    def test_single_double(self):
        for n,x in enumerate(b.WORDS):
            self.assertEqual(b.D[x],n)
            for i in range(8): self.assertEqual(b.D[x^(1<<i)],n)
            for i,j in combinations(range(8),2): self.assertIsNone(b.D[x^(1<<i)^(1<<j)])
    def test_roundtrip(self):
        for m in (0,71,143):
            for c in range(12):
                msg=w.make_message(m,c,b.P); core=w.encode(msg,b.P); frame=b.encode(core)
                self.assertEqual(len(frame),3*len(core)); self.assertEqual(b.decode(frame)[0],msg)
    def test_erasure(self):
        msg=w.make_message(0,0,b.P); core=w.encode(msg,b.P); n=len(core); frame=bytearray(b.encode(core))
        for i in range(n): frame[i]^=3
        self.assertEqual(b.decode(bytes(frame))[0],msg);frame[n]^=3;self.assertIsNone(b.decode(bytes(frame))[0])
    def test_bounds(self):
        for frame in (b'',b'x'*34,b'x'*10000,bytearray(36)): self.assertIsNone(b.decode(frame)[0])
    def test_bool_chapter(self):
        msg=w.make_message(0,0,b.P);msg['c']=True;self.assertFalse(b.strict_message(msg,0,0))
