"""Source-attributed writing-system interoperability profiles; NO translations.
The canonical scientific wire format is independent of historical scripts.
Examples preserve separate sign / transliteration / reading / language layers.
"""
from __future__ import annotations
import hashlib, json, re, unicodedata
from dataclasses import dataclass, asdict

SOURCES = {
 'iso': 'https://www.unicode.org/iso15924/',
 'uax15': 'https://www.unicode.org/reports/tr15/',
 'uax29': 'https://www.unicode.org/reports/tr29/',
 'unicode18': 'https://www.unicode.org/versions/Unicode18.0.0/core-spec/chapter-11/',
 'oracc': 'https://oracc.museum.upenn.edu/doc/help/editinginatf/primer/',
 'unike': 'https://www.unicode.org/reports/tr57/',
 'maya': 'https://www.unicode.org/events/utw/2026/talks/developing-an-encoding-for-maya-hieroglyphs/',
 'tolkien_rights': 'https://www.tolkienestate.com/frequently-asked-questions-and-links/',
}

@dataclass(frozen=True)
class ScriptProfile:
    code: str
    label: str
    structure: str
    status: str
    source: str
    notation: str
    language_scope: str

# Representative research set, not an assertion of all writing systems or translational coverage.
PROFILES = [
 ScriptProfile('Xsux','Sumero-Akkadian cuneiform','LOGOSYLLABIC','HISTORIC_RESEARCH_ONLY',SOURCES['oracc'],'ATF_SIGN_TRANSLITERATION_SEPARATE','sux, akk (separate readings)'),
 ScriptProfile('Egyp','Egyptian hieroglyphs','MIXED_LOGOGRAPHIC_PHONETIC','HISTORIC_RESEARCH_ONLY',SOURCES['unike'],'UNICODE_CODEPOINT_AND_GARDINER_REF_SEPARATE','egy'),
 ScriptProfile('Linb','Linear B','SYLLABARY_WITH_LOGOGRAMS','HISTORIC_RESEARCH_ONLY',SOURCES['unicode18'],'SYLLABIC_SIGNS_NOT_TRANSLATIONS','gmy'),
 ScriptProfile('Maya','Maya hieroglyphic writing','LOGOSYLLABIC','ENCODING_IN_PROGRESS_NO_AUTO_RENDER',SOURCES['maya'],'EXTERNAL_SIGN_CATALOG_REQUIRED','various Mayan languages'),
 ScriptProfile('Hani','Han characters','MORPHOSYLLABIC','REFERENCE_ONLY',SOURCES['iso'],'GLYPH_VARIANTS_AND_READINGS_SEPARATE','zho/jpn/kor etc'),
 ScriptProfile('Hang','Hangul','ALPHABETIC_FEATURAL','REFERENCE_ONLY',SOURCES['iso'],'JAMO_SYLLABLE_NORMALIZATION_EXPLICIT','kor'),
 ScriptProfile('Arab','Arabic','ABJAD','REFERENCE_ONLY',SOURCES['iso'],'JOINING_DIRECTION_DIACRITICS_PRESERVED','ara and other languages'),
 ScriptProfile('Deva','Devanagari','ABUGIDA','REFERENCE_ONLY',SOURCES['iso'],'GRAPHEME_CLUSTER_SEGMENTATION','hin/san and other languages'),
 ScriptProfile('Brai','Braille','TACTILE_CELL_NOTATION','REFERENCE_ONLY',SOURCES['iso'],'CELL_PATTERN_IS_NOT_UNIVERSAL_LEXEME','multiple'),
 ScriptProfile('Grek','Greek','ALPHABET','REFERENCE_ONLY',SOURCES['iso'],'ALPHABETIC_ENCODING','ell'),
 ScriptProfile('Latn','Latin script','ALPHABET','REFERENCE_ONLY',SOURCES['iso'],'LATIN_SCRIPT_NOT_ENGLISH_SEMANTICS','multiple'),
 ScriptProfile('Ethi','Ethiopic','ABUGIDA','REFERENCE_ONLY',SOURCES['iso'],'SYLLABIC_SIGN_ENCODING','amh and other languages'),
 ScriptProfile('Tibt','Tibetan','ABUGIDA','REFERENCE_ONLY',SOURCES['iso'],'SYLLABLE_MARKS_PRESERVED','bod'),
 ScriptProfile('Ogam','Ogham','ALPHABET','HISTORIC_RESEARCH_ONLY',SOURCES['iso'],'STROKE_LOCATION_NOT_TRANSLATION','sga'),
 ScriptProfile('Runr','Runic','ALPHABET','HISTORIC_RESEARCH_ONLY',SOURCES['iso'],'CHRONOLOGICAL_VARIANTS_PRESERVED','gmc'),
 ScriptProfile('Cher','Cherokee','SYLLABARY','REFERENCE_ONLY',SOURCES['iso'],'COMMUNITY_RIGHTS_REVIEW','chr'),
 ScriptProfile('Cans','Unified Canadian Aboriginal Syllabics','SYLLABICS','COMMUNITY_REVIEW_REQUIRED',SOURCES['iso'],'COMMUNITY_ORTHOGRAPHIC_PRACTICES','multiple'),
 ScriptProfile('Zyyy','Mathematical notation / symbols','FORMAL_NOTATION','PROJECT_NEW_AUTHORING',SOURCES['iso'],'NO_HISTORICAL_LANGUAGE_CLAIM','language-neutral model only'),
]
BY_CODE = {p.code:p for p in PROFILES}
assert len(BY_CODE)==len(PROFILES)

