# Public Release Audit — Public-Safe Criteria

Date: 2026-04-25
Owner: atlaslattice
Status: Public-safe governance criteria

## Purpose

This document defines the public release criteria for atlaslattice repositories. It is intentionally written without enumerating private or sensitive repository names.

The goal is to publish public-interest systems research in a controlled, reviewable way while protecting private information, reducing misuse risk, and keeping sensitive work properly contextualized.

## Operating rule

No repository should be made public through a blanket visibility change.

Publication should happen only through an explicit allowlist after a repository passes release-readiness review.

## Release-readiness checklist

Before publication, each repository should be reviewed for:

- Secrets, tokens, credentials, API keys, private endpoints, and internal hostnames.
- Personally identifying information, private correspondence, phone numbers, addresses, or private account identifiers.
- Personal health information or sensitive biographical information.
- Unlicensed third-party source code, copied proprietary content, or unclear provenance.
- Domain-sensitive language that could be misconstrued as advocacy of violence, fraud, sabotage, evasion, harassment, or unlawful disruption.
- Medical, legal, financial, public-safety, education, labor, surveillance, or critical-infrastructure claims that require clear disclaimers.
- Generated or draft content that overstates certainty, lacks sources, or reads as operational guidance rather than research analysis.

## Risk tiers

### A — Low-risk early public candidate

Repository can be considered for early publication after standard checks and a basic README context layer.

Typical examples:

- climate and environmental analysis
- water and waste-management research
- agriculture and public-infrastructure research
- general AI governance resources

### B — Domain-sensitive candidate

Repository may still be publishable, but requires stronger disclaimers and deeper review.

Typical examples:

- education and student privacy
- disability and accessibility technology
- supply-chain transparency
- construction or safety systems
- labor and employment impact analysis
- privacy and security tooling

### C — Hold pending manual review

Repository should not be included in early publication. It requires manual review, possible renaming, and careful context.

Typical examples:

- healthcare, mental health, elder care, or child safety
- banking, finance, credit, insurance, or payments
- military, policing, prisons, immigration, or public-sector enforcement
- surveillance, security, or critical infrastructure
- highly political or institution-critical research

## Standard publication context header

Recommended README opening for draft research archives:

```md
# Publication Context

This repository is a research archive and policy/technical exploration.
It does not advocate violence, fraud, evasion, harassment, sabotage, or unlawful activity.
Any financial, legal, medical, military, public-sector, education, labor, infrastructure, or safety references are for governance, transparency, interoperability, accountability, and safety analysis only.

Status: Draft research archive.
```

## Domain-specific disclaimer patterns

### Education

This repository is not a substitute for educators, school administrators, parents, or student-support professionals. Any education-related analysis must respect student privacy, accessibility requirements, and local law.

### Disability and accessibility

This repository is not a medical device, diagnostic tool, or substitute for accessibility professionals. Accessibility claims should be treated as research hypotheses until independently validated with affected users and qualified experts.

### Construction and safety

This repository is not a certified safety system and must not be used as the sole basis for construction, workplace, engineering, or life-safety decisions.

### Supply chain

This repository is focused on transparency, resilience, compliance, and accountability. It does not provide operational guidance for sabotage, interdiction, evasion, or unlawful disruption.

### Healthcare and mental health

This repository is not medical advice, diagnosis, treatment, or crisis intervention. Any health-related content is research-only and requires qualified clinical oversight before real-world use.

### Finance and banking

This repository is research-only and does not provide financial, legal, tax, investment, fraud, evasion, or regulatory-compliance advice.

### Military, policing, prisons, immigration, and public safety

This repository is for governance, rights, oversight, safety, accountability, and human-in-the-loop analysis. It does not provide tactical, coercive, evasion, targeting, or enforcement guidance.

## Publication workflow

1. Classify the repository into Tier A, B, or C.
2. Run release-readiness review.
3. Add or update README context.
4. Add a license or mark rights status clearly.
5. Open a reviewable PR or commit.
6. Add the repository to a publication allowlist only after explicit approval.
7. Change visibility repo-by-repo, never through a blanket bulk script.

## Recommended public posture

The atlaslattice portfolio should read as serious public-interest systems research:

- constructive over incendiary
- accountable over oppositional
- safety-oriented over disruptive
- research/prototype framing over deployment claims
- explicit human oversight in sensitive domains

## Naming guidance

Avoid names that sound like institutional attack, revolutionary disruption, or operational harm.

Prefer names that communicate public-interest research, interoperability, accountability, and governance.

| Avoid | Prefer |
|---|---|
| bank killer app | open banking interoperability toolkit |
| banking revolution | regenerative finance research archive |
| fintech disruption | fintech accountability and interoperability |
| surveillance tools | surveillance accountability research |
| AI safety hypocrisy | AI safety accountability review |
| labor exploitation | labor impact and platform accountability |

## Public release principle

Make the work public when it is ready to be understood correctly.

The goal is not to dilute the ideas. The goal is to publish them with enough structure, context, and safety framing that serious readers can evaluate them on their merits.
