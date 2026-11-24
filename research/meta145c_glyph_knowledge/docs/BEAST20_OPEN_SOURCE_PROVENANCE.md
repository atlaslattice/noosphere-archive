# BEAST20 open-source provenance and engineering references

Research date: **2026-11-23, Pacific/Honolulu**.

## Implementation boundary

BEAST20 uses original Python implementation code and Python's standard library.
The projects below supplied documented patterns and design comparisons. They are
not bundled runtime dependencies, and no third-party implementation source was
copied into `src/beast20` during this work. In particular, this work does not
include a Git, Lucene, Scrapy, NetworkX, cachetools, DiskCache, OpenTelemetry, or
DuckDB source transplant. Importing `sqlite3` uses the SQLite library already
provided by the Python runtime.

This distinction is intentional provenance, not a claim that rewriting copied
code removes its license. A future adaptation of actual upstream source must
record the exact repository revision and file, preserve applicable notices, and
describe the changes. The source versions below identify the documentation
reviewed; an unpinned documentation page is not a verified source commit.

At the time of the local environment check, `python3` reported **Python 3.12.14**,
**SQLite 3.53.1**, and `ENABLE_FTS5=1`. These are local environment observations,
not a statement about any hosted runtime. The current lexical implementation
uses explicit SQLite posting lists, including CJK characters and bigrams; FTS5
was reviewed as an alternative and is not required by that implementation.

## Source and license matrix

| Project or standard | Inspected revision | Pattern considered or implemented independently | Upstream license / source status |
| --- | --- | --- | --- |
| Git | *Pro Git*, second edition, Git Objects chapter; project COPYING inspected on research date | Immutable content addressing, deduplicated source bytes, versioned derivation identities | Git implementation is generally GPL-2.0-only unless a file states otherwise. No Git code or book text copied. General architectural analogy only. |
| SQLite | Official FTS5, copyright and WAL documentation; local runtime 3.53.1 | Indexed batches, transactional checkpoints, scoped memo records and inverted posting lists | Deliverable SQLite code and documentation are dedicated to the public domain. Its build scripts can have different licenses. |
| CPython | Python 3.13 documentation; local runtime 3.12.14 | Dependency-ready DAG scheduling, synchronization, bounded parallel work and cancellation | PSF License Version 2; documentation examples and recipes are also available under 0BSD beginning with Python 3.8.6. Runtime import, not a source copy. |
| cachetools | Documentation 7.3.0; current LICENSE inspected | Bounded LRU/TTL reuse and per-key in-flight coordination | MIT; Thomas Kemmer. Original local implementation; package not imported. |
| NetworkX | Documentation 3.7 | Reachability and descendant-only invalidation | BSD-3-Clause. Original local graph traversal; package not imported. |
| Apache Lucene | Core API 10.2.1, `TopDocs.rrf` | Reciprocal rank fusion across candidate rankings | Apache-2.0, with additional notices for some bundled files. Original rank calculation; no Lucene implementation copied. |
| Scrapy | AutoThrottle 2.13.4 and downloader middleware documentation | Conditional refresh, per-origin request budgets and backoff | BSD-3-Clause; Scrapy developers. Original local implementation; package not imported. |
| DiskCache | Documentation 5.6.1 and project LICENSE | Persistent reuse, bounded memoization, comparison of stampede-control strategies | Apache-2.0; Grant Jenks. Reference only; package not imported. |
| OpenTelemetry Python | Official concepts pages and Python project LICENSE, unpinned | Stage timings, parent-child execution relationships and bounded telemetry dimensions | Apache-2.0. Reference only; no SDK or exporter installed by BEAST20. |
| DuckDB | Official workload-tuning documentation and project LICENSE, unpinned | Optional future columnar analysis of larger benchmark/public-data batches | MIT; Stichting DuckDB Foundation. Evaluated as a future adapter; not an installed dependency or completed integration. |
| HTTP semantics and caching | RFC 9110 and RFC 9111, June 2022 | ETag/Last-Modified validation, status handling, Retry-After and cache-policy distinctions | IETF Trust document terms; extracted Code Components require the stated Revised BSD notice. No RFC Code Components or substantial prose copied. |

Circuit breakers, token buckets, idempotency receipts and cancellation handling
are implemented as common engineering patterns using original code. They should
not be attributed to a particular source repository unless source from that
repository is actually adapted. Conditional refresh here is a bounded feed
operation; it should not be advertised as a complete RFC 9111 HTTP cache without
testing all required cache behaviors.

## Primary reference links

### Git

