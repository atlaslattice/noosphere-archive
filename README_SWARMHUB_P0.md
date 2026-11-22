# SwarmHub P0 Reference Core v0.1 — Review Candidate

Clean-room, standard-library Python, source-only, no credentials or public/private source imports. Targets: [noosphere-archive #5](https://github.com/atlaslattice/noosphere-archive/issues/5), [#6](https://github.com/atlaslattice/noosphere-archive/issues/6), [#7](https://github.com/atlaslattice/noosphere-archive/issues/7), [#8](https://github.com/atlaslattice/noosphere-archive/issues/8), [#9](https://github.com/atlaslattice/noosphere-archive/issues/9), and [#13](https://github.com/atlaslattice/noosphere-archive/issues/13).

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
PYTHONPATH=. python -m core.demo
```

**Scope:** no deployment, no distributed data store, no real credentials/rights, no signed host identity, no live API, no CANON ratification, no issue closure, no external app callbacks or code execution. It demonstrates fail-closed contracts in memory using synthetic inputs. Source references are metadata until independently verified.

**Live concurrent peer work:** [PR #14](https://github.com/atlaslattice/noosphere-archive/pull/14) separately proposes #11 and #12 lifecycle/evidence graph code. This patch deliberately DOES NOT implement those files, change them, or claim to supersede #14. Reconcile before merging any branch that overlaps.

- `core/coordinate_resolver.py`: exact HSN syntax (1,728 coords), H00.S00.N00 out-of-band Earth route, digest/edition hold.
- `core/sentinel.py` and `core/orchestrator.py`: independent review; no model or route can approve deployment or private-to-Work transfer.
- `core/preservation.py`: INV-0 append-only LOCAL in-memory state snapshots, all destructive requests quarantined.
- `core/ingestion.py`: explicit raw export status and source manifest; no false completeness.
- `core/canon_queue.py`: candidate queue with no automatic promotion; Aetherforge template.
- `core/rhythm.py`: 1/3 Work as transparent pure scheduling example, zero actual model invocations.

**Important difference:** local tests prove code-level behavior only, not durable database integrity, host authorization, permission-revocation correctness, complete Ariadne ontology, or successful public publisher release. All issue tickets remain open until code is merged, independently checked and integrated. Preserve original repo/main and history.
