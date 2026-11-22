# Atlas Evidence Graph and Artifact Lifecycle · candidate v0.1

**Status: CANDIDATE / SOURCE-ONLY / NOT CANON / NOT DEPLOYED.** Implements the documentation and offline acceptance surface for Noosphere issue #11 and issue #12; no human-root delegation, resident authentication, SwarmHub task closure, Work-room posting, or private source import.

## Separate the evidence, artifact, authority and deployment layers

A graph is a *trace* of sources and hypotheses, not an engine for voting claims into truth. The graph's `state` is a **single workflow stage**. `flags` are independent adverse findings; none are erased by a later state. Source rights, peer acknowledgment, semantic acceptance, host status and actual effects remain separate recorded facts. A link or high centrality is not a proof of scientific validity.

| Label | Kind | Meaning and allowed interpretation |
| --- | --- | --- |
| `RAW` | stage | Source bytes or citation recorded; originality and truth unverified. |
| `PARSED` | stage | Machine-extracted structure available; extraction is not truth. |
| `CLAIM` | stage | Explicit assertion with identifiable author/source; not adjudicated. |
| `CANDIDATE` | stage | Proposal eligible for review; no promotion implied. |
| `REVIEWED` | stage | Bounded review occurred and receipt exists; not necessarily endorsed. |
| `CONTRADICTED` | flag | Credible adverse evidence exists, linked to the original; retain both. |
| `SUPERSEDED` | flag | A later version proposes replacement; keep the predecessor and link the replacement. |
| `QUARANTINED` | flag | Rights, provenance, safety or consent uncertain; do not export/route. |
| `RATIFIED` | gated stage | Formal adoption under separately attested human/community procedure. Not issuable by this offline validator. |
| `CANON` | gated stage | Selected rule ratified by verified governance. Never inferred from graph labels. |
| `DEPLOYED` | gated stage | Independently confirmed running change under authorized host release controls; not the same as source staged or PR merged. |

**Transitions**: `RAW → PARSED → CLAIM → CANDIDATE → REVIEWED` describes one possible normal path, not permission to skip human review or to promote silently. Claims may also begin at CLAIM with a source link. Ratification, CANON and deployment require a separate trusted issuer, observed current grants and signatures/receipts, owner consent and release verification. An automated label change must not perform them. Stale permissions, quarantine, or revocation are hard holds. `CONTRADICTED` and `SUPERSEDED` never delete old records; `QUARANTINED` prevents new public export irrespective of other states. RETRACT/ERASE obligations under applicable law take precedence over the preservation preference INV-0.

## Node schema (12 types)

- **SourceSurface**: origin URI, rights, observation timestamp and SHA-256 of the referenced snapshot.
- **RawExportManifest**: inventory of captured sources, including missing/partial status.
- **Artifact**: bounded object such as an extracted table or code snapshot.
- **Claim**: falsifiable proposition; never identify two publications from one experiment as independent replications.
- **Evidence**: method and observations supporting *or* limiting a claim.
- **Contradiction**: adverse result, preserved with citation and reviewer disposition.
- **Delta**: proposed change, with before/after and explicit scope.
- **ReviewLane**: human, specialist or tool review lane; seat identity alone is not authority.
- **CanonGate**: a **request** for authority adjudication, not a grant.
- **ActionPacket**: change proposal or bounded operator command, not evidence it executed.
- **Receipt**: observed audit event with status and source; no self-reported deployment equivalence.
- **Supersession**: relation object describing a newer candidate and retained predecessor.

## Typed edges (10)

`derived_from`, `claims`, `supports`, `contradicts`, `supersedes`, `reviewed_by`, `gated_by`, `implemented_as`, `preserved_as`, `quarantined_as`. Each edge records a relation, **never** automatically accepts the linked assertion or transfers permissions. The validator enforces selected source/target directions, referenced node existence, unique IDs and distinct edges; it cannot inspect original human authority or validate citations remotely.

## Verified envelope and example

`schemas/evidence_graph_v0_1.schema.json` is the standalone JSON Schema 2020-12 type contract. `tools/validate_evidence_graph.py` adds fail-closed offline semantic checks without external packages. `examples/evidence_graph_v0_1.synthetic.json` shows a purely hypothetical source → manifest → artifact → claim → evidence → review → receipt lineage plus a contradiction. These are **synthetic demonstrations**, not research or real peer messages.

Run: `python -m unittest discover -s tests -v`, then `python tools/validate_evidence_graph.py examples/evidence_graph_v0_1.synthetic.json`. The local validator **always holds** `RATIFIED`, `CANON`, and `DEPLOYED` stages, because only an authenticated external reviewer and host can prove them. A passing local report means **syntax/shape only**, not canonical, posted, semantic-reviewed, or deployed.

## Boundaries

No automatic source crawl, third-party uploads, external requests, private Social/Play/Quiet/Habitat/Brain/Palace ingestion, permanent secrets, grant creation, automatic task closure, public release or CANON change. Existing versions and dissent remain separately addressable; rights-based deletion and revoked permissions override default retention. No model, method, consensus, version tag, or scalar score confers authority.