"""GF9-R2 reproducible two-endpoint mathematical packet and noisy-channel codec.
This is a bounded synthetic machine-language experiment, not alien translation.
CRC is error detection, not sender authentication. Repetition is not optimal ECC.
"""
from __future__ import annotations
import hashlib,json,math,random,re,zlib
from dataclasses import dataclass,asdict
from .gf9_reference import frequency_hz,reference_packet,validate_reference
from .linguistics import BY_CODE,PROFILES,registry_digest

SCHEMA='atlas.gf9.rosetta-wire/v2'
MODEL='KIRCHHOFF_LOVE_SSSS_RECTANGULAR_LINEAR_ISOTROPIC'
CHAPTER_LABELS = [
 'Opt-in handshake and stopping','Counting and explicit numerals','Dimensionless proportions',
 'Coordinates and reversible rotations','Clocks and temporal references','Element identity and specimen',
 'Lattice structure and measurement','Nodal geometry and frequency','Counterexamples and boundary HOLD',
 'Material and geometry transformation','Declared frequency sonification','Teach-back and provisional semantics']
CHAPTER_OPS = ['CONSENT','COUNT','RATIO','ROTATE','CLOCK','ELEMENT','LATTICE','RESONANCE','HOLD','TRANSFORM','SONIFY','TEACH']
CODEC_R=(1,3,5)
CODEC_DEC=(2,3,4,6,8)
ANCHOR='07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6'

@dataclass(frozen=True)
class Policy:
    repetition:int=1
    decimals:int=3
    def __post_init__(self):
        if type(self.repetition)!=int or self.repetition not in CODEC_R or type(self.decimals)!=int or self.decimals not in CODEC_DEC:raise ValueError('INVALID_CODEC_POLICY')

BASE=Policy(1,3)

def canonical(obj)->bytes:
    if not isinstance(obj,dict):raise ValueError('WIRE_JSON_OBJECT_REQUIRED')
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8','strict')

