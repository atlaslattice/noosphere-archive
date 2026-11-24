# Atlas META145C · Public-safe source package

The code is derived from one real, source-verified offline owner-private 144-Sphere circuit. This *public package* deliberately contains **NO original Ariadne registry, historical OpenAlex crosswalk, R10 private evidence DB, original fiction sources, private Brain/Palace state, or owner sessions**. Its synthetic tests run with the Python standard library:

```
PYTHONPATH=. python -m unittest discover -s tests_public
PYTHONPATH=. python -O -m unittest discover -s tests_public
```

To run the full 144×1,728 build locally, the authorized operator supplies the exact original Ariadne v0.7 `atlas.json` and 4,516-row historical OpenAlex crosswalk using the verified hashes already compiled into `src/glyph.py` and `src/core.py`:

```
PYTHONPATH=. python -m src.cli --ariadne /private/atlas.json --openalex /private/openalex_to_ariadne_ALL_4516.csv --output /private/results
```

No hosted account rights, resident sessions, background jobs, external API, CANON mutations or physical cymatic experiments occur. See `docs/INTEGRATION_PROTOCOL.md` and `docs/TEST_METHOD.md` for negative controls and precise scope. For actual measured results and source-hash receipts, consult the separate owner-private package. Nothing in this code automatically makes encyclopedia, literature or fiction content verified knowledge.

## Memory integration

`topic_view(..., memory=memory, memory_checkpoint=checkpoint)` now requires a caller-retained checkpoint whenever memory is used. The checkpoint has `expected_tip` and `expected_count`; it must come from independent custody, never a fresh self-read of the same mutable database. One verified snapshot supplies every topic score. Calls without memory retain their original behavior.

Writes reserve a SQLite transaction before inspecting the prior chain and roll back on failure. Optional checkpoint-bound writes reject a valid-prefix rollback. Existing stored payload hashes and the database schema are preserved. See `docs/MEMORY_INTEGRITY_INTEGRATION.md` for migration, limitations, source ancestry and the reproducible regression command.
