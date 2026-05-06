# Shenmu Integrated Simulation Model — Adversarial Review

**Document ID:** SHENMU-SIM-REVIEW-2026-0506  
**Date:** 2026-05-06  
**Source:** Shenmu CN-SHM-01 Integrated Simulation Model, Final Synthesis  
**Status:** Critical F8/F9 defects detected; do not treat simulation output as canonical until patched  
**Target Revision:** SHENMU-SIM-v1.1  
**Canon References:** Daily OS v1.4; F8 dimensional sanity; F9 common-sense horizon; Zero Erasure discipline

## Executive Verdict

The simulation is useful as a scaffold, but it is not yet reliable. The code contains a critical electricity-revenue multiplier bug and several scenario/prose mismatches. The model should be classified as **REJECT AS CANONICAL OUTPUT / APPROVE FOR PATCHING**.

## Critical Findings

### F-SIM-01 — Electricity Revenue Multiplied by 10×

The `electricity()` method returns:

```python
return gen_gwh * self.tariff * 10
```

The comments correctly derive that 450 GWh at ¥0.55/kWh equals ¥247.5M, which is simply:

```python
revenue_M = gen_gwh * tariff
```

But the executable line uses `* 10`, producing ¥2,475M instead of ¥247.5M.

**Impact:** All payback, NPV, IRR, and scenario outputs are invalid. The stated stress payback of ~20.9 years cannot be produced by the current code.

**Patch:** Replace with:

```python
return gen_gwh * self.tariff
```

### F-SIM-02 — Unreachable Correct Return Block

The function includes the correct formula after the first return, but it is unreachable. This indicates the model was patched in comments but not in executable code.

**Patch:** Delete the long inline correction comment and leave one clear unit-tested formula.

### F-SIM-03 — Scenario Claims Do Not Match Code

The document claims:

- stress case simple payback ~20.9 years,
- NDRC levered payback ~13.8 years,
- 6.7-year target requires manufacturing or carbon >¥200/t.

Because of the 10× electricity bug, the script will output much shorter paybacks. The prose and code disagree.

**Patch:** Add expected-output tests that fail if stress payback is outside a documented tolerance range.

### F-SIM-04 — Manufacturing Revenue Is Gross but Treated as Cash Flow

`manufacturing()` returns ¥1,400M gross revenue. The comment says net margin is separate, but the model adds the full gross value to revenue and subtracts only generic project OPEX.

**Impact:** Manufacturing-supported scenarios are materially overstated.

**Patch:** Model manufacturing as either:

```python
manufacturing_gross * manufacturing_margin
```

or add a dedicated manufacturing OPEX line.

### F-SIM-05 — Direct Jobs Mismatch

The layer table sums to approximately 653 direct jobs, but the model/header claims 700–1,200 jobs. This creates a credibility gap.

**Patch:** Add `jobs_low`, `jobs_mid`, `jobs_high` or align the layer table to the stated jobs range.

### F-SIM-06 — NDRC Savings Treated as Annual Cash Flow

`levered_payback()` adds a fixed ¥180M annual concessionary savings to net cash flow. Financing savings are not the same as operating cash flow, and should be separated into levered/NPV analysis.

**Patch:** Report three metrics separately:

- simple operating payback,
- levered debt-service payback,
- NPV-adjusted payback.

### F-SIM-07 — Tax Rate Defined but Unused

`TAX_RATE = 0.25` is defined but never applied. NPV and IRR are therefore pre-tax while the model implies project-finance rigor.

**Patch:** Either apply tax or label outputs as pre-tax.

### F-SIM-08 — Monte Carlo Uses Simple Payback While Labeling Concessionary Scenario

Monte Carlo creates `use_concessionary=True`, but appends `proj.compute_payback()`, not `levered_payback()`. Therefore the Monte Carlo ignores NDRC financing despite labeling the scenario as concessionary.

**Patch:** Choose one:

- Monte Carlo simple operating payback, no concessionary label; or
- Monte Carlo levered payback using financing assumptions.

### F-SIM-09 — “Final” and “Ready for Execution” Are Premature

The closing prose says the model is ready for execution. Given the critical revenue bug and scenario mismatch, this must be downgraded.

**Patch:** Replace with:

> Status: DRAFT SIMULATION — F8/F9 PATCH REQUIRED BEFORE CANONICAL USE.

## Required v1.1 Corrections

1. Fix electricity revenue formula.
2. Add regression tests for expected stress/current/full-stack paybacks.
3. Remove unreachable code/comment block.
4. Separate manufacturing gross revenue from net contribution.
5. Separate simple, levered, and NPV-adjusted payback.
6. Apply or explicitly exclude tax.
7. Fix Monte Carlo to match the metric it claims to test.
8. Align direct jobs with stated 700–1,200 range or relabel output as 653 modeled jobs.
9. Replace “Final” / “ready for execution” with “Draft — patch required.”

## Corrected Core Formula

```python
def electricity(self, gen_gwh: float = 450) -> float:
    """Electricity revenue in ¥M/year.
    1 GWh = 1,000,000 kWh.
    Revenue ¥M = gen_gwh * 1,000,000 * tariff / 1,000,000.
    """
    return gen_gwh * self.tariff
```

## Final Ruling

**Status:** REJECT AS CANONICAL OUTPUT / APPROVE FOR PATCHING  
**Severity:** Critical F8/F9  
**Reason:** Executable model contradicts claimed outputs due to 10× electricity revenue error.  
**Next Action:** Generate SHENMU-SIM-v1.1 with unit tests before any scenario table is cited externally.
