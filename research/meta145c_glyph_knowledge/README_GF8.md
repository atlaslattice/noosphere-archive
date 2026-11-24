# Atlas GF8 — Physically grounded cymatic glyphs + external reasoning filter

**Release state:** source-only research addendum to META145C; not a live ChatGPT plugin, not calibrated, not host-tested, not source or CANON truth promotion.

This folder contains the unchanged META145C public source as a standalone test dependency, plus **new** GF8 modules and tests. The additive GitHub draft PR should include only GF8 additions, retaining the original GF7 code and v36 META145C lineage.

## New implementation

- `src/gf8.py`: numerical thin-plate resonance frequencies, physically parameterized eigenmode nodal glyphs, frequency-driven complex modal response, declared model validity, complete 1,728 GF7 inverse-design checks, and user-reported measurement comparison.
- `src/calibration.py`: nodal mask IoU / symmetric Chamfer comparison for *registered and externally source-preserved* experimental data; returns an unverified candidate receipt, never physical calibration by fiat.
- `src/reasoning_filter.py`: deterministic source-pin/rights-scope-safe context preparation and postflight numeric status verification. Model weights are never touched.
- `src/build_gf8_viewer.py`: fully offline interactive HTML with the 12 GF7 frequency ranges, 12 mode choices, 12 material/aspect contexts, model HOLD flags, and fixed-plate driven resonance patterns.
- `tests/test_gf8.py`, `tests/test_calibration.py`, `tests/browser_smoke.py`: public synthetic physics, security, memory, and Chromium smoke tests.
- `docs/FREQUENCY_MODEL.md`, `docs/WRAPPER_CONTRACT.md`: calculations and safe integration contract.

## Reproduce (Python stdlib, except Chromium test)

```sh
python -m unittest discover -s tests -p 'test*.py'
python -O -m unittest discover -s tests -p 'test*.py'
python -m unittest discover -s tests_public -p 'test*.py'
python -m src.build_gf8_viewer
python tests/browser_smoke.py  # requires Python playwright and Chromium
python -m examples.frequency_sweep
python -m examples.wrapper_demo
```

`outputs/GF8_FREQUENCY_EXPLORER.html` is self-contained and makes no network request. Individual outputs are data, not real material measurements. For physics context and the 12-band screening table see [FREQUENCY_MODEL.md](docs/FREQUENCY_MODEL.md).

## Nonclaims and release gates

- No direct OpenAI or GPT-6 model-weight update or undisclosed training.
- No physical experiment, free/fully-clamped-edge plate solver, sand granular dynamics, acoustic pressure recording or frequency-agnostic universal glyph.
- No independently authenticated Atlas resident, permission grant, data harvesting, host latency result or CANON revision.
- No contradiction between fixed frequency band names and unique natural frequency: GF7 labels a range, GF8 derives a mode of a declared plate.
- Not installed as a live ChatGPT plugin. Reviewed publisher integration/host authorization would be required to run it in SwarmChat or Atlas ONE.
