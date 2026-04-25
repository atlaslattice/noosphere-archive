# Public Release Readiness Audit

Date: 2026-04-25
Owner: atlaslattice
Purpose: controlled public release of private repositories after contamination and framing review.

## Rule

Do not bulk-publicize every private repository. Publish only after a repo has passed this checklist:

- No secrets, tokens, credentials, keys, API endpoints with private auth, or private account IDs.
- No personal health data, private correspondence, phone numbers, home addresses, or identifying private information.
- No unlicensed proprietary source/code/content.
- No wording that could reasonably be misconstrued as advocacy of violence, fraud, sabotage, evasion, harassment, or unlawful disruption.
- Sensitive domains include medical, mental health, finance, banking, policing, military, immigration, child safety, prisons, insurance, credit, and surveillance.
- Sensitive repos need a README/publication context header before publication.

## Standard publication context header

```md
# Publication Context

This repository is a research archive and policy/technical exploration.
It does not advocate violence, fraud, evasion, harassment, sabotage, or unlawful activity.
Any financial, legal, medical, military, or public-sector references are for governance, transparency, interoperability, accountability, and safety analysis only.

Status: Draft research archive.
```

## Batch 1 — likely low-risk publication candidates

These should still get a quick README/license/secrets check, but are comparatively safe to publish early:

| Repo | Current state | Risk tier | Required action |
|---|---|---|---|
| atlaslattice/noosphere-archive | private | low | Add README context if missing; publish after check |
| atlaslattice/educational-ai | private | low-medium | Add README context; publish after check |
| atlaslattice/climate-ai-solutions | private | low | Add README context; publish after check |
| atlaslattice/water-management-ai | private | low | Add README context; publish after check |
| atlaslattice/waste-management-ai | private | low | Add README context; publish after check |
| atlaslattice/agricultural-ai | private | low | Add README context; publish after check |
| atlaslattice/disability-tech-access | private | low-medium | Add accessibility/public-benefit framing; publish after check |
| atlaslattice/elder-care-tech | private | medium | Add care/medical disclaimer; publish after check |
| atlaslattice/supply-chain-transparency | private | low-medium | Add public-interest framing; publish after check |
| atlaslattice/construction-safety-ai | private | low-medium | Add safety/research framing; publish after check |
| atlaslattice/retail-automation | private | medium | Add labor-impact framing; publish after check |
| atlaslattice/call-center-automation | private | medium | Add labor-impact framing; publish after check |

## Batch 2 — publish only after README/context patch

These are publishable, but need explicit framing to prevent misread claims or harm narratives:

| Repo | Current state | Risk tier | Required action |
|---|---|---|---|
| atlaslattice/healthcare-ai | private | high | Medical disclaimer + no-clinical-use statement |
| atlaslattice/mental-health-ai | private | high | Crisis/non-clinical disclaimer + escalation framing |
| atlaslattice/child-safety-ai | private | high | Child-safety disclaimer + avoid operational misuse |
| atlaslattice/pharmaceutical-ai | private | high | Medical/pharma research disclaimer |
| atlaslattice/insurance-ai-bias | private | high | Policy/audit framing; avoid claims of legal advice |
| atlaslattice/recruitment-ai-bias | private | medium | Audit/research framing |
| atlaslattice/legal-ai-ethics | private | high | Not legal advice disclaimer |
| atlaslattice/voice-assistant-privacy | private | medium | Privacy/security disclaimer |
| atlaslattice/smart-home-security | private | medium | Defensive security framing only |
| atlaslattice/translation-ai-bias | private | medium | Bias-research framing |
| atlaslattice/energy-grid-ai | private | high | Critical infrastructure safety framing |
| atlaslattice/transportation-ai | private | medium-high | Safety-critical research framing |
| atlaslattice/logistics-exploitation | private | medium-high | Labor/policy framing; neutralize inflammatory wording |
| atlaslattice/food-delivery-exploitation | private | medium-high | Labor/policy framing; neutralize inflammatory wording |
| atlaslattice/gig-economy-exploitation | private | medium-high | Labor/policy framing; neutralize inflammatory wording |
| atlaslattice/content-moderation-trauma | private | medium-high | Mental health/labor trauma framing |
| atlaslattice/social-media-harm | private | medium-high | Public-interest safety framing |
| atlaslattice/streaming-economics | private | medium | Creator-economy framing |
| atlaslattice/gaming-labor | private | medium | Labor/research framing |
| atlaslattice/academic-publishing | private | low-medium | Research policy framing |
| atlaslattice/creative-ai-rights | private | medium | Copyright/creator rights framing |
| atlaslattice/journalism-ai | private | medium | Journalism ethics framing |
| atlaslattice/housing-crisis-ai | private | medium-high | Housing policy framing |

## Batch 3 — hold until manual contamination audit

