# BEAST20 — integrated Atlas computation and public-source refresh

**Status: LOCAL_TESTED.** This package implements twenty cooperating features on
the existing Ariadne, R10 functional-memory and GF8 reasoning-filter source.
It preserves the original source editions and CANON history. The implementation
is runnable locally; this package is not a hosted deployment or a standalone
population of autonomous residents.

The practical aim is to avoid repeating work whose inputs have not changed,
recompute the affected dependencies when they have, and retain enough evidence
to tell those cases apart. The implementation uses original Python code and the
standard library. [Open-source provenance](docs/BEAST20_OPEN_SOURCE_PROVENANCE.md)
records the upstream patterns and licenses reviewed; it does not claim that
third-party implementation code was copied or that the referenced packages are
installed dependencies.

## The twenty implemented features

The machine-readable [feature ledger](docs/BEAST20_FEATURE_LEDGER.json) maps each
feature to its actual symbols, focused tests, cooperating features and limits.

| ID | Feature | Implemented behavior |
| --- | --- | --- |
| E01 | Exact-byte content store | Scope-separated SQLite objects addressed by SHA-256; verify each returned body. |
| E02 | Source and execution identity | Memo keys include source digest, edition, principal, rights epoch, algorithm version, configuration and inputs. |
| E03 | Bounded positive and negative memo | TTL/LRU cache with an explicit negative-result sentinel, fresh decoded return values and finite JSON validation. |
| E04 | Batched object retrieval | Bounded SQL chunks preserve request order, duplicates and missing results while verifying bytes. |
| E05 | Dependency invalidation | Reverse dependency traversal removes affected derived memo entries; cycles terminate and raw evidence remains. |
| E06 | Incremental multilingual retrieval | Unicode/CJK posting lists, no-op detection and reciprocal-rank fusion preserve distinct evidence polarities. |
| E07 | Duplicate in-flight work sharing | Equivalent concurrent jobs share one computation; cancellation of one waiter does not cancel another's work. |
| E08 | Dependency-aware execution | Validate the complete DAG before invocation, run ready tasks and block descendants of failed prerequisites. |
| E09 | Fair bounded admission | Rotate ready Houses and bound workers, graph size and concurrent graph admission. |
| E10 | Durable task resume | Persist results, hashes, attempt state and ownership leases; reuse completed jobs after reopening state. |
| E11 | Bounded retry and dead letters | Retry within the task budget, preserve observed failures across interruption, and retain terminal failure receipts. |
| E12 | Provider circuit breakers | Isolate provider failures, defer while open and admit one half-open recovery probe. |
| E13 | Conditional public-source refresh | ETag/Last-Modified validation, unchanged-body detection and supported cache-policy handling avoid redundant requests or parsing. |
| E14 | Revision history and visible reverts | Preserve item revisions, deduplicate identical logical content and emit a changed head when content returns to an older revision. |
| E15 | Transactional origin budgets | Shared per-origin token buckets and persisted provider backoff coordinate poller instances. |
| E16 | Recoverable feed delivery | Atomically checkpoint fetched changes; durable pending/ack cursors replay incomplete delivery into an index. |
| E17 | Verified memory and batched topic views | Use R10's expected checkpoint, preserve existing ranking arithmetic and recheck memory before returning projected topic views. |
| E18 | Reusable GF8 physical computation | Reuse identical physical inputs across separately typed HSN contexts, with trusted in-process result digests and unchanged packet semantics. |
| E19 | Incremental complete Atlas cascade | Execute 1,728 node jobs, 144 Sphere reductions, 12 House reductions and one META145 reduction with dependency-based reuse. |
| E20 | Bounded measurement and regression evidence | Record fixed stage timings/counters and reproduce paired comparisons with exact output checks, including negative results. |

## How the features cooperate

A selected public feed enters through conditional refresh and the shared origin
budget. New revisions become ordered durable delivery events. The runtime writes
each delivered item into the source store and multilingual index, invalidates
dependent memo entries, and acknowledges only after those operations complete.
If indexing or invalidation fails, a later call can finish the same delivery even
when the provider now returns `304`, fresh-cache or rate-limit status.

The computation path uses exact source/configuration identities to combine
singleflight, persistent task reuse and dependency scheduling. In the full Atlas
circuit, a changed supplemental input for one node affects that node, its Sphere,
its House and the final reduction. Unrelated completed tasks remain reusable.
Changing the source edition or the relevant algorithm identity changes the reuse
scope. The circuit performs lexical/digest computations; its jobs are not model
calls, independent expert judgments or newly authenticated residents.

GF8 reuse depends on the plate model, material, geometry, damping, drive,
resolution, modal truncation and implementation bytes. An HSN or glyph address
does not substitute for any of those physical inputs. The runtime creates the
coordinate-specific context and receipt after retrieving the shared physical
result. A bounded result-digest map in the process prevents an editable SQLite
cache from silently supplying a new validly self-hashed physical result. A new
runtime recomputes a configuration before trusting its persistent cached value.

## Run locally

Use Python 3.11 or later with its standard library. Run these commands from this
package directory, `research/meta145c_glyph_knowledge`. State directories are
explicit and remain local. The CLI's authorization callbacks represent the local
operator invocation; they do not demonstrate hosted account authentication.

### Local memory and physical-reuse demo

```bash
python -m src.beast20 demo
```

This exercises the verified-memory API and reuses one physical configuration
across coordinate-specific contexts. It makes no network requests or model calls.

### Complete pinned-source cascade

Supply the authorized original Ariadne file. The historical OpenAlex crosswalk
is optional; if supplied, its exact expected digest is checked too.

