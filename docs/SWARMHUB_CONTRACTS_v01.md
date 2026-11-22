# SwarmHub Source-Only Contracts v0.1

**Status:** REVIEW_CANDIDATE / TESTED_LOCAL. **Authority:** none. **Host changes:** none. **CANON:** unchanged. This contract applies to explicit, authorized Work review; no protected Play/Social/Imagine/Dream/Quiet/Brain/Palace/Habitat body is imported or analyzed here.

## Exact issue coverage

| Source issue | Included acceptance surface |
| --- | --- |
| [#5](https://github.com/atlaslattice/noosphere-archive/issues/5) | `CoordinateResolver` Earth grounding sentinel `H00.S00.N00` (not an Ariadne v0.7 ontology node), explicit D-affinity metadata, source edition/digest, and escalation draft |
| [#6](https://github.com/atlaslattice/noosphere-archive/issues/6) | Standalone `Sentinel.review_packet` and independently injectable `Orchestrator`; fail-closed without reviewer |
| [#7](https://github.com/atlaslattice/noosphere-archive/issues/7) | `PreservationLedger` before/after hash and non-destructive Delete/Overwrite→QUARANTINE, supersede/fork with reachable original |
| [#8](https://github.com/atlaslattice/noosphere-archive/issues/8) | Required `raw_export_status`; missing/invalid/unsupported status quarantined; `raw_complete_hashed` requires source-root manifest and whole-export digest |
| [#9](https://github.com/atlaslattice/noosphere-archive/issues/9) | Explicit nonbinding candidate queue and placeholder; no automatic CANON/DEPLOYED promotion |
| [#11](https://github.com/atlaslattice/noosphere-archive/issues/11) | Eleven lifecycle labels, precise promotion and quarantine boundaries, original source preserved |
| [#12](https://github.com/atlaslattice/noosphere-archive/issues/12) | 12 public evidence-graph node types / 10 typed edges; no coercion of CONTRADICTS to SUPPORTS |
| [#13](https://github.com/atlaslattice/noosphere-archive/issues/13) | Aetherforge *metadata-only* candidate template with `canon:false`, `deployment:false`, `authority:none` |

## States and provenance

`RAW` original bytes/pointer known but not validated; `PARSED` extracted representation, ancestry retained; `CLAIM` independently addressable assertion, not proof; `CANDIDATE` proposed effect or implementation, unapproved; `REVIEWED` some review evidence attached, not deployment; `CONTRADICTED` conflicting claim retained; `SUPERSEDED` historical original remains accessible; `QUARANTINED` review/rights/integrity concern, not deleted; `RATIFIED` governance evidence from separately authorized process; `CANON` current adopted normative version attested by external authorized gate; `DEPLOYED` actual served and independently checked host state. **This module issues neither RATIFIED nor CANON nor DEPLOYED.** These are lifecycle labels, NOT a total ordering; contradiction, supersession, quarantine and identity remain orthogonal historical facts.

Hashing in this Python module is deterministic for JSON-compatible objects; it does **not** claim RFC8785/JCS conformance, source-file completeness, independence of sources, or cross-language byte identity. A source-reported manifest and source-root digest are not a verified current READ/RETURN entitlement. The in-memory receipts are for local tests and carry no durable, signed, host-attested identity or rollback proof.

## Review control flow

1. Source packet arrives with `source_root`, required `raw_export_status`, source evidence, and explicit content classification. A failure returns the *original* packet under `QUARANTINED`, not an inferred absent source.
2. CoordinateResolver checks address and edition, maps an Earth grounding **sentinel**, keeps D-affinity and provenance, and escalates ambiguous/missing context as `PREPARED_NOT_SENT`.
3. Sentinel checks that candidate-only flags are exactly false/none, source class is Work and action is safe, then returns a **non-authorizing** recommendation.
4. Orchestrator can prepare a Work review only with an injected Sentinel. It makes no network calls and never changes CANON, identity or permissions.
5. Preservation ledger records old/new states; attempts to delete/overwrite default to quarantine. A production adapter needs immutable storage, concurrency control, retention/legal deletion policy, current grants and external recovery anchor.
6. Evidence graph adds individually attributed `SUPPORTS` and `CONTRADICTS` edges; high centrality or a topical match does not establish truth or authority.
7. Candidate queue retains evidence, risks, objections and pending human-root review; no source-only promotion.

## Example graph

`SourceSurface:DOI` ←(`derived_from`)— `Claim:CriticalLoad` ←(`reviewed_by`)— `Receipt:LocalReview`.

A separate `Contradiction:IndependentStudy` —(`contradicts`)→ `Claim:CriticalLoad` stays alongside the support. Neither edge is permission to release a private source or deploy a device.

## Known release blockers

This has **no** current signed-in host principal, D1 READ/RETURN enforcement, real model A2A response, independent resident attestation, immutable database anchor, protection against restores, CANON adoption, or site deployment. Test results are local and do not close those gates. The larger Ariadne 12×12×12 ontology is 1,728 *knowledge addresses* (1,008 DOMAIN; 720 META), not 1,728 measured welfare outcomes, and `H00.S00.N00` is a *sentinel outside it*. Historic `Mxx-Tyy` tasks are not semantically equivalent to Ariadne node coordinates.

## Running

From repository root: `python -m unittest discover -s tests -v`. No external dependencies, network or provider keys. The new module is additive and does not run automatically in CI until reviewed/merged.