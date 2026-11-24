# Atlas BEAST20 — integrated build and measured results

**Delivery date: November 23, 2026, Pacific/Honolulu.**

**Status: implemented and locally verified; source publication candidate.** Twenty cooperating capabilities connect source storage, scoped reuse, multilingual retrieval, restartable execution, public-source refresh, verified functional memory and the existing GF8 reasoning filter. The complete feature-to-code-to-test mapping is in [BEAST20_FEATURE_LEDGER.json](BEAST20_FEATURE_LEDGER.json); usage and architecture are in [README_BEAST20.md](../README_BEAST20.md).

## What was integrated

The implementation preserves current main `288b713290438853f50dd1e085432be3b06c0d0d`, the R11/GF8 claim-integrity branch at `6ea414d8d353f614a39f61a50b0787a61eb65227` (PR #41), and R10's checkpoint-bound memory retrieval at `fba6086b434bd7a20e4ba59fceff8858db3040e5` (PR #38). Their predecessor source and commit history remain present. The original project CANON and independent HSN/GF7 namespaces are preserved.

The source corpus was recovered separately and checked against its original hashes:

- Ariadne v0.7: `07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6` — 1,728 nodes, 144 Spheres and 12 Houses.
- Historical OpenAlex crosswalk: `a306c7306a79754b033e9f8c41c0de5ff5176b4544a6a80b5c740e2f8d2cc903` — 4,516 topics and 22,580 candidate edges.

Original source bodies are not included in the public code or benchmark reports. The OpenAlex mappings retain their historical, unreviewed status.

## Verification

**395 distinct Python tests and 22 Node tests passed.** The Python total includes **118 new BEAST20 cases**. Those 118 cases also passed under `python -O`; that repeat is reported separately and does not increase the distinct-test count. The executable CLI demonstration completed 12 coordinate contexts with one physical computation and 11 reuses.

Independent review supplied 31 of the new cases. It reproduced and verified corrections for lost source reversions, discarded HTML/XHTML content, altered archived payloads, shortened provider backoff, a concurrent origin-budget race, forged cache results, mutable scope identity, and interrupted feed-to-index delivery.

Evidence: [LOCAL_VERIFICATION.json](../benchmarks/LOCAL_VERIFICATION.json).

## Final local measurements

Each row below uses **nine alternating paired runs**, with identical compared output digests. Import/start/end source manifests matched. The environment was Python 3.12.14 and SQLite 3.53.1. Medians and p95 values, raw pairs, source hashes and each workload's limitations are retained in the machine-readable report.

| Workload | Baseline median | BEAST20 median | Baseline / BEAST20 |
| --- | ---: | ---: | ---: |
| R10 optimized memory projection → checkpointed batch projection | 84.055 ms | 94.513 ms | 0.889× |
| GF8 repeated contexts → first-batch physics reuse | 13.138 ms | 4.964 ms | 2.647× |
| GF8 repeated contexts → warm physics reuse | 13.297 ms | 3.859 ms | 3.445× |
| Individual verified object reads → bulk reads | 19.164 ms | 5.971 ms | 3.210× |
| Pretokenized in-memory scan → persistent search | 5.622 ms | 4.585 ms | 1.226× |
| Complete cascade rebuild → unchanged-result reuse | 316.977 ms | 178.816 ms | 1.773× |
| Full rebuild after one input change → incremental execution | 298.690 ms | 185.497 ms | 1.610× |

The integrated memory projection is **12.4% slower in median time** than the already optimized R10 comparator on this workload. It performs a second memory verification at return and five bulk topic queries instead of 1,728 per-coordinate queries. The lower SQL query count did not ensure lower wall time. This is an explicit retained regression; the original R10 API remains available.

Persistent search initially regressed to 28.048 ms against a 7.161 ms in-memory baseline. Investigation found that SQLite had selected the document-oriented index and scanned all postings for each query. The final implementation directs term lookups to the existing covering primary index and retrieves winning source rows in a bounded join. The final table contains a new paired measurement; the initial report remains unchanged.

These are descriptive local measurements, not universal performance or statistical-significance claims. Small gains need testing on the intended hosted workload. Component ratios are not multiplied.

Evidence: [final paired results](../benchmarks/BEAST20_REAL_SOURCE_RESULTS.json), [unchanged initial results](../benchmarks/BEAST20_REAL_SOURCE_RESULTS_INITIAL.json), [reproduction and measurement method](../benchmarks/README.md).

## Cascading reuse that actually executed

The compiled graph contains **1,885 jobs**: 1,728 node computations, 144 Sphere reductions, 12 House reductions and META145. Every unchanged rerun executed zero handlers and reused 1,885 results. Each changed supplemental node input executed exactly four handlers and reused 1,881 results. The original source ontology was not edited to manufacture this test.

That is a 99.8% reduction in handler executions for the one-input-change case, with a measured **1.610× wall-time improvement** because graph admission, validation, digest checks and database work remain. Closing and reopening the persistent task database reused all 1,885 successful results with exact output parity. These are lexical/digest computations, not simulated expert conversations or model calls.

## Real public-source operation

The opt-in HTTPS adapter was exercised against `https://github.com/python/cpython/releases.atom`. It received ten entries, then a real HTTP 304 response. Two network requests produced one parsing pass; no release content was copied into the public receipt. The timing of those two requests is a smoke observation, not a network-speed benchmark.

The feed/index bridge uses a durable delivery log and a separate acknowledgment cursor for each destination. If indexing or invalidation fails after the feed checkpoint commits, a later call can replay the pending change even when the provider returns 304, the response is still fresh, or the origin is locally rate limited. Tests verify restart, a new destination, ordered acknowledgments and A→B→A reversions. Bounded pages expose remaining work explicitly.

Evidence: [LIVE_PUBLIC_FEED_SMOKE.json](../benchmarks/LIVE_PUBLIC_FEED_SMOKE.json) and `tests_beast20/test_feed_delivery.py`.

## Open-source engineering

The build directly uses CPython's `graphlib`, `asyncio` and other standard-library modules, plus SQLite. Small original implementations adapt documented content-addressing, LRU/TTL, rank-fusion, conditional-fetch and dependency-invalidation patterns from the open-source ecosystem. No Git, Lucene, Scrapy, cachetools, NetworkX or DuckDB source code was silently transplanted or relicensed. The source/license ledger identifies what was studied, imported, implemented independently or left as a future option.

See [BEAST20_OPEN_SOURCE_PROVENANCE.md](BEAST20_OPEN_SOURCE_PROVENANCE.md).

## Operational boundary

The code, local CLI, tests and opt-in public-feed transport work in the measured environment. A scope key isolates data but does not grant permission. Actual hosts must supply current READ/RETURN authorization; local test callbacks do not prove hosted revocation. GF8 cached results are trusted only after computation in the current process or an independently trusted future checkpoint, so a self-consistent replacement cache cannot manufacture numerical results or authority.

No production SwarmChat publisher was changed by this package. No background agent service, autonomous resident, model-weight training, physical cymatic processor, paid provider call or new recurring automation is claimed. The source integration and CI definition are concrete; hosted mounting and hosted authorization/latency validation remain separate work.
