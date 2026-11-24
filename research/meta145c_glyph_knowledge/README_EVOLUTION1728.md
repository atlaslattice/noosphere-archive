# Native1728 Evolution — repeated source-bound experiments and measured code upgrades

This release extends Native1728 with an executable long-horizon workload model,
source-node attribution, a training-only META145 incumbent, native report views,
and two measured BEAST20 storage optimizations.

## What the requested repetition means

The completed experiment uses **one initial batch plus 1,728 repeats**:

| Quantity | Recorded scope |
| --- | ---: |
| Batches / epochs | 1,729 |
| Configuration timelines per batch | 1,728 |
| Synthetic years per timeline | 1,728 |
| Main timeline-year transitions | 5,162,766,336 |
| Additional source-attribution audit transitions | 5,975,424 |
| Training / holdout batches | 1,297 / 432 |
| Source nodes / Spheres / Houses | 1,728 / 144 / 12 |

A **synthetic year is one request/cache/admission state transition**. It is not
a calendar forecast, a full execution of the Atlas graph, a model inference,
an independently completed resident Macroturn, or a new source-code patch.
The C++ engine executes every main transition and sums its observed request
counters. The requested product is then checked against that observed count.
Two extra audit timelines per epoch attribute baseline and selected metrics to
the original node references; their transitions are counted separately.

Epochs reset their workload/cache state. Cumulative training evidence changes
the incumbent; there is no invented continuous civilization or agent state.
The 12 workload regimes include bounded hotsets, full-source scans, burst reuse,
local and global revision churn, scarce and abundant service, unavailable sources,
and frequent source rechecks. All configurations see identical seeded events
within an epoch. Assumptions remain in every complete report.

The fixed grid contains 1,728 configurations, but the twelve worker settings
have equivalent schedules in this synchronous model. It therefore represents
144 distinct modeled cache/chunk behaviors. Every configuration is still
executed directly; no shared-state shortcut substitutes for its transitions.
The recorded compiled-engine run took 25.149 seconds. The repetition evaluates
the fixed grid; it does not generate 1,729 new algorithms.

## Result and synthesis

The final selected configuration is the current build's baseline:
**one worker, 2,048 memo entries, and a 400-record batch width**
(`CFG.W01.M12.B12`). The incumbent is established or changes four times as
training evidence accumulates. Retaining the existing configuration is robustness
evidence; the experiment does not manufacture another simulated performance gain.

The selection objective is lexicographic: zero freshness violations first,
then broader fresh source-node coverage, more fresh completions, fewer held
requests, lower predicted service cost, and deterministic resource tie breaks.
Every fourth 12-epoch block is holdout and cannot select or change the incumbent.
Unavailable-source and insufficient-budget requests remain held.

All 1,728 source nodes have fresh completions under the selected modeled policy.
The node → Sphere → House sums agree with the selected and baseline audit totals.
The model records zero freshness violations. Freshness here verifies the declared
revision/invalidation model; it does not establish the semantic quality of model
answers, because this experiment generates no model answers.

The eight synthesis hypotheses concern memo capacity, verified batch reads,
synchronous worker settings, revision invalidation, unavailable-source gates,
quality-first admission, workload-specific benchmarking, and validation overhead.
Each retains its proposed status and required checks. Actual implementation and
measurement are recorded separately below.

## Code actually changed

### 1. Bounded reuse of validated scope identities

`src/beast20/storage.py` caches a scope digest in a 256-entry cache keyed by all
five validated scalar fields: source digest, edition, principal, rights epoch,
and mode. Current scalar values are validated on every access. A valid scope
mutation creates a different key; invalid values fail before cache hashing.
This caches digest computation, not authorization or payload-integrity checks.

### 2. Indexed memo-expiry cleanup

The storage constructor creates `beast_memo_expiry(expires)` for new and existing
databases. Expiry cleanup uses an indexed search. The exact row-count query,
durable LRU counter, transactions, TTL boundary and content digest checks remain.

### Actual old/new comparison

The primary comparison uses the same **one-worker / 2,048-entry / 400-chunk**
configuration in both source versions. Each lane runs in a separate process with
the original pinned Ariadne source, verified metadata reads and the existing
cold/warm/changed DAG replay.

