# GF8: More physically faithful cymatic glyphs

**Status:** new source-only analytic reference implementation; **not** calibrated, deployed, hosted, physically measured, or a revision of original GF7/HSN/KG8. Existing source remains intact.

## Why band-indexed GF7 was not a physical Chladni glyph

GF7 v0.7 has **12 logarithmic-ish frequency bands**, **12 (m,n) mode presets**, and **12 material/aspect presets**. That yields 1,728 synthetic addresses. The current META145C `positional_gf7(Hxx.Sxx.Nxx)` changes addresses, **not physical acoustics**. It is a useful reversible navigation analogy, not the statement that a given Ariadne node naturally vibrates at that frequency. GF8 retains GF7 as an unchanged index, but derives a *new*, separate predicted vibrational field from material properties, dimensions, boundary conditions, damping, forcing and frequency.

## Current GF8 solver: declared physics

For a flat isotropic Kirchhoff–Love rectangular thin plate **simply supported on all four edges**:

- Rigidity: `D = E * h³ / (12 * (1 - ν²))`
- Natural frequency: `f_mn = π/2 * sqrt(D / (ρ h)) * (m²/a² + n²/b²)`
- Spatial eigenfunction: `phi_mn(x,y) = sin(mπx/a) * sin(nπy/b)`
- Harmonic forcing: `Q_mn = F * phi_mn(xdrive,ydrive) / (M_mn * ((2π f_mn)² - (2π fdrive)² + 2 i ζ (2π f_mn)(2π fdrive)))`, with `M_mn = ρ h a b / 4` for this normalization.
- Total displacement is the complex modal sum. A normalized low-displacement mask is only a *nodal proxy*. It does **not** calculate sand/granule transport or microscope-acoustic visualization.

The API refuses unsupported `FREE_ALL_EDGES`, `CLAMPED`, circular drums, nonlinear acoustics, ultrasonic fluid coupling, nonhomogeneous plates, and arbitrary 3D energy-wave/perspective claims. Those require separate measured or FEM models, not silent approximation.

## Re-evaluate GF7 band centers with a specified plate

The following is **an inverse-design illustration**: choose `M01=(1,1)`, `C05=steel square`, thickness `2 mm`, adjust square plate edge length until mode `(1,1)` falls at the band geometric-center frequency. E/ρ/ν are nominal assumptions (steel E=200 GPa, ρ=7850 kg/m³, ν=0.30), not data from an actual plate. Screen nominal validity by declaring a **3 cm to 2 m laboratory geometry window**, thickness/edge <=3%, and thickness/bending-wavelength <=3%. These are conservative screening heuristics, not a universal law or proof of real resonance.

| GF7 | Band Hz | Center Hz | Inverse plate edge (cm) | Screening status |
|---|---:|---:|---:|---|
| B01 | 0.1–1 | 0.316 | 550.90 | HOLD—beyond lab geometry |
| B02 | 1–5 | 2.236 | 207.17 | HOLD—beyond lab geometry |
| B03 | 5–20 | 10 | 97.97 | Within declared analytic screen |
| B04 | 20–80 | 40 | 48.98 | Within screen |
| B05 | 80–200 | 126.49 | 27.55 | Within screen |
| B06 | 200–500 | 316.23 | 17.42 | Within screen |
| B07 | 500–1,000 | 707.11 | 11.65 | Within screen |
| B08 | 1,000–2,000 | 1,414.21 | 8.24 | Within screen |
| B09 | 2,000–5,000 | 3,162.28 | 5.51 | HOLD—thickness/edge |
| B10 | 5,000–20,000 | 10,000 | 3.10 | HOLD—thin-plate wavelength |
| B11 | 20,000–100,000 | 44,721.36 | 1.47 | HOLD—thickness and lab geometry |
| B12 | 100,000–1,000,000 | 316,227.77 | 0.55 | HOLD—thin-plate model and lab geometry |

**Interpretation:** all 12 frequency bands remain addressable; *not all* are physically plausible for the fixed steel/2 mm/boundary conditions. For high ultrasound, use appropriately thin microstructures and a different model/measurement technique. For infrasound, a much larger or softer structure may be needed. No band has a universal resonance glyph.

## Real laboratory calibration procedure — not executed here

1. Record plate material composition, dimensions (caliper), thickness map, mounting/support, humidity/temperature, drive amplitude/location and instrument serial/calibration.
2. Perform low-power frequency sweeps, capture real drive frequency/phase/amplitude and support constraints. Do not assume the center of a band is a resonance.
3. Collect frequency-specific vibration fields (laser Doppler vibrometer ideally) and/or calibrated Chladni powder images. Preserve original files, EXIF/timestamps, release permissions, file SHA-256 and licensing.
4. Register field and theoretical geometry with known fiducials; estimate nodal contours including threshold uncertainty.
5. Compare measured vs predicted frequencies, and nodal masks via intersection-over-union and symmetric Chamfer distance. Report confidence limits and experiment controls, not only attractive pictures.
6. Adjust mechanical parameters only through a transparent fit with held-out modes, then preserve both original and proposed calibrated values. Keep out-of-sample residuals and evidence for changed geometry/boundary conditions.
7. Carry results into Atlas as **observational evidence, numerical prediction, mismatch, or expert-reviewed claim**, never by automatic CANON or semantic equivalence. A measurement changes knowledge *about the plate*, not the model weights of GPT.

The included `calibration.py` computes numerical comparison metrics over already-registered masks and refuses to certify instrument provenance. It cannot perform camera registration or read real images. All demo observations are synthetic.

## Independent analytic numerical cross-check

For a 300 × 200 mm simply supported aluminum rectangle, 0.5 mm thick, this
implementation predicts **44.16152 Hz** for (1,1). An independent Navier
reference reports approximately **44.162 Hz** for the same nominal setup.
Agreement at this precision validates the *equation and arithmetic*, not the
actual plate mounting or instrument calibration.

## Open-source methodological references

- [Reference numerical frequency table / FEM comparison](https://planex2d.org/plate-frequencies/) (300×200 mm simply supported aluminum, 0.5 mm, 44.162 Hz).
- [Robin et al., simplified support and measured frequencies in flat plates](https://pmc.ncbi.nlm.nih.gov/articles/PMC6812332/) (Kirchhoff–Love equation and physical support considerations).
- [SInES 2026 Chladni plates](https://sinestools.univie.ac.at/chladniplates.htm) (free/clamped/suspended geometries, drive location and complex resonance spectrum).
- [Open interactive simply supported rectangular plate model](https://sandboxphysics.com/labs/chladni-plate/) (forced modal response, damping and power balance).
- [Houdini Chladni patterns](https://www.sidefx.com/docs/houdini/nodes/cop/chladni.html) (illustrative interference graphics only; do not confuse visual effects with calibrated physics).

All externally sourced mechanisms are referenced for engineering context; this GF8 code is newly authored. Do not infer that a cited project endorses Atlas.
