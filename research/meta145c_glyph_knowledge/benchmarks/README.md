# BEAST20 local benchmark protocol

Run from `research/meta145c_glyph_knowledge` with Python 3.10 or newer. Only the
standard library is required. The runner makes no network requests or model
calls and uses no artificial delays in performance measurements.

## Reproduce the public synthetic fixture

```bash
python3 benchmarks/bench_beast20.py \
  --repeats 5 \
  --output benchmarks/BEAST20_SYNTHETIC_RESULTS.json
```

The generated fixture has 1,728 nodes, 144 Spheres and 12 Houses. Its labels,
topics and review events are synthetic. Actual code executes over these inputs;
the rows are not expert participants, model turns or scientific discoveries.

## Reproduce the original source workload

Supply the authorized original source files; source bodies are deliberately
excluded from this repository's benchmark report.

```bash
python3 benchmarks/bench_beast20.py \
  --registry /path/to/ariadne-atlas-v07.json \
  --topics /path/to/openalex_to_ariadne_ALL_4516.csv \
  --repeats 5 \
  --output benchmarks/BEAST20_REAL_SOURCE_RESULTS.json
```

The original loader requires these exact SHA-256 identities:

| Input | Required SHA-256 |
| --- | --- |
| Ariadne v0.7 registry | `07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6` |
| Historical 4,516-topic crosswalk | `a306c7306a79754b033e9f8c41c0de5ff5176b4544a6a80b5c740e2f8d2cc903` |

The crosswalk contains 22,580 historical candidate placements. Running it does
not accept those candidates as semantic equivalences. The 144 review events
remain explicitly synthetic even when the registry and topic inputs are real.

## Comparisons and their guarantees

| Comparison | Baseline | Candidate |
| --- | --- | --- |
| Legacy memory | Existing per-topic full memory scan | R10 checkpoint-verified batch, retaining per-coordinate topic SQL |
| Current memory | Optimized R10 verified batch | Integrated batch topic projection, with a second checkpoint check before return |
| GF8 cold batch | 24 independent analytic contexts | One fresh store/runtime and reuse across 24 typed contexts with identical physics |
| GF8 warm batch | 24 independent analytic contexts | A prepopulated physics cache; each context is rebuilt and checked |
| Source objects | Individual exact-byte object reads | Bounded batched exact-byte reads, retaining SHA-256 checks |
| Source-name retrieval | Pretokenized in-memory set intersections | Persistent inverted-index retrieval, including source-byte verification |
| Whole cascade | Fresh checkpoint DB and 1,885 concrete jobs | Unchanged-input reuse of completed jobs |
| Incremental cascade | Full rebuild for the changed input | One new supplemental input, requiring its node, Sphere, House and META145 reductions |

The retrieval baseline is intentionally competitive. An in-memory scan may
beat a persistent index on a small dataset. Likewise, fewer SQL queries do not
guarantee lower wall time when the new path performs additional integrity
checks. Negative measurements are retained rather than discarded.

Every timed pair compares output digests. GF8 compares the complete existing
reasoning packets; memory compares complete existing topic-view projections;
retrieval compares ordered IDs and scores; cascades compare every job output.
Digest calculation for benchmark parity occurs outside the measured interval.

The cascade performs lexical and digest reductions. Its synchronous handlers
do not acquire multicore parallelism through `asyncio`. Cold task construction,
scheduling, validation and checkpoint costs remain in its measured interval.
Each incremental pair uses a never-before-seen supplemental revision, leaving
the original source registry unchanged. The expected execution counts are
1,885 for a fresh build, zero for unchanged reuse, and four for that one-node
supplement. A separate SQLite restart observation verifies zero re-execution;
it is not presented as a paired latency ratio.

## Sampling and source binding

The runner alternates baseline-first and candidate-first ordering. It retains
every measured time, the median, minimum, maximum and nearest-rank p95. With
five pairs, p95 is the largest observation; these are descriptive local
measurements, not broad statistical confidence or hosted service benchmarks.
Ratios use baseline median divided by candidate median. Ratios from different
layers must never be multiplied.

The runner captures relevant Python source hashes before imports, at the start
of measurement and at the end. A change during measurement aborts saving. The
initial development report predates this manifest capture and is identified
explicitly when retained in a merged report.

After a focused code change, rerun only affected comparisons:

```bash
python3 benchmarks/bench_beast20.py \
  --registry /path/to/ariadne-atlas-v07.json \
  --topics /path/to/openalex_to_ariadne_ALL_4516.csv \
  --sections memory-current physics storage cascade \
  --merge-from benchmarks/BEAST20_REAL_SOURCE_RESULTS_INITIAL.json \
  --repeats 5 \
  --output benchmarks/BEAST20_REAL_SOURCE_RESULTS.json
```

`memory-current` skips the slow historical scan comparison. The merge retains
unrerun scenarios under their original measurement pass and replaces only the
named scenarios measured again. The original report's filename and exact hash
are recorded, so improvements do not erase preceding regressions.

The local authorization callback used by the benchmark is a test seam. No
result demonstrates live host authentication, revocation, semantic truth,
model-quality improvement, physical acoustic acceleration or universal
superiority over other systems.