| Metric | Previous source | Upgraded source |
| --- | ---: | ---: |
| Median elapsed time, nine alternating pairs | 2,105.347816 ms | 1,854.883412 ms |
| Baseline / candidate ratio | — | 1.1350297287579603× |
| Median latency reduction | — | 11.896580797555023% |
| Equal output digests | — | 9/9 |
| Equal cache operation counts | — | 9/9 |

One individual full-cascade candidate pair was slower; the raw pair is retained.
This is a local workload result, not a hosted or universal speedup. It is not
multiplied by the previous Native1728 experiment's ratio.

A separate storage-facing benchmark runs six workloads with nine alternating
pairs each. The cold/warm/changed synthetic handler/storage workloads improved
by median ratios of approximately 1.137×, 1.068× and 1.713× at capacities 8, 256,
and 2,048. That benchmark uses memory SQLite and excludes AsyncExecutor, so it
does not substitute for the full-cascade result. Small differences in unchanged
batch-read control workloads are retained without a general batching-gain claim.

## Native interfaces

SwarmChat extends the existing owner-scoped integration interface with:

- `swarm_native1728_evolution_status`: separate simulation identity, counters,
  META145 selection, source checks and the independently measured code change.
- `swarm_native1728_evolution_page`: bounded pages for `house`, `sphere`, `node`,
  `candidate`, `epoch`, and `synthesis`. Hierarchy views accept an exact `hsn`
  subtree such as `H05`, `H05.S05`, or `H05.S05.N01`.

The page is `/work/integration/evolution`. The existing native composer can use
the two registered read operations. It retains the same owner and leaf-tool
authorization, input/output budgets, dependency checks and failure propagation.

The host verifies exact report bytes, source-record membership, metric
conservation, hierarchy sums and the training selection. A frozen bundle can be
validated once and reused; mutable wrappers are revalidated. Returned pages are
copies and cannot mutate the cached report. A report checksum is integrity
evidence, not independent proof that the simulation ran.

Atlas ONE's existing integration status and page receive a compact projection of
the same verified report and actual implementation measurements. Its GrokSeek
compiler and D1 queue boundary remain in place. This release adds no model
provider, cross-host execution credential, background schedule or resident turn.

The preceding Native1728 live-verification gap is closed: the authenticated
production `swarm_native1728_demo` completed all twelve actual tool steps. The
receipt is `benchmarks/native1728_evolution/SWARM_LIVE_COMPOSITION.json`.

## Evidence files

All paths below are under `benchmarks/native1728_evolution/`.

| File | Meaning |
| --- | --- |
| `LONG_HORIZON_REPORT.json.gz` | Complete lossless report: all candidates, node/Sphere/House totals, every epoch decision and hypotheses |
| `LONG_HORIZON_SUMMARY.json` | Compact inspection view; not a substitute for the complete report |
| `LONG_HORIZON_ENGINE_RAW.json.gz` | Raw compiled-engine counters, checksums and audit output |
| `LONG_HORIZON_BUNDLE.json.gz` | Exact-byte host wrapper with report SHA-256 |
| `LONG_HORIZON_MANIFEST.json` | Artifact hashes and implementation identities |
| `CURRENT_IMPLEMENTATION_TRACE.json.gz` | Fresh actual handler/SQLite calibration after the storage changes |
| `CURRENT_CALIBRATION_MANIFEST.json` | Calibration source hashes and exact compressed/decompressed identities |
| `CASCADE_UPGRADE_MEASURED.json` | Nine real old/new full-cascade pairs at identical settings |
| `STORAGE_UPGRADE_MEASURED.json` | Six storage workloads, all 54 raw pairs and integrity diagnostics |
| `SWARM_LIVE_COMPOSITION.json` | Authenticated production execution of the existing twelve-component demo |
| `IMPLEMENTATION_UPGRADE.json` | Actual storage changes, preserved invariants, measured results and hypothesis dispositions |
| `HOST_EXPORT_MANIFEST.json` | Exact generated companion module identities |
| `RELEASE_VERIFICATION.json` | Final local test counts, commands, source pins and production build evidence |
| `HOSTED_EVOLUTION_RELEASE.json` | Publication identities and direct production MCP verification |

