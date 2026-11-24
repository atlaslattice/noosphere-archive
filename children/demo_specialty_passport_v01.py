"""Synthetic-only demonstration: no real resident, agent call or permission."""
import json
from pathlib import Path
from children.specialty_passport_v01 import validate_passport, synthesis_routing

if __name__ == '__main__':
    demo = json.loads((Path(__file__).parents[1] / 'examples' / 'children_specialty_passports_v01.synthetic.json').read_text())
    for p in demo:
        validate_passport(p)
    out = synthesis_routing(demo, ['H02.S05.N02', 'H03.S04.N01', 'H11.S01.N07'], 'review', '2026-11-22T00:00:00Z')
    print(json.dumps({'status': out['status'], 'house_routes': out['house_routes'],
                      'missing': out['missing'], 'residents_verified': out['resident_identities_verified'],
                      'candidates_by_node': {r['coordinate']: len(r['candidates']) for r in out['candidate_details']}}, indent=2))
