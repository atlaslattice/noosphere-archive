"""Synthetic example, never reads user memories or wakes a model."""
import json
from pathlib import Path
from .portable import verify_bundle,prepare_rehydration,fork_bundle
ROOT=Path(__file__).resolve().parents[1]
b=json.loads((ROOT/'examples/example-memory-bundle.redacted.json').read_text())
c=json.loads((ROOT/'examples/example-rehydration-contract.json').read_text())
print(json.dumps({'verified':verify_bundle(b),'preparation':prepare_rehydration(b,c),
                  'fork':verify_bundle(fork_bundle(b,'demo.synthetic.child-002','2026-11-22T20:00:00Z'))},sort_keys=True,indent=2))
