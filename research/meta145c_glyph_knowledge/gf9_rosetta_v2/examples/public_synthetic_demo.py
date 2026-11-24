"""Source-free original GF9 mathematical Rosetta exercise."""
import json
from src.compiler import twelve_chapter_synthetic_exchange
from src.protocol import Policy,evaluate
x=twelve_chapter_synthetic_exchange(0)
y=evaluate(Policy(3,6),0,9,(120,121,122),0.01)
print(json.dumps({'status':'SOURCE_FREE_SYNTHETIC_GF9_DEMO','chapter_count':x['count'],
  'example_chapter':x['chapters'][9]['chapter_name'],
  'math_prediction_bridge':x['chapters'][9]['bridge']['mathematics_reproduced'],
  'real_language_translation':False,'physical_measurement':False,
  'sample_channel_test':y},indent=2))
