"""Print all 12 physical GF7-to-GF8 inverse-design screenings. No source writes."""
import json
from src.gf8 import Plate,mode_hz,reference_for_gf7,driven_glyph

band_examples=[f'GF7.B{n:02d}.M01.C05' for n in range(1,13)]
records=[reference_for_gf7(g) for g in band_examples]
print(json.dumps({'model':'GF8_SCREENING_NOT_EXPERIMENT','example_plate':Plate().metadata(),
    'example_plate_mode_11_hz':mode_hz(Plate(),1,1),'bands':records},indent=2))
