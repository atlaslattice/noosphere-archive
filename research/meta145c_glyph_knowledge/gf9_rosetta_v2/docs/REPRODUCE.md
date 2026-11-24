# GF9-R2 reproduction, checkpoints and limits

Use Python 3.11+; core has no external dependencies. The optional Chromium viewer test requires local Playwright and Chromium and uses **no network**.

## Original source custody

The **private** archive includes `private_inputs/ariadne_v07_atlas.json` from the user's owner-private Atlas R09 package and exact SHA256 `07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6`. Never publish its original record definitions or the derived private `MODULES_144_X_CHAPTERS_12_PRIVATE.json` without separate rights review. Public code/tests work without the registry, in synthetic fixtures.

## Verification

```
PYTHONPATH=. python -m unittest discover -s tests
PYTHONPATH=. python -O -m unittest discover -s tests
PYTHONPATH=. python -m src.cli --help
```

## Evolution (already executed and archived)

```
PYTHONPATH=. python run.py phase1
PYTHONPATH=. python run.py phase2
```

Each stage is **finite**. Stage 2 must begin from a verified 5k state. After any crash, reconstruct only a contiguous, hash-valid append-only tail against a trusted checkpoint before resuming; do not overwrite events or increment counts on assumption. The delivered `recover_phase2.py` is an actual crash-recovery test case with 9,790 valid phase-two rows and an additional 210 rows.

```
PYTHONPATH=. python blind_chunk.py 0
PYTHONPATH=. python blind_chunk.py 1
PYTHONPATH=. python blind_chunk.py 2
PYTHONPATH=. python blind_chunk.py 3
```

`outputs/INDEPENDENT_BLIND_BENCHMARK.json` combines all four source-identified, disjoint sets. Policy selection in `outputs/POLICY_PROMOTION_REVIEW_144.json` used **GF9-R2-VALIDATION**; independent benchmark uses **GF9-R2-INDEPENDENT-BLIND**; trial mutation uses **GF9R2-TRAIN**. These namespaces are explicitly distinct.

## No trust laundering

An unsigned hash or self-declared resident is not an authenticated person. A successful CRC is not cryptographic verification of a sender. Historical script source labels do not imply a translation. A source-reported simulated score cannot promote a scientific claim to measured/validated. The private archive's hash root must be separately trusted to detect deletion or replacement of the full ledger.
