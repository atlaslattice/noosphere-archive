# Optional Atlas Civilization R01 source reference

The canonical source lives at `atlaslattice/Atlas-Intelligence/programs/civilization-r01`, release `ATLAS-CIVILIZATION-R01-20261123-1`. This repository adds a small metadata validator and an optional `prepare_civilization_kernel_work` function in `core.swarmhub_contracts`. It routes candidates through the existing Sentinel and Orchestrator. Existing EX1728 source references remain separate.

Supply exact reference bytes plus their selected SHA-256, an explicit `house_id` from H01 to H12, a current `room_id`, and `mode="WORK"`. The reference must name the canonical immutable commit and file fingerprints, including the frozen benchmark artifacts. No kernel implementation is copied here.

```python
from core.swarmhub_contracts import prepare_civilization_kernel_work

# selected_bytes and selected_sha256 come from the host's reviewed source pins.
candidate = prepare_civilization_kernel_work(
    selected_bytes, selected_sha256, house_id="H02", room_id="work-review"
)
assert candidate["status"] == "PREPARED_NOT_EXECUTED"
assert candidate["packet"]["dispatch_candidate"] == "REFERENCE_QUERY"
```

The recorded local synthetic experiment retained eleven supporting-kernel gain candidates and one H02 regression. H02 uses the reference/scan fallback by default. These are twelve supporting software comparisons, with zero original 1,728 primary metric credit, zero specialized-node completion and zero production or whole-system gain claims.

The helper verifies selected reference bytes only. It performs no source retrieval, kernel execution, model calls, room posts, persistence, authorization or Canon promotion. A digest does not authenticate an owner. The packet explicitly leaves source retrieval, host READ permission and the current RETURN fence unverified. Those checks remain with the canonical host before actual use. A kernel ID is not converted to an original HSN or EX1728 task by ordinal position.

Run `python3 -m unittest discover -s tests -p test_civilization_kernel_reference.py -v` for the source-reference controls. Synthetic test commits are test inputs, not publication evidence.
