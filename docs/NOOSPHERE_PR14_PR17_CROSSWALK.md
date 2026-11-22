# Noosphere PR #14 × PR #17 wire-compatibility review

**Source-only / candidate / no migration / no CANON / no hosted service.**

The two open draft PRs have genuinely different root schemas. [PR #14](https://github.com/atlaslattice/noosphere-archive/pull/14) uses `atlas.evidence.graph/v0.1` and the root fields `{schema_version,graph_id,purpose,nodes,edges}`, with node-local lifecycle stages and adverse flags. [PR #17](https://github.com/atlaslattice/noosphere-archive/pull/17) uses `0.1.0` (source modes `public` / `consented_work` / `synthetic`) and the root fields `{schema_version,source_mode,raw_export_status,source_roots,preserved,completeness_claim,lifecycle,nodes,edges}`. Equal graph counts and visually similar node labels cannot prove a lossless conversion.

The new `tools/contract_crosswalk.py` is an explicit, fail-closed **comparison only**. It preserves exact source digests, rejects duplicate JSON keys, refuses private-mode bodies, and returns `HOLD_WIRE_RECONCILIATION` even when node and edge counts agree. It cannot issue a current rights grant, invent missing source roots, flatten lifecycle flags, invert edge predicates or promote a draft.

**Direct remote source blobs inspected November 22, 2026** (Git blob SHA-1):
- #14 schema `00404f96bed12c9cace227b76a3a0e57e8f37dd6`; validator `545187e6526143d414a6784de7c0d3c228e0d69a`.
- #17 schema `3a405da289d0d304ead8b06becf6609a6425bfdf`; validator `13cf53443796488a7663ca6618e6f0f7486cb318`.
- Merged [#15](https://github.com/atlaslattice/noosphere-archive/pull/15) supplies an independent current-main contract, `core/swarmhub_contracts.py` blob `70dc375cb7d6ed931b40c3b2b82642d5312cdcb3`.

**Local check:** `python -m unittest discover -s tests -p 'test_contract_crosswalk.py' -v`. All fixtures are synthetic; no protected Play/Social/Imagine/Brain/Palace bodies. This is not peer or human-root ratification.

**Next real integration gate:** choose an editioned canonical wire shape; prove source-root and receipt identity at the current host; review directionality and lifecycle semantics; define a reversible, no-content-leak crosswalk with negative tests; rerun entire merged-main suite and CI before changing hosted service or closing master issue #4. Keep #14/#17 historical originals and objections intact.