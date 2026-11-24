"""Original, physically parameterized GF9-R2 3D glyphs and two-notation exchange.
A GF9 glyph is a calculated finite modal field + typed parameters. Historical
writing systems can annotate it, but are NOT equivalent to its operators.
"""
from __future__ import annotations
import math,hashlib,json
from .protocol import physical_problem,make_message,Policy,valid_message,CHAPTER_LABELS
from .linguistics import PROFILES,script_record,original_style_grammar

def digest(obj):
 return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest()

def physical_3d_glyph(module:int,chapter:int,grid:int=13,vertical_gain:float=0.17)->dict:
    if type(grid)!=int or not 9<=grid<=49 or grid%2!=1 or not 0<=vertical_gain<=1:raise ValueError('GLYPH_GRID_BOUNDS')
    ref=physical_problem(module,chapter);m,n=ref['mode']
    coords=[];nodes=[]
    for y in range(grid):
       line=[];mask=[]
       for x in range(grid):
          xn=x/(grid-1);yn=y/(grid-1)
          displacement=math.sin(m*math.pi*xn)*math.sin(n*math.pi*yn)
          line.append([round(xn,5),round(yn,5),round(vertical_gain*displacement,6)])
          mask.append(1 if abs(displacement)<0.025 else 0)
       coords.append(line);nodes.append(mask)
    body={'schema':'atlas.gf9.3d-nodal-glyph/v1','source_coordinate':f'H{module//12+1:02d}.S{module%12+1:02d}',
      'chapter':chapter+1,'geometry_model':'SSSS_RECTANGULAR_SEPARABLE_EIGENMODE',
      'mode':[m,n],'grid':grid,'vertical_gain':'ILLUSTRATIVE_NORMALIZED_FIELD',
      'xyz':coords,'node_mask':nodes,
      'material':'NOMINAL_REFERENCE_STEEL_ALLOY',
      'physical_frequency_hz':round(ref['old_frequency_hz'],8),
      'transformed_frequency_hz':round(ref['new_frequency_hz'],8),
      'predicted_frequency_ratio':round(ref['frequency_ratio'],10),
      'scientific_evidence':'ANALYTIC_UNCALIBRATED_NOT_MATERIAL_CYMATICS',
      'source_gf8':'ATLAS_GF8_KIRCHHOFF_LOVE_SSSS_SOURCE_MODEL',
      'script_rights':'ORIGINAL_PARAMETRIC_GLYPH_NOT_TOLKIEN_GLYPH',
      'semantic_claim':'NONE'}
    return {'payload':body,'sha256':digest(body)}

def validate_glyph(glyph:dict):
    if type(glyph)!=dict or set(glyph)!={'payload','sha256'} or digest(glyph['payload'])!=glyph['sha256']:raise ValueError('GLYPH_SHA_FAILED')
    p=glyph['payload'];mod=int(p['source_coordinate'][1:3])*12-12+int(p['source_coordinate'][5:7])-1;ch=p['chapter']-1
    expected=physical_3d_glyph(mod,ch,p['grid'])
    if expected['sha256']!=glyph['sha256']:raise ValueError('GLYPH_PHYSICAL_MATH_MISMATCH')
    return True

def serialized_earth(glyph:dict)->str:
    validate_glyph(glyph)
    p=glyph['payload'];return f"GF9-EARTH/v1:{p['source_coordinate']}:{p['chapter']:02d}:{p['mode'][0]}x{p['mode'][1]}:{glyph['sha256']}"

def serialized_imperial_fiction(glyph:dict)->str:
    validate_glyph(glyph)
    p=glyph['payload'];return f"RSL-FICTION-IMPERIAL/v1|{glyph['sha256']}|{p['mode'][1]}:{p['mode'][0]}|{p['source_coordinate']}|{p['chapter']:02d}"

def bridge_equivalence(glyph:dict,earth:str,fiction:str)->dict:
    validate_glyph(glyph)
    if earth!=serialized_earth(glyph) or fiction!=serialized_imperial_fiction(glyph):raise ValueError('SYMBOLIC_SERIALIZATION_MISMATCH')
    return {'schema':'atlas.gf9.two-notation-bridge/v1','status':'EXACT_SHARED_MODEL_PACKET_PARITY_ONLY',
      'earth_wire':earth,'fictional_imperial_wire':fiction,'glyph_sha256':glyph['sha256'],
      'script_lexicon_learned':False,'intention_understood':False,'actual_alien_response':False,
      'mathematics_reproduced':True,'rights':'ORIGINAL_FICTIONAL_NOTATION'}

def sonify_metadata(module:int,chapter:int,reference_hz:float=440.0)->dict:
    """Sonification is explicit metadata only; no sound-wave generation."""
    if not isinstance(reference_hz,(float,int)) or not 20<=reference_hz<=20000:raise ValueError('REFERENCE_SOUND_INVALID')
    p=physical_problem(module,chapter)
    native=p['old_frequency_hz'];scale=1.0
    # Piecewise octaves are a presentation choice and NOT atomic sound.
    while native*scale<110:scale*=2.0
    while native*scale>880:scale/=2.0
    return {'input_hz':round(native,10),'audible_reference_hz':reference_hz,
      'sonification_scale':scale,'rendered_hz':round(native*scale,10),
      'conversion':'EXPLICIT_OCTAVE_SHIFT_FOR_AUDIBILITY',
      'not_material_measurement':True,'no_audio_generated':True}

def twelve_chapter_synthetic_exchange(module:int)->dict:
    steps=[]
    for ch in range(12):
      p=Policy(3,6);message=make_message(module,ch,p)
      if not valid_message(message,module,ch):raise ValueError('LESSON_PREDICTION_INVALID')
      glyph=physical_3d_glyph(module,ch,9)
      step={'chapter':ch+1,'chapter_name':CHAPTER_LABELS[ch],
        'intent':'MATHEMATICAL_EXERCISE_ONLY',
        'candidate_wire_message':message,
        'identity_status':'SIMULATED_NOT_AUTHENTICATED',
        'bridge':bridge_equivalence(glyph,serialized_earth(glyph),serialized_imperial_fiction(glyph)),
        'sonification':sonify_metadata(module,ch),
        'historical_script':script_record(PROFILES[(module+ch)%len(PROFILES)].code),
        'status':'HOLD_SEMANTICS_PENDING_REAL_EXPRESSIVE_TEST'}
      steps.append(step)
    return {'schema':'atlas.gf9.12-chapter-synthetic-exchange/v1','module':f'H{module//12+1:02d}.S{module%12+1:02d}',
      'chapters':steps,'count':len(steps),'actual_AI_to_AI_contact':False,
      'source':'ORIGINAL_GF9_R2_FICTIONAL_TWO_NOTATION_CALCULATOR'}