```bash
python -m src.beast20 cascade \
  --registry /path/to/ariadne-atlas-v07.json \
  --topics /path/to/openalex_to_ariadne_ALL_4516.csv \
  --state /tmp/atlas-beast20-cascade
```

Repeat the same command with the same state directory to exercise durable reuse.
For a changed-input run, supply `--node-inputs /path/to/node-inputs.json`. That file
maps existing full HSN addresses to JSON supplemental computation inputs, for
example `{"H01.S01.N01":{"review_revision":1}}`. It does not rewrite the original
registry or accept a scientific claim. The runtime rejects unknown coordinates.

### One explicit public-feed refresh

```bash
python -m src.beast20 feed \
  --url https://github.com/python/cpython/releases.atom \
  --host github.com \
  --state /tmp/atlas-beast20-public-feed \
  --allow-network \
  --query Python
```

The transport uses the selected HTTPS host, bounded response size and timeout.
This command runs once; it does not install a scheduler. Supported feed inputs
include Atom, RSS and JSON Feed. Original HTML is retained as inert source data;
this module does not execute or render it. Feed contents enter the index as
`PUBLIC_SOURCE_UNREVIEWED`, regardless of any authority language in the feed.

### Tests and reproducible benchmarks

```bash
python -m unittest discover -s tests_beast20 -p 'test_*.py' -v
python -O -m unittest discover -s tests_beast20 -p 'test_*.py' -v
python -m unittest discover -s tests_public -p 'test*.py' -v
python -m unittest discover -s tests -p 'test*.py' -v
python benchmarks/bench_beast20.py --repeats 5 --output /tmp/beast20-synthetic.json
python benchmarks/bench_beast20.py \
  --registry /path/to/ariadne-atlas-v07.json \
  --topics /path/to/openalex_to_ariadne_ALL_4516.csv \
  --repeats 5 --output /tmp/beast20-real-source.json
```

The default benchmark generates an explicitly synthetic topology. The second
benchmark uses exact pinned original sources, keeping their text out of the
result report. Both compare actual output digests and preserve paired timings;
there are no artificial sleeps or imaginary agents in the measured workloads.

## Read the evidence, including the regressions

- [Local verification](benchmarks/LOCAL_VERIFICATION.json) records the executed
  test commands and source hashes.
- [Final source benchmark](benchmarks/BEAST20_REAL_SOURCE_RESULTS.json) records
  workload definitions, paired raw times, counters, parity and limitations.
- [Initial source benchmark](benchmarks/BEAST20_REAL_SOURCE_RESULTS_INITIAL.json)
  retains the initial unfavorable results rather than replacing their history.
- [Live public-feed smoke observation](benchmarks/LIVE_PUBLIC_FEED_SMOKE.json)
  records the bounded provider exercise; it is separate from local CPU timings.

The R10 comparison uses the already optimized checkpoint-bound memory API as a
baseline, not only the older repeated scans. The integrated topic-view wrapper
also checks the checkpoint again before returning and applies current-read and
current-return callbacks. On this workload that additional work can outweigh the
savings from batching topic queries. Retain that regression and its different
correctness contract; do not describe it as a universal memory acceleration.

The initial persistent search was slower than the competitive pretokenized
in-memory scan. Investigation found that SQLite chose the document-oriented
index for grouping and scanned all postings in the scope. The repaired query
uses the declared covering term index and hydrates only the ranked results in a
bounded join. Every returned source body is still SHA-256 verified. The final
benchmark measures the repaired query against the same baseline; the initial
result remains available above.

Component ratios must not be multiplied. Cold setup, broad queries, cache misses,
full source changes, checkpoint verification and bookkeeping all have costs.
Async overlap does not provide CPU multicore execution for synchronous Python
handlers. Task timeouts require cooperative async work; a blocking synchronous
handler can block its event loop.

## Source lineage

| Source | Exact identity |
| --- | --- |
| Current-main starting point | `288b713290438853f50dd1e085432be3b06c0d0d` |
| R10 checkpoint-bound memory, inherited PR #38 | `fba6086b434bd7a20e4ba59fceff8858db3040e5` |
| R11/GF8 integrity fixes, inherited PR #41 | `6ea414d8d353f614a39f61a50b0787a61eb65227` |
| Ariadne original v0.7 SHA-256 | `07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6` |
| Historical OpenAlex crosswalk SHA-256 | `a306c7306a79754b033e9f8c41c0de5ff5176b4544a6a80b5c740e2f8d2cc903` |

The source branches were combined without rewriting their original commits.
The crosswalk remains historical candidate placement, not a fresh OpenAlex API
verification or accepted semantic equivalence. Earlier CANON editions and the
independent physical, glyph and HSN namespaces remain intact.

## Operating boundary

`Scope` separates source editions, principals and rights epochs; it does not
authenticate them. Runtime integrations must provide real current-rights
callbacks at READ and RETURN. Hashes detect disagreement with the supplied
expected bytes or checkpoint; a hash stored alongside editable local data is not
an independent signature or authority service. Protected Play, Imagine, Brain,
Palace, Social and Quiet content is not an automatic Work input.

The memo cache bounds entries and caps each payload; raw source history has a
separate retention purpose. SQLite may retain reusable free pages after rows
expire. Feed conditional handling supports the documented behaviors in its
tests and does not claim a complete general-purpose RFC HTTP cache.

Handlers are explicitly registered application callables. This package does not
add paid provider credentials, remove spending or authorization controls, spawn
models on its own, alter model weights, publish to CANON, or deploy itself. A
host integration must supply its actual transport, identities, rights and
deployment mechanism before any hosted capability can be called verified.