These are not necessarily unsafe, but their names/domains are easy to misconstrue. Do not publish until manually reviewed and reframed.

| Repo | Current state | Risk tier | Required action |
|---|---|---|---|
| atlaslattice/banking-revolution | private | very high | Rename/reframe before public; audit for “bank killer” language |
| atlaslattice/banking-revolution-archive | private | very high | Archive audit; reframe as open banking/interoperability research |
| atlaslattice/fintech-disruption | private | high | Reframe as fintech interoperability/accountability research |
| atlaslattice/credit-scoring-injustice | private | high | Audit for legal/financial claims; add public-policy framing |
| atlaslattice/military-ai-ethics | private | very high | Audit for weapons/targeting language; add non-violence/HITL framing |
| atlaslattice/police-surveillance | private | very high | Audit for surveillance/evasion language; public-interest framing only |
| atlaslattice/immigration-tech | private | very high | Audit for sensitive personal/political claims |
| atlaslattice/prison-tech-ethics | private | very high | Audit for safety, rights, carceral policy framing |
| atlaslattice/surveillance-capitalism | private | high | Reframe critique as policy/research archive |
| atlaslattice/ai-safety-hypocrisy | private | high | Tone reduction; avoid personal/institutional attacks |
| atlaslattice/ai-labor-exploitation | private | high | Labor-rights framing; tone review |
| atlaslattice/accounting-ai-ethics | private | medium-high | Empty/private; audit before public |

## Public repos already visible

Several repos are already public and may also need README/context cleanup, but visibility risk has already occurred. Prioritize private-to-public flow first, then review public profile coherence.

Known public examples from inventory:

- atlaslattice/sheldonbrain-rag-api
- atlaslattice/Sovereign-Shredder-Core
- atlaslattice/A2A
- atlaslattice/awesome-ai-ethics
- atlaslattice/ai-bias-detection
- atlaslattice/algorithmic-accountability
- atlaslattice/deepfake-detection
- atlaslattice/ai-transparency-toolkit
- atlaslattice/ethical-ai-guidelines
- atlaslattice/ai-fairness-metrics
- atlaslattice/machine-learning-bias
- atlaslattice/ai-labor-practices
- atlaslattice/content-moderation-ethics
- atlaslattice/ai-safety-research
- atlaslattice/responsible-ai-toolkit
- atlaslattice/ai-governance-framework
- atlaslattice/explainable-ai-tools
- atlaslattice/ai-risk-assessment
- atlaslattice/data-privacy-tools
- atlaslattice/ai-audit-framework
- atlaslattice/algorithmic-justice
- atlaslattice/ai-worker-rights
- atlaslattice/tech-ethics-resources
- atlaslattice/ai-impact-assessment
- atlaslattice/facial-recognition-ethics
- atlaslattice/ai-surveillance-critique
- atlaslattice/gig-economy-analysis
- atlaslattice/platform-worker-rights
- atlaslattice/ai-copyright-issues
- atlaslattice/synthetic-media-ethics
- atlaslattice/ai-misinformation-detection
- atlaslattice/automated-decision-systems
- atlaslattice/ai-accountability-tools
- atlaslattice/digital-rights-toolkit
- atlaslattice/ai-regulation-tracker
- atlaslattice/tech-worker-organizing
- atlaslattice/ai-training-data-ethics
- atlaslattice/algorithmic-discrimination
- atlaslattice/ai-policy-analysis
- atlaslattice/tech-accountability-framework
- atlaslattice/ai-employment-impact
- atlaslattice/digital-labor-rights
- atlaslattice/ai-consent-framework
- atlaslattice/predictive-policing-critique
- atlaslattice/ai-healthcare-ethics
- atlaslattice/automated-hiring-bias
- atlaslattice/ai-credit-scoring-fairness
- atlaslattice/social-media-algorithms
- atlaslattice/ai-content-moderation
- atlaslattice/tech-monopoly-analysis
- atlaslattice/ai-pricing-discrimination
- atlaslattice/digital-surveillance-tools
- atlaslattice/ai-recommendation-systems

## Addendum — public repo rationalization plan

Public visibility already happened for many repos. The job is therefore not only “what can become public?” but also:

1. What should stay public as a credible standalone project?
2. What should be moved private if visibility reversal is possible and justified?
3. What should be harvested into Aluminum OS / UWS / Noosphere archive, then archived or deleted?
4. What should be renamed or reframed because the repo name creates unnecessary volatility?

### Public repo action categories