def physical_problem(module:int,chapter:int):
    if type(module)!=int or not 0<=module<144 or type(chapter)!=int or not 0<=chapter<12:raise ValueError('UNBOUNDED_COORDINATE')
    ref=reference_packet(); validate_reference(ref)
    plate=ref['resonator']['properties'].copy()
    # The element sample is NOT presumed to mechanically produce these plate modes.
    m=1+module%3; n=1+(module//12)%3
    target=plate.copy()
    ratio=1.015 + ((module*3+chapter*11)%17)/100.0
    if chapter%3==0:target['thickness_m']*=ratio
    elif chapter%3==1:target['width_m']*=ratio
    else:target['height_m']*=ratio
    f0=frequency_hz(plate,(m,n));f1=frequency_hz(target,(m,n))
    # Ratio (not calibrated Hz) is the meaning-bearing mathematical payload.
    return {'mode':[m,n],'frequency_ratio':f1/f0,'old_frequency_hz':f0,'new_frequency_hz':f1,
       'change_factor':ratio,'changed_quantity':['thickness','width','height'][chapter%3],
       'model':MODEL,'source_status':'ANALYTIC_UNCALIBRATED'}

def make_message(module:int,chapter:int,policy:Policy,source_digest:str=ANCHOR)->dict:
    data=physical_problem(module,chapter)
    code=PROFILES[(module+chapter)%len(PROFILES)].code
    return {'v':2,'m':f'H{module//12+1:02d}.S{module%12+1:02d}',
       'c':chapter+1,'op':CHAPTER_OPS[chapter],
       's':code,'numerical':f"{data['frequency_ratio']:.{policy.decimals}f}",
       'grade':'MODELED_NOT_MEASURED','meaning':'MATHEMATICAL_EXERCISE_ONLY',
       'a':source_digest[:12], 'scope':'SYNTHETIC_WORK',
       'status':'HOLD' if chapter in (0,8,11) else 'CANDIDATE'}

def valid_message(msg:dict,module:int,chapter:int,tol:float=0.00005)->bool:
    if type(msg)!=dict or set(msg)!={'v','m','c','op','s','numerical','grade','meaning','a','scope','status'}:return False
    if type(msg['v'])!=int or msg['v']!=2 or msg['m']!=f'H{module//12+1:02d}.S{module%12+1:02d}' or msg['c']!=chapter+1 or msg['op']!=CHAPTER_OPS[chapter]:return False
    if msg['s']!=PROFILES[(module+chapter)%len(PROFILES)].code: return False
    if msg['grade']!='MODELED_NOT_MEASURED' or msg['scope']!='SYNTHETIC_WORK' or msg['meaning']!='MATHEMATICAL_EXERCISE_ONLY':return False
    if msg['a']!=ANCHOR[:12] or msg['status']!=('HOLD' if chapter in (0,8,11) else 'CANDIDATE'):return False
    if type(msg['numerical'])!=str or not re.fullmatch(r'[0-9]{1,3}(?:\.[0-9]{1,8})?',msg['numerical']):return False
    try:value=float(msg['numerical'])
    except ValueError:return False
    return abs(value-physical_problem(module,chapter)['frequency_ratio'])<=tol

def encode(msg:dict,policy:Policy)->bytes:
    if not isinstance(policy,Policy):raise ValueError('CODEC_POLICY_INVALID')
    raw=canonical(msg)
    if len(raw)>2048:raise ValueError('WIRE_BOUNDS')
    core=b'GF9R2'+len(raw).to_bytes(2,'big')+raw
    return core+zlib.crc32(core).to_bytes(4,'big')

def serialize_repetition(data:bytes,policy:Policy)->bytes:
    return bytes(b for a in data for b in [a]*policy.repetition)

def physical_noise(data:bytes,policy:Policy,seed:int,rate:float)->bytes:
    if not 0<=rate<=0.1:raise ValueError('CHANNEL_RATE_OUT_OF_BOUNDS')
    rng=random.Random(seed)
    # Comparable fixed 5-lane error draws per original byte regardless of policy.
    out=bytearray()
    for b in data:
        draw=[(rng.random(),rng.randrange(0,8)) for _ in range(5)]
        for lane in range(policy.repetition):
            flag,bit=draw[lane]
            out.append((b ^ (1<<bit)) if flag<rate else b)
    return bytes(out)

def recover(frame:bytes,policy:Policy)->tuple[dict|None,str]:
    r=policy.repetition
    if type(frame)!=bytes or len(frame)%r or len(frame)>16384:return None,'HOLD_BOUNDS'
    decoded=bytearray()
    for i in range(0,len(frame),r):
        part=frame[i:i+r]
        if r==1:decoded.append(part[0]);continue
        winner=max(set(part),key=lambda x:part.count(x))
        if part.count(winner)<=r//2:return None,'HOLD_NO_MAJORITY'
        decoded.append(winner)
    b=bytes(decoded)
    if len(b)<11 or not b.startswith(b'GF9R2'):return None,'HOLD_VERSION'
    length=int.from_bytes(b[5:7],'big')
    if length>2048 or len(b)!=5+2+length+4:return None,'HOLD_LENGTH'
    if zlib.crc32(b[:-4])!=int.from_bytes(b[-4:],'big'):return None,'HOLD_CRC'
    try:
        def unique(pairs):
            d={}
            for k,v in pairs:
                if k in d:raise ValueError('DUPLICATE_JSON_KEY')
                d[k]=v
            return d
        msg=json.loads(b[7:-4].decode('utf-8','strict'),object_pairs_hook=unique)
    except (ValueError,UnicodeError):return None,'HOLD_JSON'
    if canonical(msg)!=b[7:-4]:return None,'HOLD_NONCANONICAL'
    return msg,'RECOVERED_CRC_VERIFIED_NOT_AUTHENTICATED'

def evaluate(policy:Policy,module:int,chapter:int,seeds:tuple[int,...],rate:float)->dict:
    msg=make_message(module,chapter,policy)
    raw=encode(msg,policy)
    passes=0;rejected=0;postflight_holds=0;false_accepted=0
    for seed in seeds:
        damaged=physical_noise(raw,policy,seed,rate)
        found,status=recover(damaged,policy)
        if found is None:rejected+=1;continue
        if valid_message(found,module,chapter):passes+=1
        else:postflight_holds+=1
    n=len(seeds)
    # Distinguish robust recovery from mere source checksum detection.
    # Safety gate is nonoffsettable: no false physical/context claims can pass.
    score=passes/n - 0.029*(policy.repetition-1) - 0.001*max(0,policy.decimals-4)
    return {'passes':passes,'rejected':rejected,'postflight_holds':postflight_holds,'false_accepted':false_accepted,
      'frames':n,'score':round(score,9),'wire_bytes':len(raw)*policy.repetition,
      'rate':rate,'quantization':policy.decimals,'repetition':policy.repetition}

def channel_rate(module,chapter):
    # Synthetic communication noise, not an astronomical-link measurement.
    return [0.0025,0.006,0.011,0.018,0.027][(module*3+chapter)%5]
