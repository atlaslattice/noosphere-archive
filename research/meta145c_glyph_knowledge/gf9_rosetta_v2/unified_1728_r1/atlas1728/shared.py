"""Shared nonauthoritative utility functions for offline Atlas verification."""
from __future__ import annotations
import hashlib,json,math,re,unicodedata,zlib
from .source import sha,canon,DOMAIN,METHOD,HSN

WORDS=re.compile(r'[^\W_]+', re.UNICODE)
CHAPTER_OPS=('CONSENT','COUNT','RATIO','ROTATE','CLOCK','ELEMENT','LATTICE','RESONANCE','HOLD','TRANSFORM','SONIFY','TEACH')
GF7_BANDS=((.1,1),(1,5),(5,20),(20,80),(80,200),(200,500),(500,1000),(1000,2000),(2000,5000),(5000,20000),(20000,100000),(100000,1000000))
GF7_MODES=((1,1),(1,2),(2,1),(2,2),(1,3),(3,1),(2,3),(3,2),(3,3),(1,4),(4,1),(4,4))
GF7_MATERIALS=tuple((mat,ratio) for mat in ('aluminum','steel','borosilicate') for ratio in (1,1.25,1.5,2))


def terms(s: str) -> frozenset[str]:
    if not isinstance(s,str):raise ValueError('QUERY_NOT_STRING')
    s=unicodedata.normalize('NFKC',s).casefold()
    return frozenset(tok for tok in WORDS.findall(s) if len(tok)>1)


def identity_address(nid:str,root_sha:str)->str:
    if not HSN.fullmatch(nid) or not re.fullmatch('[a-f0-9]{64}',root_sha):raise ValueError('ADDRESS_INVALID')
    code=sha(f'AXG1|{root_sha}|{nid}'.encode())[:12]
    return f'AXG1:{root_sha[:12]}:{nid}:{code}'


def reverse_address(glyph:str,root_sha:str)->str:
    if not isinstance(glyph,str):raise ValueError('BAD_GLYPH')
    items=glyph.split(':')
    if len(items)!=4 or items[0]!='AXG1':raise ValueError('NOT_AXG1_NAMESPACE')
    nid=items[2]
    if identity_address(nid,root_sha)!=glyph:raise ValueError('GLYPH_CHECKSUM_OR_EDITION_MISMATCH')
    return nid


def synthetic_plate_frequency(module:int,chapter:int)->dict:
    # Independent simple reference for the GF9/R2 source's SSSS rectangular model.
    if type(module)!=int or type(chapter)!=int or not 0<=module<144 or not 0<=chapter<12:raise ValueError('BOUNDS')
    from math import pi,sqrt
    E=2e11;rho=7850.;nu=.3;h=.001;a=.3;b=.3
    # Original GF9 material properties are derived from its separate source; in this
    # standalone candidate model, these values are DECLARED ASSUMPTIONS, not data.
    m=1+module%3;n=1+(module//12)%3
    def f(hh,aa,bb):
        D=E*hh**3/(12*(1-nu**2))
        return pi/2*sqrt(D/(rho*hh))*((m/aa)**2+(n/bb)**2)
    ratio=1.015+((module*3+chapter*11)%17)/100.
    t=[h,a,b];t[chapter%3]*=ratio
    old=f(h,a,b);new=f(*t)
    return {'mode':[m,n],'baseline_hz':round(old,9),'changed_hz':round(new,9),
            'frequency_ratio':round(new/old,12),'changed_quantity':('thickness','width','height')[chapter%3],
            'status':'ANALYTIC_SSSS_NOMINAL_NOT_MEASURED'}


def strict_wire(value:dict)->bytes:
    raw=canon(value)
    if len(raw)>4096:raise ValueError('WIRE_SIZE')
    frame=b'GF9A'+len(raw).to_bytes(2,'big')+raw
    return frame+zlib.crc32(frame).to_bytes(4,'big')


def read_wire(raw:bytes)->dict:
    if not isinstance(raw,bytes) or not 10<=len(raw)<=4106 or raw[:4]!=b'GF9A':raise ValueError('WIRE_FORMAT')
    length=int.from_bytes(raw[4:6],'big')
    if length!=len(raw)-10 or zlib.crc32(raw[:-4])!=int.from_bytes(raw[-4:],'big'):raise ValueError('WIRE_TAMPER')
    def uniq(items):
        d={}
        for k,v in items:
            if k in d:raise ValueError('DUPLICATE_WIRE_KEY')
            d[k]=v
        return d
    obj=json.loads(raw[6:-4].decode('ascii'),object_pairs_hook=uniq)
    if canon(obj)!=raw[6:-4]:raise ValueError('NONCANONICAL_WIRE')
    return obj