| Category | Meaning |
|---|---|
| KEEP PUBLIC | Good standalone repo or harmless public-interest topic. Add README/license polish only. |
| KEEP PUBLIC + CONTEXT | Can remain public, but needs a publication-context header or tone cleanup. |
| HARVEST / MERGE | Useful material should be migrated into a canonical repo, then the original repo archived. |
| CONSIDER PRIVATE | Public exposure may be reputationally or operationally noisy; make private if contents justify it. |
| DELETE / EMPTY ARCHIVE | Empty, duplicate, or low-value shell repo. Delete only after confirming no unique history. |

### Existing public repos — initial classification

| Repo | Initial action | Rationale / destination |
|---|---|---|
| atlaslattice/sheldonbrain-rag-api | KEEP PUBLIC + CONTEXT | Core infrastructure/retrieval work. Add sober README and security note. |
| atlaslattice/Sovereign-Shredder-Core | KEEP PUBLIC + CONTEXT | Name is intense; review for “shredder” misread. Reframe as secure document redaction/destruction if accurate. |
| atlaslattice/A2A | KEEP PUBLIC | Likely protocol/integration repo. Add README that explains scope. |
| atlaslattice/awesome-ai-ethics | KEEP PUBLIC | Low risk; good credibility surface. |
| atlaslattice/ai-bias-detection | KEEP PUBLIC | Low-medium risk; standard ethics topic. |
| atlaslattice/algorithmic-accountability | KEEP PUBLIC | Strong public-interest topic. |
| atlaslattice/deepfake-detection | KEEP PUBLIC + CONTEXT | Defensive framing only. Avoid offensive generation language. |
| atlaslattice/ai-transparency-toolkit | KEEP PUBLIC | Strong public-interest/tooling framing. |
| atlaslattice/ethical-ai-guidelines | KEEP PUBLIC | Low risk. |
| atlaslattice/ai-fairness-metrics | KEEP PUBLIC | Low-medium risk; good research topic. |
| atlaslattice/machine-learning-bias | KEEP PUBLIC | Low-medium risk. |
| atlaslattice/ai-labor-practices | KEEP PUBLIC + CONTEXT | Labor framing should be careful, not inflammatory. |
| atlaslattice/content-moderation-ethics | KEEP PUBLIC + CONTEXT | Add trauma/labor disclaimer; avoid sensational claims. |
| atlaslattice/ai-safety-research | KEEP PUBLIC | Credibility-positive if sober. |
| atlaslattice/responsible-ai-toolkit | KEEP PUBLIC | Strong public-facing repo. |
| atlaslattice/ai-governance-framework | KEEP PUBLIC | Strong public-facing repo. |
| atlaslattice/explainable-ai-tools | KEEP PUBLIC | Low risk. |
| atlaslattice/ai-risk-assessment | KEEP PUBLIC | Low-medium risk. |
| atlaslattice/data-privacy-tools | KEEP PUBLIC + CONTEXT | Defensive/privacy framing. Avoid surveillance or evasion language. |
| atlaslattice/ai-audit-framework | KEEP PUBLIC | Strong public-facing repo. |
| atlaslattice/algorithmic-justice | KEEP PUBLIC + CONTEXT | Good topic, but add nonpartisan policy/research framing. |
| atlaslattice/ai-worker-rights | KEEP PUBLIC + CONTEXT | Labor topic; keep sober and constructive. |
| atlaslattice/tech-ethics-resources | KEEP PUBLIC | Low risk. |
| atlaslattice/ai-impact-assessment | KEEP PUBLIC | Strong public-facing repo. |
| atlaslattice/facial-recognition-ethics | KEEP PUBLIC + CONTEXT | Sensitive surveillance domain; policy/ethics framing required. |
| atlaslattice/ai-surveillance-critique | KEEP PUBLIC + CONTEXT | Critique is valid; avoid evasion/sabotage implications. |
| atlaslattice/gig-economy-analysis | KEEP PUBLIC + CONTEXT | Labor/economics framing. |
| atlaslattice/platform-worker-rights | KEEP PUBLIC + CONTEXT | Labor framing. |
| atlaslattice/ai-copyright-issues | KEEP PUBLIC + CONTEXT | Not legal advice disclaimer. |
| atlaslattice/synthetic-media-ethics | KEEP PUBLIC | Public-interest topic. |
| atlaslattice/ai-misinformation-detection | KEEP PUBLIC + CONTEXT | Defensive/detection framing only. |
| atlaslattice/automated-decision-systems | KEEP PUBLIC | Standard governance topic. |
| atlaslattice/ai-accountability-tools | KEEP PUBLIC | Strong public-facing repo. |
| atlaslattice/digital-rights-toolkit | KEEP PUBLIC | Strong public-facing repo. |
| atlaslattice/ai-regulation-tracker | KEEP PUBLIC + CONTEXT | Not legal advice; cite sources carefully. |
| atlaslattice/tech-worker-organizing | KEEP PUBLIC + CONTEXT | Labor organizing can be public; avoid calls for sabotage/harassment. |
| atlaslattice/ai-training-data-ethics | KEEP PUBLIC | Standard governance topic. |
| atlaslattice/algorithmic-discrimination | KEEP PUBLIC + CONTEXT | Public-interest framing. |
| atlaslattice/ai-policy-analysis | KEEP PUBLIC + CONTEXT | Nonpartisan/source-backed framing. |
| atlaslattice/tech-accountability-framework | KEEP PUBLIC | Strong public-facing repo. |
| atlaslattice/ai-employment-impact | KEEP PUBLIC + CONTEXT | Labor/economics framing. |
| atlaslattice/digital-labor-rights | KEEP PUBLIC + CONTEXT | Labor framing. |
| atlaslattice/ai-consent-framework | KEEP PUBLIC | Strong governance topic. |
| atlaslattice/predictive-policing-critique | KEEP PUBLIC + CONTEXT | Sensitive public-sector topic; avoid evasion/operational claims. |
| atlaslattice/ai-healthcare-ethics | KEEP PUBLIC + CONTEXT | Medical disclaimer needed. |
| atlaslattice/automated-hiring-bias | KEEP PUBLIC + CONTEXT | Employment/legal disclaimer. |
| atlaslattice/ai-credit-scoring-fairness | KEEP PUBLIC + CONTEXT | Financial/legal disclaimer. |
| atlaslattice/social-media-algorithms | KEEP PUBLIC + CONTEXT | Platform-safety framing. |
| atlaslattice/ai-content-moderation | KEEP PUBLIC + CONTEXT | Platform-safety and labor framing. |
| atlaslattice/tech-monopoly-analysis | KEEP PUBLIC + CONTEXT | Source-backed policy/economics framing. |
| atlaslattice/ai-pricing-discrimination | KEEP PUBLIC + CONTEXT | Financial/legal disclaimer; no accusations without sources. |
| atlaslattice/digital-surveillance-tools | CONSIDER PRIVATE / REFRAME | Name can sound like tooling for surveillance. If defensive/critique, rename/reframe. |
| atlaslattice/ai-recommendation-systems | KEEP PUBLIC | Standard topic; add safety framing if needed. |

