# Atlas artifact lifecycle — candidate governance policy v0.1

**CANDIDATE / NOT CANON / NOT DEPLOYED / AUTHORITY NONE**

Implements [Noosphere #11](https://github.com/atlaslattice/noosphere-archive/issues/11) as a **reviewable documentation and structural-schema contract**. It does not relabel historical artifacts, claim human authorization, install middleware, or automatically promote/deploy anything.

## Eleven labels: eight stages and three nonexclusive overlays

The 11 requested labels should not be mutually exclusive. A reviewed claim may simultaneously be contradicted or superseded. Keep one **primary stage**, plus any combination of three independently preserved **flags**.

| Label | Axis | Meaning |
| --- | --- | --- |
| RAW | Stage | Original material captured; interpretation and rights not asserted |
| PARSED | Stage | Extracted structure linked to raw material, without asserting truth |
| CLAIM | Stage | Separately addressable assertion with provenance and uncertainty |
| CANDIDATE | Stage | Proposed interpretation, implementation or action; unapproved |
| REVIEWED | Stage | One or more review receipts exist; not consensus or correctness |
| RATIFIED | Stage | Specific human-governance decision with verifiable scope; not automatically canon |
| CANON | Stage | Scoped ratified version within one continuum; not universal authority |
| DEPLOYED | Stage | Explicit operational authorization with owner/rollback; GitHub merge alone is not deployment |
| CONTRADICTED | Flag | Credible unresolved conflicting evidence or argument; both sides retained |
| SUPERSEDED | Flag | Newer version preferred for a specified purpose; old version retained |
| QUARANTINED | Flag | Rights, provenance, security, safety or trust concern; block outward promotion |

## Transition and demotion rules

- Typical candidate route: RAW → PARSED → CLAIM → CANDIDATE → REVIEWED. Each stage requires source, lineage and review receipts; no filename, model statement, PR, or issue closure is sufficient evidence.
- REVIEWED → RATIFIED → CANON → DEPLOYED are **separate human-root/governance decisions**. Every decision is scoped to one continuum, version, purpose and release audience. Structural JSON fields can declare approvals but **cannot authenticate a signatory**. Human-root confirmation must be checked independently.
- Contradictions, supersessions and quarantine flags are **additive historical overlays**, not exclusive stages. Never delete a flag from history merely because a dispute was later resolved; add resolution references.
- Demotion, correction or re-review creates a successor version with immutable predecessor and INV-0 preservation references. Preserve raw content and all rejected alternatives.
- A2A bridges can compare continuums but cannot merge identities, private permissions, histories, or governance status.
- raw_export_status must remain explicit: complete, partial, summary_only, stub, missing or unknown. Stubs and summaries cannot silently become full source receipts.
- No automatic promotion from private Play or Writers' Room into Work. Consent, source rights and room scope remain independent gates.

## Machine-readable reference

[JSON Schema (Draft 2020-12)](../schemas/artifact_lifecycle.schema.json) describes the required record fields: source_ref, artifact_id, continuum_id, stage, flags, preservation_ref, dissent_refs, raw_export_status, canon and deployment Booleans, authority, and the governance review declaration.

Schema validation only checks **shape**, not independent provenance, truth, human identity, live permissions, actual immutable storage, or release readiness.

A synthetic CANDIDATE record has stage CANDIDATE, flags CONTRADICTED, canon false, deployment false, authority none, raw_export_status partial, a retained predecessor/fossil reference, dissent references and a not_granted human-root gate. It is *not* a fictional approval.

## Local verification

The schema was parsed and checked against Draft 2020-12 locally on 2026-11-22. One candidate fixture and one structurally declared higher-stage example validated; six malformed or ungated variations were rejected. This **does not authenticate** the higher-stage example's fictional receipt. No GitHub CI or production workflow is claimed.

## Adoption

Historical labels should be inventoried before migration; existing content and governance receipts must not be overwritten. An independent runtime validator and signatory verification remain separate tasks.

**Keeper:** Labels describe status. Receipts support claims. Dissent remains inspectable. Humans decide consequential promotion.