- [Git Objects](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects)
- [Git COPYING](https://github.com/git/git/blob/master/COPYING)

### SQLite

- [SQLite public-domain statement](https://sqlite.org/copyright.html)
- [FTS5](https://sqlite.org/fts5.html)
- [FTS5 trigram tokenizer](https://sqlite.org/fts5.html#the_trigram_tokenizer)
- [Write-ahead logging](https://www.sqlite.org/wal.html)

### CPython

- [graphlib](https://docs.python.org/3.13/library/graphlib.html)
- [asyncio synchronization](https://docs.python.org/3.13/library/asyncio-sync.html)
- [asyncio tasks and cancellation](https://docs.python.org/3.13/library/asyncio-task.html)
- [Python history and license](https://docs.python.org/3.13/license.html)

### Caching and dependency graphs

- [cachetools 7.3.0](https://cachetools.readthedocs.io/en/v7.3.0/)
- [cachetools LICENSE](https://github.com/tkem/cachetools/blob/master/LICENSE)
- [NetworkX descendants](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.dag.descendants.html)
- [NetworkX documentation and BSD license](https://networkx.org/documentation/stable/)
- [DiskCache tutorial](https://grantjenks.com/docs/diskcache/tutorial.html)
- [DiskCache recipes](https://github.com/grantjenks/python-diskcache/blob/master/diskcache/recipes.py)
- [DiskCache LICENSE](https://github.com/grantjenks/python-diskcache/blob/master/LICENSE)

### Retrieval and public source refresh

- [Lucene 10.2.1 TopDocs and RRF](https://lucene.apache.org/core/10_2_1/core/org/apache/lucene/search/TopDocs.html)
- [Lucene LICENSE.txt](https://github.com/apache/lucene/blob/main/LICENSE.txt)
- [Scrapy 2.13 AutoThrottle](https://docs.scrapy.org/en/2.13/topics/autothrottle.html)
- [Scrapy 2.13 downloader middleware](https://docs.scrapy.org/en/2.13/topics/downloader-middleware.html)
- [Scrapy LICENSE](https://github.com/scrapy/scrapy/blob/master/LICENSE)
- [RFC 9110 HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
- [RFC 9111 HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html)

### Measurement and optional analytics

- [OpenTelemetry traces](https://opentelemetry.io/docs/concepts/signals/traces/)
- [OpenTelemetry metrics and cardinality](https://opentelemetry.io/docs/concepts/signals/metrics/)
- [OpenTelemetry Python LICENSE](https://github.com/open-telemetry/opentelemetry-python/blob/main/LICENSE)
- [DuckDB workload tuning](https://duckdb.org/docs/2.0/guides/performance/how_to_tune_workloads)
- [DuckDB LICENSE](https://github.com/duckdb/duckdb/blob/main/LICENSE)

## Correctness constraints that accompany reuse

Cache identities include the exact source digest, source edition, Work mode,
principal and rights epoch. Source-byte equality does not establish current
permission, source truth or snapshot freshness. The host must check current
rights at read and return; persistent local records do not supply hosted
authorization. Content changes and relevant algorithm/configuration changes
must invalidate or change the identity of derived values.

The GF8 adapter additionally keeps a bounded, trusted result-digest map in the
runtime process, separate from the editable SQLite cache. A validly hashed
replacement cache object therefore cannot silently acquire a newly issued
reasoning receipt. A new runtime recomputes the original GF8 result once before
reusing that physical configuration; this release does not claim accelerated
trust of a cold cache across process restarts. The runtime pins its initial
scope identity, and the original R10 memory checkpoint verification still runs
when a physical result is reused.

Computational dependency edges must remain distinguishable from evidence
relations. `SUPPORTS`, `CHALLENGES`, `RELATED` and `REQUIRES` are not interchangeable
claims. RRF ranks retrieval candidates; its score is neither a truth probability
nor permission to promote a candidate into CANON.

Singleflight is beneficial when concurrent callers request the same expensive
calculation. It must release waiting callers after exceptions and cancellations,
and must not serialize unrelated keys. LRU/TTL caching must retain a real bound;
an entry-count bound is not automatically a disk-byte bound. Historical source
objects can require a separate retention policy.

## Mandarin and other CJK text

The source byte digest is calculated from original text, independently of the
Unicode-normalized search representation. NFKC/casefold normalization can aid
lexical matching but is not an identity transform and must not rewrite evidence.

SQLite documents that trigram full-text queries cannot match fewer than three
Unicode characters. Its Porter stemmer is designed for English. BEAST20's
character and adjacent-bigram postings therefore provide an explicit short-CJK
term path without depending on that trigram minimum. This is lexical retrieval,
not translation, Chinese word segmentation, language-model understanding, or a
guarantee of recall. Tests should include short Mandarin terms, mixed scripts,
punctuation boundaries, supplementary CJK characters, and distinct original
strings with the same normalized search terms.

## Performance evidence and limits

Performance must be measured on the actual combined pipeline and named workload.
The baseline should include a reasonable indexed implementation, as well as any
recovered historical implementation. Avoid attributing an improvement over
repeated full scans to all possible existing systems.

Useful workloads include cold reads, warm repeated reads, distinct concurrent
jobs, duplicate concurrent jobs, source changes, revocation, restarts, provider
backoff and invalid inputs. Record result equivalence, task invocation counts,
latency distributions, memory, object-store growth and network bytes when those
are actually measured. An ablation run should disable a major optimization while
retaining the same correctness conditions and source corpus.

Do not multiply component speedup ratios. Conditional refresh, stable source
identities, selective invalidation, caching and singleflight often save the same
underlying work. Some optimizations add overhead on a cold or small workload.
Thread/async overlap does not automatically accelerate CPU-bound Python code.
DuckDB is not a replacement for every transactional SQLite query; its official
tuning guide explicitly distinguishes large analytical work from many small
concurrent queries.

SQLite's official WAL page documents a rare concurrent write/checkpoint race,
fixed in 3.51.3 and later, with selected backports. The checked local 3.53.1 runtime
includes that fix. The storage component currently retains SQLite's default
journal and serializes its own connection; these local choices do not establish
the behavior of a different hosted database.

Local tests establish local behavior on the recorded environment. They do not
establish hosted latency, authenticated multi-user revocation, live public-feed
availability, independent resident activity, physical cymatic acceleration,
general model intelligence, or universal superiority over other systems.
