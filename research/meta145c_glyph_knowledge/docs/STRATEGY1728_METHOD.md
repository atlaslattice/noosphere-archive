# BEAST20 Strategy1728 — simulation, selection, and measured replay

This module performs a finite **1,728-configuration search** over three existing
BEAST20 controls. It retains simulated forecasts separately from actual replay
measurements. A selected configuration is an optimum of the declared training
objective within this discrete candidate set, not a proof of a global or hosted
optimum.

## The three axes

| Axis | Twelve candidate values | Actual integration point |
| --- | --- | --- |
| Workers | 1–12 | `AsyncExecutor(workers=...)` |
| Memo capacity | 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048 | `ArtifactStore(max_memo_entries=...)` |
| Object-read chunk width | 1, 2, 4, 8, 16, 32, 64, 96, 128, 192, 256, 400 | `ArtifactStore.batch_get(chunk_size=...)` |

Candidate slots use the H/S/N address shape to provide 144 groups of 12
candidates and 12 parent groups, ending in one META145 selection. These are
configuration groupings. They do not replace Ariadne's semantic coordinates,
reassign deities or elements, or imply that a House's knowledge domain is a
worker count.

## Trace and computation model

The runner invokes the existing `CascadeCompiler` handlers against an original
verified `SourceSnapshot`, or an explicitly synthetic topology if no registry is
supplied. It records three service-time samples per actual node/reduction
handler and retains the median. The traces contain task IDs, dependencies,
source/configuration cache identities, output hashes, output sizes and timing
values. Original source names and bodies are not copied into the trace.

SQLite memo reads, writes, individual object chunks and batches are measured
locally nine times. A nonnegative linear fit provides a batch fixed-cost and
per-item estimate. The batch objects are coordinate/record-digest metadata,
not complete private source documents. Handler timings use a monotonic
performance counter; they estimate serial service cost rather than measuring
OS CPU time in isolation.

The discrete-event scheduler has one serialized CPU service lane. Only an
explicit nonzero async wait in a supplied trace may overlap. The measured
lexical/reduction trace has **no inserted async wait**. Increasing worker count
therefore does not manufacture CPU parallelism. Equivalent in-flight keys can
share work, and a bounded LRU memo is updated on completion. Ready Houses rotate
fairly. Memo state resets between training and holdout and persists between
scenarios within each split.

The model assumes no TTL expiry during a split. It excludes provider failures
and most executor bookkeeping overhead. It is deliberately not a complete
prediction of hosted latency. Reports state the trace measurement kind and
retain that a caller-supplied checksum is not an independent attestation.

## Selection and holdout

Training scenarios comprise a cold graph, an unchanged repeat, and a change to
one supplemental node input. Holdout uses a cold graph, an unchanged repeat,
and a supplemental change to a different node. The original ontology remains
unchanged. This is a workload holdout, not independent external source data.

The default objective weights predicted latency, serialized service cost,
reserved memo capacity and workers. Weights and resource constraints are
explicit report fields. Deterministic ties prefer fewer workers, then smaller
memo capacity, then smaller chunk width, then stable candidate ID. A Pareto
frontier reports nondominated training latency/cache-reservation/worker choices.

Holdout values do not choose or prune candidates, determine objective weights,
or construct the Pareto frontier. The selected configuration's holdout result
is reported separately, including a predicted regression or a holdout resource
limit violation. No feasible strategy is an explicit outcome.

Replay-equivalent scheduler states are computed once, while all 1,728 distinct
configurations receive their own metrics and objective. For synchronous traces,
the worker axis shares an identical serial schedule. The report exposes the
number of unique scheduler replays rather than claiming 1,728 physical runs.

## Actual paired replay

After selection, the runner runs the baseline and chosen configuration through
the actual `ArtifactStore` and `AsyncExecutor`. Each run retrieves metadata
objects in configured chunks, runs the cold/warm/changed graphs, checks each
graph completes, and compares output digests. Fresh temporary state starts each
baseline or candidate run. Pair order alternates to reduce simple order bias.

Executor receipt versions deliberately change between scenarios so durable
executor reuse cannot conceal the memo-capacity axis. Memo keys remain stable
for unchanged semantic computations. This isolates a useful composite workload;
it is **not** a claim that the ordinary unchanged-cascade path lost its existing
durable reuse. Setup and initial object population are outside timing; task
construction, verified batch reads, memo operations, scheduler work, and output
digesting are inside it. Both sides use the same contract.

`STRATEGY1728_MEASURED_REPLAY.json` retains raw pairs, exact output comparisons,
actual median timing and the measured ratio. Its measured ratio is separate from
the strategy report's simulated holdout ratio. An unfavorable measured result
is retained and does not retroactively change the selected candidate.

## Reproduce

From `research/meta145c_glyph_knowledge`:

```sh
python3 benchmarks/bench_strategy1728.py \
  --registry /path/to/ariadne-atlas-v07.json \
  --topics /path/to/openalex_to_ariadne_ALL_4516.csv \
  --repeats 9 \
  --output-dir benchmarks/strategy1728
```

Omit `--registry` and `--topics` for an explicitly synthetic topology. No network
request, model call, resident turn, credential access, or source publication is
performed by this command.

The runner emits a full trace, all 1,728 candidate rows, a compact native-host
summary, and the independently measured replay. Each report carries source and
implementation identities. The full candidate report and compact summary have
separate checksums; the compact summary retains the full report's checksum.

## Programmatic use

```python
from src.beast20.strategy_lab import StrategyLab, compact_summary

report = StrategyLab(source_digest, edition).evaluate(
    trace_envelope,
    expected_trace_sha256=independently_expected_trace_digest,
    constraints={"max_workers": 4, "max_memo_entries": 2048},
)
native_host_view = compact_summary(report)
```

This pure local API does not invoke a model provider or authenticate a host.
Applications must retain their actual READ/RETURN authorization and source
scope checks around any private trace or result.