The earlier `benchmarks/strategy1728/` artifacts remain immutable historical
evidence for source revision `2bea02211f93763bd753434676945c0f5bc7b8a7`. Their
storage implementation hash intentionally differs from this new release.

## Reproduce

Run from `research/meta145c_glyph_knowledge`. The direct engine requires local
`g++` with C++17 and OpenMP; Python uses the standard library. Obtain your
authorized original Ariadne registry independently. Original source bodies are
not included in the public experiment artifacts.

```sh
python3 benchmarks/bench_long_horizon.py \
  --registry /path/to/ariadne-atlas-v07.json \
  --trace benchmarks/native1728_evolution/CURRENT_IMPLEMENTATION_TRACE.json.gz \
  --trace-sha256 c20ce58e2ca932108092496d184f91d8f5ab636a0668b1246ce65fbfbfa7ee33 \
  --epochs 1729 --years 1728 --threads 4 \
  --output-dir /tmp/atlas-long-horizon-reproduction
```

Use a new output directory to retain the recorded experiment. Timings vary by
machine. State outcomes and checksums are deterministic for the pinned engine,
source references, seed, calibration and workload parameters.

Restore the complete report, then use the public package CLI:

```sh
gzip -dk benchmarks/native1728_evolution/LONG_HORIZON_REPORT.json.gz
python3 -m src.beast20 evolution-summary \
  --report benchmarks/native1728_evolution/LONG_HORIZON_REPORT.json
python3 -m src.beast20 evolution-bundle \
  --report benchmarks/native1728_evolution/LONG_HORIZON_REPORT.json \
  --output /tmp/atlas-long-horizon-bundle.json
```

Skip restoration if the complete JSON is already present. Verify its bytes
against `LONG_HORIZON_MANIFEST.json` before using it. No command here starts a
background worker, posts a room message, calls a model, or modifies canon.

## Published release and final verification

The extension was published on November 23, 2026 (Honolulu):

- **SwarmChat version 53**, source `59d70591e360a8923ed413f8d0744f1a78663f3d`:
  [Evolution evidence explorer](https://swarmchat-private-broker-20261112.tdavesheldon.chatgpt.site/work/integration/evolution).
  Two concurrent source advances were merged normally. Their interop and
  Civilization registrations remain alongside the new evolution read tools.
- **Atlas ONE version 14**, source `9a7bd89ca42ae5151c1fa04f5933adbedb866306`:
  [Native integration view](https://atlas-one-beta.tdavesheldon.chatgpt.site/integration/).
  A subsequent concurrent version 15 was observed with a successful deployment;
  a fresh native status call confirms it retains this exact report. This
  release's recorded build and tests apply to the version 14 source.

Both publications succeeded. Existing audiences remain unchanged: SwarmChat's
integration page/tools are owner-scoped; Atlas ONE remains owner-private.

| Final local gate | Passed | Optional skips |
| --- | ---: | ---: |
| Public Python source and regression contracts | 627 | 2 |
| SwarmChat complete 78-file host suite | 691 | 2 |
| Atlas ONE service, interop, evolution and registry suite | 393 | 0 |
| **Distinct total** | **1,711** | **4** |

The BEAST20 gate passed all 240 cases normally and under optimized Python;
repeated runs are not counted twice. Python 3.13.5 was exercised; Python 3.11
was not installed locally and remains a separate CI matrix entry. The optional
skips concern omitted historical/private test inputs. Both production builds
passed on stable source inputs.

Production verification used authenticated native tools. SwarmChat's four-step
evolution DAG completed with **three actual invocations and one deduplication**.
It bound the returned `H01` coordinate to a node page, found all 144 descendants,
returned the requested twelve rows and verified the complete report identity.
The existing twelve-component demo also completed all twelve actual invocations.
Atlas's native integration status returned the same report and actual replay
ratio. These checks made zero model calls or room posts and started no background
jobs. Registration of 78 eligible tools is not a claim that every tool executed.

The report shared by both hosts is pinned to:

```text
18cb16f53f2ee02fb3ae9ee599ea3bb8154b86dad83ac99cbb57af955eb3e1de
```

Source publication extends [PR 48](https://github.com/atlaslattice/noosphere-archive/pull/48).
Hosted publication, local tests and GitHub Actions remain separate checks; see
the PR's current CI status for the remote workflow result.
