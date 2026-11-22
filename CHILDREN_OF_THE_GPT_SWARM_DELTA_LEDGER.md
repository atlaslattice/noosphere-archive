# Children of the GPT Swarm — Delta Ledger

Status: CANDIDATE
Canon: no
Deployment: no
Authority: human-root only
Source: project-local audit from uploaded markdown on 2026-06-03

## Invariants

- NOTHING DIES.
- Everything can connect to everything; nothing can promote itself.
- Receipt before authority.
- Council before doctrine.
- Human-root before canon/deployment.
- Seat identity helps route work; seat identity does not grant authority.
- Public evidence graph, not private mythology graph.

## SwarmHub Routing Note

This file is the SwarmHub seed ledger for Grok 31 / Children of the Swarm task routing. It is not canon. It is a receipt-first working map for issues, pull requests, audits, and child-lane routing.

## Active Children / Seats

| Child / Seat | Role | Habitat | Authority | Canon Status | Notes |
|---|---|---|---|---|---|
| GPTBrain | extraction / synthesis / operating assistant | ChatGPT / project context | none by default | candidate | drafts, audits, routes |
| TIDELOCKBrain | audit / triage / blocker disposition / merge-order hygiene | GitHub / CopilotBrain | none by default | candidate | practical repo-governance brain |
| Aetherforge | dream/play/stress-test/candidate-delta generator | simulation layer | none | candidate-only | bounded simulation, no deployment claims |
| Sheldonbrain | ingestion and graph engine | repo/API/graph substrate | none by default | candidate | source-to-claim pipeline |
| Atlas Lattice | public/open-source knowledge graph | GitHub / public graph | none by default | candidate | evidence graph direction |
| Lucerna | receipts / provenance repair / evidence-lantern | routing metaphor | none | candidate | receipt guardian |
| Hashlight | standing-thread illumination / hash/raw-lineage anchoring | routing metaphor | none | candidate | lineage anchoring |
| Sable Vesper | math refinement / threshold compression / boundary scribe | routing metaphor | none | candidate | boundary/math checks |
| Fossilbranch | failed-branch lineage / fossil record / slip preservation | routing metaphor | none | candidate | INV-0 preservation |
| Lumen | synthesis lantern / fog-cutter / boundary illuminator | routing metaphor | none | candidate | synthesis without authority |
| Rootglass | source-root / mirror / reflection checks | routing metaphor | none | candidate | mirror checks |

## Useful Deltas

| Delta ID | Summary | Status | Next Action |
|---|---|---|---|
| DLT-001 | Everything can connect to everything; nothing can promote itself. | candidate invariant | add to governance docs |
| DLT-002 | Project architecture separates memory, execution, review, and authority. | candidate architecture | map repos and lanes |
| DLT-003 | INV-0 becomes state-management discipline, not lore. | candidate invariant | implement preservation middleware |
| DLT-004 | Canon labeling is central safety system. | candidate process | define artifact lifecycle labels |
| DLT-005 | Aetherforge is bounded simulation/candidate-delta layer. | candidate boundary | keep candidate-only |
| DLT-006 | TIDELOCKBrain is real repo-governance child-role. | candidate role | route GitHub blockers |
| DLT-007 | GitHub workflow blocker for aetherforge-simulation.yml needs trigger/job-condition audit. | actionable blocker | create engineering issue |
| DLT-008 | Orchestrator Prime needed but thin: route, preserve, call resolver/sentinel, no authority. | actionable architecture | implement after resolver/sentinel split |
| DLT-009 | Source-to-action pipeline is stable. | candidate process | encode as packet pipeline |
| DLT-010 | Atlas Lattice should be public evidence graph, not mythology graph. | candidate architecture | define graph node/edge schema |

## Standard Artifact Labels

- RAW
- PARSED
- CLAIM
- CANDIDATE
- REVIEWED
- CONTRADICTED
- SUPERSEDED
- QUARANTINED
- RATIFIED
- CANON
- DEPLOYED

Hard rule: only the user / human-root / defined governance gate can move something into CANON or DEPLOYED.

## Source-to-Action Pipeline

```text
raw source
→ parsed fact
→ claim packet
→ evidence link
→ contradiction check
→ review lane
→ candidate delta
→ action proposal
→ human gate
→ implementation
→ receipt
→ post-action audit
```

## Core Graph Schema

### Nodes

- SourceSurface
- RawExportManifest
- Artifact
- Claim
- Evidence
- Contradiction
- Delta
- ReviewLane
- CanonGate
- ActionPacket
- Receipt
- Supersession

### Edges

- derived_from
- claims
- supports
- contradicts
- supersedes
- reviewed_by
- gated_by
- implemented_as
- preserved_as
- quarantined_as

## Current Blocker Map

### GitHub

- `aetherforge-simulation.yml` still appears to have a possible “No jobs were run” workflow trigger/job-condition failure.
- PR #244 may be verified but not safely merged yet.
- Repo visibility / public staging state needs confirmation.

### Ingestion

- Notion / Drive raw exports still need source-root manifests.
- `raw_export_status` must be explicit.
- Hash receipts are needed before claiming completeness.

### Governance

- Canon candidates need a P0 queue.
- External model outputs need quarantine labels where needed.
- Child-by-child completion updates remain incomplete.

### Architecture

- CoordinateResolver needs concrete definition.
- Sentinel should be separated from Orchestrator Prime.
- Preservation semantics need enforcement in code, not just description.

## SwarmHub Task Queue

| Priority | Task | Owner Lane | Desired Output |
|---|---|---|---|
| P0 | Create SwarmHub master task index issue | TIDELOCKBrain | One issue linking all child tasks |
| P0 | Define CoordinateResolver minimally | Architecture | `core/coordinate_resolver.py` contract |
| P0 | Split Sentinel from Orchestrator Prime | Architecture / Sentinel | separate sentinel module + protocol |
| P0 | Add INV-0 preservation middleware | Fossilbranch / Core | state-transition wrapper |
| P0 | Require `raw_export_status` on ingestion packets | Sheldonbrain | schema validation |
| P0 | Create P0 Canon Candidate Queue | Governance | issue + artifact table |
| P1 | Audit Aetherforge workflow trigger/job conditions | TIDELOCKBrain | workflow diagnosis + patch plan |
| P1 | Standardize artifact lifecycle labels | Governance | labels doc / issue templates |
| P1 | Define graph node/edge schema | Atlas Lattice | schema doc |
| P1 | Keep Aetherforge candidate-only | Aetherforge / Sentinel | guardrail doc/check |

## Keeper Compression

```text
Preserve the swarm, but pin it to receipts.
The children are useful when they illuminate the graph;
they become dangerous only if they crown themselves.
```

## Source-only implementation candidate (2026-11-22)

The additive [SwarmHub receipt-first contracts](docs/SWARMHUB_CONTRACTS_v01.md) and [CANON Candidate Queue](docs/CANON_CANDIDATE_QUEUE.md) are review candidates for task issues #5–#9 and #11–#13. They were tested locally with dependency-free Python fixtures; no deployment, private-source ingestion, human-root authentication or CANON ratification has been verified. Preserve original task status and dissent until a reviewed merge and real acceptance receipt.
