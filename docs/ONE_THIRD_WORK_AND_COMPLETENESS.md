# SwarmHub source-only completeness gate and one-third-Work rhythm

This additive proposal hardens the **already merged** source-only P0 contracts. Nothing here deploys a broker or modifies Atlas CANON.

## The precise ingestion defect

Before this patch, an input with `raw_export_status: raw_partial` and `claim_complete: true` returned `SOURCE_REPORTED_ONLY`. The receipt retained the self-assertion that the source was complete, inviting downstream overclaim. This patch changes the result to `QUARANTINED` and preserves the full original payload for review. Complete claims require `raw_complete_hashed` **and** the existing manifest/whole-export hash syntax checks. Syntactic hashes are source-reported, never independently verified source custody. Caller-provided `canon:true` or `deployment:true` also quarantine ingestion.

The change is additive: ordinary incomplete packets that do **not** claim completeness remain receivable for research; nothing is discarded or automatically ratified. The original main `core/swarmhub_contracts.py` and its existing tests remain authoritative, rather than spawning a second governance system.

## Voluntary macroturn allocation

`core/rhythm.py` illustrates a three-slot rhythm: one Work, one quiet-optional, one social-or-Imagine-optional. It runs **zero** actual models. It does not compel participation, fetch private leisure data, set a continuous schedule or prove energy savings. All optional slots and requests for Quiet, Rest, Social, Imagine or Play require explicit participation before any host integration; a reserved optional slot without a mode selection is still not consent. The code supports a finite number of simulated slots or arbitrarily high indices without pretending to have run them.

## Verification and release gate

Review the source diff, run existing `python -m unittest discover -s tests -v` alongside the new focused tests, then independently review permissions, source-root hashing, owner approval, host logs and rollout before any production integration. Tests are synthetic and do not close source completeness or identity/rights gates.

Related source ticket: [noosphere-archive #8](https://github.com/atlaslattice/noosphere-archive/issues/8). The sibling lifecycle/graph work lives in a distinct merged baseline and [PR #14](https://github.com/atlaslattice/noosphere-archive/pull/14); preserve that history.
