"""Typed HSN/AXG1/GF7 coordinate adapter. The namespaces are NOT equivalent.

This public-safe module contains *new authored* AXG1 routing tokens. It never
claims to reconstruct historic Krakoan, KG8, Tolkien languages, acoustic data,
physical resonance or a deployed glyph runtime.
"""
from __future__ import annotations
import hashlib
import re

HSN_RE = re.compile(r'^H(0[1-9]|1[0-2])\.S(0[1-9]|1[0-2])\.N(0[1-9]|1[0-2])$')
GF7_RE = re.compile(r'^GF7\.B(0[1-9]|1[0-2])\.M(0[1-9]|1[0-2])\.C(0[1-9]|1[0-2])$')
AXG_RE = re.compile(r'^AXG1:([0-9a-f]{12}):(H(?:0[1-9]|1[0-2])\.S(?:0[1-9]|1[0-2])\.N(?:0[1-9]|1[0-2])):([0-9a-f]{12})$')
GF7_BANDS = (
 (0.1,1.0), (1,5), (5,20), (20,80), (80,200), (200,500),
 (500,1000), (1000,2000), (2000,5000), (5000,20000),
 (20000,100000), (100000,1000000)
)
GF7_MODES=((1,1),(1,2),(2,1),(2,2),(1,3),(3,1),(2,3),(3,2),(3,3),(1,4),(4,1),(4,4))
GF7_MATERIALS=tuple((m,a) for m in ('aluminum','steel','borosilicate') for a in (1,1.25,1.5,2))
GLYPHFORGE_HISTORIC_NAMES=('HA-GNOME-HOORAY-01','HA-GNOME-HOORAY-REV','HA-SHPONGLE-HOORAY-CYM')
REGISTRY_SHA='07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6'


def hsn_parts(hsn: str)->tuple[int,int,int]:
    m=HSN_RE.fullmatch(hsn) if isinstance(hsn,str) else None
    if not m:raise ValueError('INVALID_HSN')
    return tuple(int(i) for i in m.groups())


def gf7_parts(gf7: str)->tuple[int,int,int]:
    m=GF7_RE.fullmatch(gf7) if isinstance(gf7,str) else None
    if not m:raise ValueError('INVALID_GF7')
    return tuple(int(i) for i in m.groups())


def positional_gf7(hsn:str)->str:
    """A numerical lookup *analogy*, not an HSN ontology ↔ physical-mode identity."""
    h,s,n=hsn_parts(hsn)
    return f'GF7.B{h:02d}.M{s:02d}.C{n:02d}'


def gf7_positional_hsn(gf7:str)->str:
    b,m,c=gf7_parts(gf7)
    return f'H{b:02d}.S{m:02d}.N{c:02d}'


def gf7_descriptor(gf7:str)->dict:
    b,m,c=gf7_parts(gf7)
    lo,hi=GF7_BANDS[b-1]
    mode=GF7_MODES[m-1]
    mat,aspect=GF7_MATERIALS[c-1]
    return {'namespace':'GF7_SYNTHETIC_PLATE_MODEL', 'coordinate':gf7,
            'band_hz':[lo,hi], 'reference_center_hz':(lo*hi)**0.5,
            'mode_indices':list(mode), 'material':mat, 'aspect_b_over_a':aspect,
            'prediction_status':'ANALYTIC_MODEL_SIMULATION_NOT_CALIBRATED',
            'physical_measurement':False,'atlas_semantic_equivalence':False,
            'historical_runtime_verified':False,'authority_effect':'NONE'}


def encode_axg1(hsn:str,source_digest:str)->str:
    hsn_parts(hsn)
    if not re.fullmatch(r'[0-9a-f]{64}',source_digest or ''):raise ValueError('SOURCE_DIGEST_REQUIRED')
    prefix=source_digest[:12]
    checksum=hashlib.sha256(('AXG1|'+source_digest+'|'+hsn).encode()).hexdigest()[:12]
    return f'AXG1:{prefix}:{hsn}:{checksum}'


def decode_axg1(token:str,source_digest:str)->str:
    m=AXG_RE.fullmatch(token) if isinstance(token,str) else None
    if not m or not isinstance(source_digest,str) or m.group(1)!=source_digest[:12]:raise ValueError('AXG1_TOKEN_INVALID')
    hsn=m.group(2)
    if encode_axg1(hsn,source_digest)!=token:raise ValueError('AXG1_CHECKSUM_MISMATCH')
    return hsn


def typed_route(hsn:str,source_digest:str)->dict:
    gf=positional_gf7(hsn)
    return {'hsn':hsn,'hsn_source_digest':source_digest,'authored_axg1':encode_axg1(hsn,source_digest),
            'gf7_positional_analogy':gf,'gf7_model':gf7_descriptor(gf),
            'glyphforge_historic_name_candidates':list(GLYPHFORGE_HISTORIC_NAMES),
            'kg8_alias':'RESOLVE_FROM_CURRENT_AUTHORIZED_KG8_SOURCE',
            'relationship_type':'POSITIONAL_DISPLAY_ANALOGY_NOT_SEMANTIC_SAME_AS',
            'resident_identity':'UNVERIFIED','physical_cymatics':'NOT_MEASURED',
            'host_effect':'NONE','canon_effect':'NONE'}
