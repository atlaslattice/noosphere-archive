# SHENMU-TEP-v1.0 — Adversarial Review and v1.1 Integration Patch

**Document ID:** SHENMU-TEP-001-REVIEW-v1.1-PATCH  
**Date:** 2026-05-06  
**Source Document:** SHENMU-TEP-v1.0 — Technical Execution Plan  
**Status:** Adversarial review complete; integration patch recommended  
**Target Revision:** SHENMU-TEP-v1.1  
**Canon References:** SHENMU-SPEC-001-v1.0-CANONICAL; Daily OS v1.4; D-123; D-116(c); ORC-024-A pending

## Executive Verdict

The TEP is structurally strong and operationally useful, but it under-tiers several work packages that create legal, regulatory, financial, reputational, or external-relationship exposure. Under Daily OS v1.4, these must be T3 or split into T2 internal-preparation and T3 external-action substeps.

**Overall status:** APPROVE STRUCTURE / PATCH BEFORE EXECUTION.

## Primary Findings

### F-TEP-01 — Under-tiered External Engagement

WP0.2 labels pre-application engagement with Shaanxi EPB, NEA, NDRC, and MEE as T2. Under Daily OS v1.4, formal external government engagement, policy statements, methodology disclosure, and commitments are T3.

**Patch:** Split WP0.2 into:
- WP0.2A — Internal Regulatory Pre-Feasibility Memo (T2)
- WP0.2B — External Regulator Engagement / Pre-Application Contact (T3)

### F-TEP-02 — Under-tiered Anchor Tenant Engagement

WP1.3 includes engagement with CATL, BYD, LONGi while marked T2. Any external partner communication involving methodology disclosure, formal commitments, or partner evaluation is T3.

**Patch:** Split into:
- WP1.3A — Internal Anchor Options Analysis (T2)
- WP1.3B — External Anchor Tenant Contact / EOI Solicitation (T3)

### F-TEP-03 — MoU and Worker Agreements Under-tiered

WP1.5 includes signing an MoU with Shaanxi HR while marked T2. WP2.3 includes signed worker transition agreements and a community fund charter marked T2/T3.

**Patch:** Drafting may be T2; signing, filing, external negotiation, or legal activation is T3.

### F-TEP-04 — Construction and Physical Commitments Under-tiered

WP3.3 Agrivoltaic Installation is marked T2 despite being physical deployment. WP3.5 retraining execution includes wage/placement commitments and should not be purely T2.

**Patch:** Physical installation, procurement, construction contracts, worker placement guarantees, wage bridge activation, and live retraining commitments are T3. Routine monitoring after authorization may be T2.

### F-TEP-05 — ETS Enrollment and Public Dashboard Under-tiered

WP3.6 includes ETS enrollment and public dashboard publication while marked T2. ETS submission and public dashboard launch create regulatory/public exposure.

**Patch:** ETS enrollment/submission and public dashboard launch are T3. Internal audit-trial preparation is T2.

### F-TEP-06 — Phase 0 Duration Ambiguity

The canonical Shenmu spec uses Phase 0 as a broad 18-month readiness window. The TEP defines Phase 0 as Months 1–6. This is not fatal, but it creates nomenclature drift.

**Patch:** Rename TEP Phase 0 to **Phase 0A — Validation & Site Selection**. Rename Months 7–12 as **Phase 0B — Detailed Engineering & Model Lock**. Rename Months 13–24 as **Phase 0C — Permitting / Financing / Enrollment**. Only after Month 24 should the project enter physical construction.

### F-TEP-07 — Payback Confirmation Timing

Phase 4 says end-of-Year-5 success includes “Payback within 6.7 years confirmed.” A 6.7-year payback cannot be confirmed as achieved by Year 5 unless the actual payback occurs early. What can be confirmed is trajectory.

**Patch:** Replace with: “Payback trajectory remains within ±10–15% of the modeled 6.7-year incentive-stack scenario.”

### F-TEP-08 — Morning Briefing Contradiction

The Phase 0 kickoff briefing says “No T3 gates expected” and “Items requiring Convenor approval: None (all T1/T2).” But T2 itself requires explicit Convenor approval under Daily OS v1.4, and the TEP contains likely T3-adjacent tasks.

**Patch:** Replace with: “T2 scope requires Convenor approval before execution; T3 outreach/commitments are excluded from today’s scope unless separately authorized.”

### F-TEP-09 — Public Dashboard Sensitivity

Quarterly public dashboards may conflict with PRC regulatory, data, labor, or PIPL constraints.

**Patch:** Replace “public dashboard” with “stakeholder dashboard + public summary layer where legally permitted.”

## Integrated v1.1 Patch Set

1. Rename phases to avoid conflict with canonical Phase 0:
   - Phase 0A — Validation & Site Selection (Months 1–6)
   - Phase 0B — Detailed Engineering & Economic Model Lock (Months 7–12)
   - Phase 0C — Permitting, Financing & Enrollment (Months 13–24)
   - Phase 1 — Construction & Commissioning (Months 25–48)
   - Phase 2 — Operations Ramp & Verification (Months 49–72)

2. Split external-facing work packages into internal T2 prep and T3 action substeps.

3. Treat any PRC government engagement above routine logistics as T3.

4. Treat any MoU, worker agreement, community fund charter, financing, offtake, tariff, permit filing, public dashboard launch, ETS submission, or external anchor-tenant solicitation as T3.

5. Treat internal analysis, draft templates, source packs, cost models, RFP drafts, survey design, and technical memos as T2.

6. Preserve ORC-024-A dependency: Sovereign Dividend activation and 25% Node Operations allocation remain T3 / pending ratification.

7. Change end-of-Year-5 payback metric to trajectory validation, not payback completion.

8. Replace public dashboard with tiered stakeholder dashboard + legally permitted public summary.

9. Correct kickoff Morning Briefing to acknowledge that T2 requires Convenor approval.

## Corrected Phase 0 Kickoff Briefing Language

```markdown
Morning Briefing: SHENMU-PHASE0A-001
Date: [Session Date]
Sprint: Shenmu Phase 0A — Validation & Site Selection
Status: Pre-Phase 0A. T2 internal preparation proposed. No external PRC engagement or commitments authorized in this briefing.

Proposed Tasks Today:
- [T2] Draft WP0.1 Site Survey RFP — Medium effort — internal preparation for DNI, unit, land, and grid validation — dep: none
- [T2] Draft WP0.2A Internal Regulatory Pre-Feasibility Memo Template — Medium effort — maps required PRC regulatory gates without contacting external bodies — dep: WP0.1 candidate-site list
- [T2] Draft Workforce Baseline Survey Instrument — Medium effort — prepares community/workforce intake without enrollment commitments — dep: none
- [T1] Prepare Shenmu stakeholder research list — Low effort — names and institutions only, no outreach — dep: none
- [T1] Create Phase 0A vault folder index — Low effort — internal organization only — dep: none

Items Requiring Approval:
- All T2 items above require Convenor approval before execution.
- Any external outreach to PRC government bodies, Shaanxi Coal Group, State Grid, training institutions, manufacturers, financiers, or worker representatives is T3 and excluded unless separately authorized.

T3 Sign-Off Request:
- None requested in this briefing.
```

## Final Ruling

The TEP is not rejected. It is a strong execution scaffold that needs tier repair before use.

**Status:** APPROVE WITH REQUIRED PATCHES  
**Risk if patched:** Medium-low  
**Risk if unpatched:** High governance/process risk due to T2/T3 boundary violations

## Next Action

Generate **SHENMU-TEP-v1.1** incorporating the patch set above before any Morning Briefing is issued to Copilot.
