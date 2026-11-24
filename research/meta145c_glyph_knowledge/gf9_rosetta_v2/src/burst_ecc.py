"""Equal-budget interleaved extended Hamming (8,4) + XOR erasure recovery. Review only."""
import hashlib,random
from . import protocol as w
from .continuation_guard import recover_bit_majority
P=w.Policy(3,6); ONE=w.Policy(1,6)
def word(n):
    b=[0]*9
    for k,i in enumerate((3,5,6,7)): b[i]=(n>>k)&1
    for p in (1,2,4): b[p]=sum(b[i] for i in range(1,8) if i&p and i!=p)%2
    b[8]=sum(b[1:8])%2
    return sum(b[i]<<(i-1) for i in range(1,9))
WORDS=tuple(word(n) for n in range(16))
D=tuple(next((n for n,x in enumerate(WORDS) if (x^v).bit_count()<=1),None) for v in range(256))
def encode(core):
    if type(core) is not bytes or not 11<=len(core)<=2059: raise ValueError('BOUNDS')
    return bytes(WORDS[x>>4] for x in core)+bytes(WORDS[x&15] for x in core)+bytes(WORDS[(x>>4)^(x&15)] for x in core)
def decode(frame):
    if type(frame) is not bytes or len(frame)%3 or not 33<=len(frame)<=6177: return None,'HOLD_BOUNDS'
    n=len(frame)//3; out=bytearray()
    for x,y,z in zip(frame[:n],frame[n:2*n],frame[2*n:]):
        a,b,c=D[x],D[y],D[z]
        if sum(v is None for v in (a,b,c))>1: return None,'HOLD_ERASURE'
        if a is None: a=b^c
        elif b is None: b=a^c
        elif c is None: c=a^b
        if a^b!=c: return None,'HOLD_PARITY'
        out.append(a*16+b)
    try: return w.recover(bytes(out),ONE)
    except (ValueError,TypeError,OverflowError,RecursionError): return None,'HOLD_MALFORMED'
def interleave_decode(frame):
    if type(frame) is not bytes or len(frame)%3: return None,'HOLD_BOUNDS'
    n=len(frame)//3
    return recover_bit_majority(bytes(v for t in zip(frame[:n],frame[n:2*n],frame[2*n:]) for v in t),P)
def strict_message(msg,m,c): return type(msg) is dict and type(msg.get('c')) is int and w.valid_message(msg,m,c)
def mask(n,s,seed):
    rng=random.Random(seed); out=bytearray(n)
    if s=='burst':
        start=rng.randrange(n-15)
        for i in range(start,start+16): out[i]^=rng.randrange(1,256)
    else:
        if s=='correlated':
            start=rng.randrange(n-7); bit=1<<rng.randrange(8)
            for i in range(start,start+8): out[i]^=bit
        for i in range(n):
            if rng.random()<(.025 if s=='iid' else .01): out[i]^=1<<rng.randrange(8)
    return out
def benchmark():
    methods={'adjacent_majority':(lambda b:w.serialize_repetition(b,P),lambda b:recover_bit_majority(b,P)), 'interleaved_majority':(lambda b:b*3,interleave_decode),'hamming_xor_interleaved':(encode,decode)}
    results={}; ns='GF9-R2-CONT03-BURST-HOLDOUT-V1'
    for s in ('iid','burst','correlated'):
        r={k:dict(exact=0,wrong_returned=0,rejected=0,wire_bytes=0,frames=0) for k in methods}
        for m in range(144):
            for c in range(12):
                msg=w.make_message(m,c,P); core=w.encode(msg,P); noise=mask(3*len(core),s,int.from_bytes(hashlib.sha256(f'{ns}:{s}:{m}:{c}'.encode()).digest()[:8],'big'))
                for name,(enc,dec) in methods.items():
                    frame=enc(core)
                    if len(frame)!=len(noise): raise ValueError('BUDGET')
                    found,_=dec(bytes(a^b for a,b in zip(frame,noise))); row=r[name];row['frames']+=1;row['wire_bytes']+=len(frame)
                    row['exact' if found==msg and strict_message(found,m,c) else 'rejected' if found is None else 'wrong_returned']+=1
        results[s]=r
    return {'namespace':ns,'synthetic_only':True,'scenarios':results,'selection_on_holdout':False}