### Harvest / merge targets

These public repos may be more powerful as sections inside canonical repositories rather than standalone fragments:

| Source repo group | Destination |
|---|---|
| AI ethics / governance shells | `atlaslattice/noosphere-archive` or `atlaslattice/aluminum-os/docs/governance/` |
| AI audit / accountability tools | `atlaslattice/uws` if executable, otherwise `aluminum-os/docs/governance/` |
| Labor/economics repos | `noosphere-archive/labor/` or a future `regenerative-labor` repo |
| Privacy/surveillance critique repos | `noosphere-archive/privacy-surveillance/` |
| Healthcare/mental health repos | hold for a separate `health-governance` archive with strong disclaimers |
| Banking/fintech/credit repos | hold for a separate `open-finance-interoperability` archive after tone review |

### Public repo cleanup requests for agents/humans

For each public repo, review:

- Does README exist?
- Does README explain the purpose in one sober paragraph?
- Is there a license?
- Is there any generated placeholder content that looks empty or spammy?
- Does the repo name overpromise or sound hostile?
- Does the repo contain secrets, private identifiers, or copied proprietary content?
- Should the repo be archived after its useful content is harvested?

### Naming guidance for volatile repos

Avoid names that sound like revolutionary disruption, institutional attack, or operational harm.
Prefer names that communicate public-interest research, interoperability, accountability, and governance.

Examples:

| Avoid | Prefer |
|---|---|
| bank killer app | open banking interoperability toolkit |
| banking revolution | regenerative finance research archive |
| fintech disruption | fintech accountability and interoperability |
| surveillance tools | surveillance accountability research |
| AI safety hypocrisy | AI safety accountability review |
| labor exploitation | labor impact and platform accountability |

## Recommended next actions

1. Add a standard README/publication context header to Batch 1 repos.
2. Spot-check Batch 1 contents for secrets and personal data.
3. Only after explicit approval, publish Batch 1 via an allowlist.
4. Patch Batch 2 with domain-specific disclaimers.
5. Hold Batch 3 until manual review and possible repo rename/reframe.
6. Review existing public repos for keep/context/harvest/private/delete action.
7. Create a canonical `PUBLIC_PROFILE.md` explaining the atlaslattice portfolio as public-interest systems research.

## Allowlist template

```txt
atlaslattice/noosphere-archive
atlaslattice/educational-ai
atlaslattice/climate-ai-solutions
atlaslattice/water-management-ai
atlaslattice/waste-management-ai
atlaslattice/agricultural-ai
atlaslattice/disability-tech-access
atlaslattice/elder-care-tech
atlaslattice/supply-chain-transparency
atlaslattice/construction-safety-ai
```