SAFE = re.compile(r'^[A-Za-z0-9_.:-]{1,96}$')
def normalize_grapheme_label(label: str, *, strict: bool=True)->str:
    if not isinstance(label,str) or not 1<=len(label)<=240:raise ValueError('INVALID_LABEL_LENGTH')
    if any(0xD800<=ord(c)<=0xDFFF or ord(c)<32 for c in label):raise ValueError('UNSAFE_UNICODE_SCALAR')
    out=unicodedata.normalize('NFC',label)
    if strict and out!=label:raise ValueError('NON_NFC_REJECTED_KEEP_ORIGINAL_SOURCE_BYTES')
    return out

def script_record(code:str, source_sign:str|None=None, transliteration:str|None=None, reading:str|None=None, asserted_translation:str|None=None)->dict:
    if code not in BY_CODE:raise ValueError('UNREGISTERED_SCRIPT')
    p=BY_CODE[code]
    if asserted_translation is not None:raise ValueError('AUTOMATIC_TRANSLATION_FORBIDDEN')
    for s in (source_sign,transliteration,reading):
        if s is not None:normalize_grapheme_label(s,strict=False)
    if code=='Maya' and source_sign is not None:raise ValueError('MAYA_SIGN_RENDER_HOLD_CATALOG_REQUIRED')
    return {'script_code':p.code,'script_label':p.label,'writing_system':p.structure,
      'sign':source_sign,'transliteration':transliteration,'reading':reading,
      'translation':None,'status':'SOURCE_REFERENCE_NOT_A_SEMANTIC_TRANSLATION',
      'source':p.source,'rights_review':'REQUIRED_BEFORE_REPRODUCING_SOURCE_TEXT',
      'not_a_gf9_operator':True}

def registry_digest()->str:
    return hashlib.sha256(json.dumps([asdict(p) for p in PROFILES],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def original_style_grammar()->dict:
    return {'name':'GF9-R2 ORIGINAL PARAMETRIC GLYPH',
      'design_inspiration':'scholarly comparative morphology; ornamental elegance only; no Tolkien characters or lexemes',
      'grounded_components':['mode_indices','material_damping','frequency_ratio','reference_frame','source_uncertainty'],
      'operator_family':['COUNT','RATIO','ROTATE','ELEMENT','LATTICE','RESONANCE','TRANSFORM','HOLD','NEGATE','ASK','VERIFY','TEACH'],
      'rights':'ORIGINAL_AUTHORING_ONLY_NO_TOLKIEN_SCRIPT_COPY',
      'phonetic_translation_claim':False,'source':SOURCES['tolkien_rights']}
