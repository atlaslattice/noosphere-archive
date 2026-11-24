# Native1728 — measured strategy selection and native tool composition

Native1728 connects the existing BEAST20 runtime, source-pinned federation, META145 selection, and native Atlas/SwarmChat tool surfaces. The recorded local experiment evaluated **1,728 configurations**, selected **one worker, 2,048 memo entries and 400-object read chunks**, and measured that choice against the baseline in **nine alternating pairs**.

**Release state:** the combined native hosts are deployed: SwarmChat version **48** at source commit `d5fe7493ffab55578005561eb2d91f852b8a609b`, and Atlas ONE version **11** at source commit `5432a9b429c56456081ff76fc1f0b7f654ef9ec5`. Existing audiences and owner access controls are preserved. [Hosted release evidence](benchmarks/native1728/HOSTED_RELEASE.json) records publication and the exact extent of live verification.

## What the evidence establishes

| Layer | Recorded result | Scope |
| --- | --- | --- |
| Strategy simulation | 1,728 distinct configurations; 144 selection groups, 12 parent groups, one META145 selection | Finite search over three declared BEAST20 controls |
| Scheduler computation | 24 unique scheduler replays reused across equivalent configurations | Synchronous handler traces share worker schedules; every configuration still receives its own metrics |
| Actual replay | Nine baseline/candidate pairs; identical output digests in every pair | Local composite source-metadata and cold/warm/changed DAG workload |
| Actual federation | Nine calls through three exact-source Python packages | EX1728 inspection, GF9 packet computation and unified Ariadne source processing |
| Native composition | Six MCP operations; 12 registered tool families; bounded DAG executor | Current SwarmChat source, with leaf authorization preserved |
| GrokSeek connection | Existing pure compiler/context integration and owner-gated plan preview | Existing Atlas ONE Librarian host; original orchestrator remains unbound |
| Hosted publication | SwarmChat 48 and Atlas ONE 11, both confirmed successful | Live discovery, direct invocation and browser verification are recorded separately |

The host's separate retrieval-evolution strategy circuit can coexist with this Python memo/worker/chunk search. Each has its own workload, implementation, report and acceptance state. Their counts and performance ratios must be reported separately.

The engineering program's 1,728 **planned tasks** are also a separate namespace from these 1,728 **simulated configurations**. A source plan, a simulation candidate, a tool invocation, a metadata acquisition and an independently completed resident Macroturn are different units of work.

## Measured result and tradeoff

The [measured replay](benchmarks/strategy1728/STRATEGY1728_MEASURED_REPLAY.json) records:

| Metric | Baseline | Selected candidate |
| --- | ---: | ---: |
| Workers | 4 | 1 |
| Memo-entry budget | 256 | 2,048 |
| Object-read chunk width | 400 | 400 |
| Median elapsed time | 2,862.845150 ms | 2,547.397773 ms |
| Memo hits per composite run | 0 | 3,766 |
| Memo misses per composite run | 5,655 | 1,889 |
| Paired output equality | — | 9/9 |

The measured baseline/candidate ratio is **1.123831221155739×**, approximately **11.02% less median elapsed time** on this workload. The separately simulated holdout ratio is **1.5355647033260476×**. The forecast excludes some scheduler/SQLite overhead, so it is not the measured speedup.

The selected configuration reserves eight times as many memo entries. It reduces repeated computation because the bounded working set fits. Its synchronous handlers do not gain CPU parallelism from additional async workers. The result is a workload-specific choice within the declared candidate set, with no claim of a global optimum, hosted latency improvement or multiplied end-to-end gain.

Training comprises a cold graph, unchanged repeat and one supplemental-input change. Holdout uses a different supplemental-input change and is excluded from selection, pruning, objective tuning and Pareto construction. Both splits start with empty memo state. The actual replay alternates pair order and changes executor receipt versions across scenarios so durable receipts cannot hide the memo-capacity effect. Setup and object population are outside timing; graph construction, verified object reads, memo operations, scheduler work and output digesting are inside it. See the [full method](docs/STRATEGY1728_METHOD.md).

## Native interfaces

The SwarmChat source implements these operations in `lib/native1728.mjs`:

| MCP operation | Behavior |
| --- | --- |
| `swarm_native1728_status` | Release identity, source digest and separate simulation/measurement status |
| `swarm_native1728_catalog` | Bounded pages of eligible registered tools and their actual input schemas |
| `swarm_native1728_strategies` | Bounded pages of recorded candidates, plus selection and measurement evidence |
| `swarm_native1728_plan` | Concrete 12-step demo plan without executing it |
| `swarm_native1728_demo` | Run the concrete plan through existing leaf tool handlers and aggregate actual outcomes |
| `swarm_native1728_compose` | Execute a validated DAG of selected read/compute tools with dependency bindings |

The composer accepts at most 24 steps and 12 workers, a 15,000-byte input and a 1 MiB aggregate output budget. Tool eligibility requires both a fixed family allowlist and the registered read-only annotation. Request-supplied names or hints cannot add a new callable tool. The host checks current rights before reading, before dispatch and at return; selected Work tools retain their own access checks.

Dependencies are validated before execution. A binding copies a declared predecessor's JSON-pointer result into a registered input field, then validates the resolved input against that same tool schema. Equivalent calls share one invocation within the current request. Failed/held children block dependent steps, and per-step receipts retain status, output digest, reuse and timing. The composer has no automatic retry, model call, room post or background loop.

The current families are:

| Family | Selected existing tool surface |
| --- | --- |
| Ariadne | HSN descriptor, resolve/search, source topics, canon context, graph previews and the existing opted-in context preview |
| META145 | Perspectives, correlations, bridges, evidence, search, glyphs, local simulations and the separate retrieval-evolution result/handoff tools |
| Engineering program | EX1728 status, task/query, readiness and perspective |
| GlyphForge | Descriptor, compile, wave and recall |
| Cymatic context | Descriptor, lookup, translate and claim preview |
| REEFCORE | Descriptor, compute, Atlas preview and bounded reservoir inference |
| Work graph | Context, trace, communities and graph preview |
| Public research | Source catalog, CFTC/EIA/Census data and import preview |
| Assembly | Blueprint and plan preview |
| Verification | Gauntlet catalog, full-stack preflight and release docket |
| Macroturn and crosswalks | Descriptor, capacity plan and season preflight |
| Source casefiles | Catalog, wave and casefile |

The 12-step demo is a concrete plan, not proof that every eligible operation in all 12 families has run. Registration, local test coverage and a successful live invocation have separate evidence.

The native interface is mounted at `/work/integration` on the existing owner-scoped SwarmChat host. Atlas ONE adds an owner-gated integration view and uses its existing `prepareLibrarianPlan(plan, {registry, tenantId, scope})` for a bounded GrokSeek preview. The trusted registry, tenant and scope come from the host. Previewing does not queue work. The existing `atlas_librarian_program` operation can separately save up to eight source-bound questions and admit ready metadata tasks into the existing D1 queue.

The GrokSeek bridge preserves the original pure compiler/context semantics. It does not mount the legacy orchestrator, create a second queue, configure a provider or make a model call. Its source bodies remain in the owner-scoped host; they are not included in this public package.

## Twenty code-backed capabilities

This map covers the integrated release, including existing capabilities that the new selection and composition layers reuse. Host paths below identify source in the companion owner-host project; they are not missing Python files in this repository.

| # | Capability | Implementation and evidence |
| ---: | --- | --- |
| 1 | Verify exact upstream package bytes before and after delegation | [`SourceMount.verify`](src/beast20/federation.py); Git ancestry, exact package file set, Git blob and SHA-256 checks |
| 2 | Keep tenant/principal/source scope in semantic cache identity | [`Scope` and `semantic_key`](src/beast20/storage.py) |
| 3 | Retrieve content-addressed objects in verified bounded batches | [`ArtifactStore.batch_get`](src/beast20/storage.py); the chunk-width search axis uses this real control |
| 4 | Bound memo capacity and invalidate dependent memo entries | [`memo_put`, `memo_get`, `set_dependencies`, `invalidate`](src/beast20/storage.py) |
| 5 | Execute dependency graphs with durable task receipts and single-flight work sharing | [`AsyncExecutor.run_graph`](src/beast20/execution.py) |
| 6 | Recompute the node → Sphere → House → META145 cascade from source/configuration identities | [`CascadeCompiler.tasks`](src/beast20/runtime.py) |
| 7 | Evaluate the complete 12 × 12 × 12 configuration grid | [`configurations`, `StrategyLab.evaluate`](src/beast20/strategy_lab.py) |
| 8 | Select on training evidence while reporting holdout and Pareto tradeoffs separately | [`StrategyLab.evaluate`](src/beast20/strategy_lab.py); [method](docs/STRATEGY1728_METHOD.md) |
| 9 | Compare the selected strategy with actual paired execution and output parity | [benchmark runner](benchmarks/bench_strategy1728.py); [nine-pair receipt](benchmarks/strategy1728/STRATEGY1728_MEASURED_REPLAY.json) |
| 10 | Invoke the real EX1728 plan/query/readiness/META145 implementation through a pinned local delegate | [`PinnedFederation._excellence`](src/beast20/federation.py); [execution receipt](benchmarks/native1728/FEDERATION_EXECUTION_RECEIPT.json) |
| 11 | Run an exact GF9 synthetic packet round trip with numerical checks | [`PinnedFederation._gf9`](src/beast20/federation.py); CRC/numerical validity does not authenticate a sender |
| 12 | Process original-source coordinates through the unified 1,728-node implementation | [`PinnedFederation._unified`](src/beast20/federation.py); receipt records 20,736 module/node checks |
| 13 | Make bounded effect-aware retry decisions and preserve ambiguous outcomes | [`retry_decision`, `ToolRegistry`](src/beast20/tool_policy.py); licensed Eigent adaptation |
| 14 | Discover eligible native operations with real schemas across 12 families | SwarmChat `lib/native1728.mjs:eligibleNativeTools` and catalog MCP operation |
| 15 | Validate bounded native DAGs before dispatch | SwarmChat `validateComposition`; step, worker, schema, duplicate, cycle and dependency limits |
| 16 | Feed predecessor results into later registered tool arguments | SwarmChat `pointerParts`, `pointer`, `composeNative`; declared bindings and post-resolution schema validation |
| 17 | Share identical native calls within a request | SwarmChat `composeNative` flight map; receipt distinguishes actual invocations from reused results |
| 18 | Produce permission-checked per-step outcomes and propagate failure | SwarmChat `composeNative`; dispatch/return checks, output/receipt digests and blocked descendants |
| 19 | Inspect all candidate forecasts separately from measured evidence | SwarmChat `native1728-release.mjs`, strategies MCP operation and `/work/integration` view |
| 20 | Reuse the existing GrokSeek compiler through the current Atlas ONE boundary | Atlas ONE `librarian/lineage/plan_bridge.mjs:prepareLibrarianPlan`; trusted source registry, structural plan and no automatic dispatch |

These interfaces do not grant a source publication license, turn EX1728 ordinals into Ariadne semantic equivalence, or count simulated candidates as resident turns. Source role identities and namespaces remain explicit in [the component inventory](docs/native1728/PUBLIC_COMPONENT_INVENTORY.json).

## Source parity and provenance

The strategy result is tied to original Ariadne v0.7 digest:

```text
07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6
```

The complete candidate report's logical digest is:

```text
f64c435222f71721dbc7b4b18229ef22a65367d0d1c8e5c0ffb92a1bd6b25b13
```

The trace payload's logical digest is:

```text
03a601aa23bb140e8c199060eb7bc825d937ba17749efdf0a4a7496c2f7f15d9
```

The measured receipt retains all nine raw pairs and SHA-256 values for the five implementation files used during that run. Packaging verified those hashes against the current source and compared all candidate rows, META145 selection and measurement fields with the native host's release data. Logical payload/report digests are distinct from hashes of formatted JSON file bytes; the [compression manifest](benchmarks/native1728/COMPRESSED_EVIDENCE_MANIFEST.json) records both where applicable.

The [federation receipt](benchmarks/native1728/FEDERATION_EXECUTION_RECEIPT.json) records exact package locks for EX1728, GF9 and the unified Python source. It contains coordinate/digest references and bounded results, with no original private source bodies or machine-specific paths. Its nine local calls are not hosted authorization or completion of the 1,728-task engineering program.

The local packaging checks are recorded in [PUBLIC_PACKAGING_REVIEW.json](benchmarks/native1728/PUBLIC_PACKAGING_REVIEW.json). Detailed selected upstream research is in [NATIVE1728_RESEARCH.md](docs/native1728/NATIVE1728_RESEARCH.md) and [NATIVE1728_OSS_LEDGER.json](docs/native1728/NATIVE1728_OSS_LEDGER.json).

## Actual open-source adaptation

The direct code adaptation in this release is Eigent's four-class replay distinction and `automatic_tool_replay_allowed` decision semantics:

- Repository: [eigent-ai/eigent](https://github.com/eigent-ai/eigent).
- Revision: `9840d8aeb304b4af62838331a35c818f128a7be9`.
- File: [backend/app/run_policy.py](https://github.com/eigent-ai/eigent/blob/9840d8aeb304b4af62838331a35c818f128a7be9/backend/app/run_policy.py).
- Git blob: `96186890d6f02cb022d84c7f22b454d0b9a84605`.
- Local Python implementation: [tool_policy.py](src/beast20/tool_policy.py).
- Native JavaScript mirror: SwarmChat `lib/native1728-tool-policy.mjs`.
- License and modification notice: [Apache-2.0 text](docs/native1728/LICENSE-EIGENT-APACHE-2.0.txt) and [third-party notices](docs/native1728/THIRD_PARTY_NOTICES.md).

Atlas adds strict arguments, immutable trusted registrations, finite attempts/deadlines, authorization callbacks, bounded async admission and explicit unknown-outcome handling. A policy decision does not itself repeat a call or prove that a remote idempotency key was honored.

The ten-project OSS ledger distinguishes adapted source, architectural references and optional dependencies. Reviewing MCP SDKs, LangGraph, AutoGen, OpenManus, OpenAI Agents SDK, DuckDB, SQLite and cachetools does not mean those runtimes have all been installed or rewritten.

## Reproduce

Commands below run from `research/meta145c_glyph_knowledge`, unless a different directory is explicit. The local Python benchmark and federation paths use the standard library. The EX1728 source-plan builder uses Node.js 22 or newer and Python 3.10 or newer.

### Restore and verify the complete evidence

The compact publication retains the raw summary and measured replay JSON, plus lossless gzip copies of the full trace and candidate report. The uncompressed full files remain locally available and are excluded from the Git transfer by two exact paths.

```sh
gzip -dk benchmarks/strategy1728/STRATEGY1728_TRACE.json.gz
gzip -dk benchmarks/strategy1728/STRATEGY1728_CANDIDATES.json.gz
```

`-k` retains the gzip files. If the original JSON is already present, skip restoration rather than overwriting it. Verify compressed bytes and decompressed content against the manifest:

```sh
python3 - <<'PY'
import gzip, hashlib, json
from pathlib import Path
manifest = json.loads(Path("benchmarks/native1728/COMPRESSED_EVIDENCE_MANIFEST.json").read_text())
for entry in manifest["entries"]:
    compressed = Path(entry["gzip_path"]).read_bytes()
    raw = gzip.decompress(compressed)
    if hashlib.sha256(compressed).hexdigest() != entry["compressed_sha256"]:
        raise SystemExit("compressed checksum mismatch: " + entry["gzip_path"])
    if hashlib.sha256(raw).hexdigest() != entry["uncompressed_sha256"]:
        raise SystemExit("decompressed checksum mismatch: " + entry["original_path"])
    local = Path(entry["original_path"])
    if local.exists() and local.read_bytes() != raw:
        raise SystemExit("local JSON differs: " + str(local))
    print(entry["original_path"], len(raw), "bytes verified")
PY
```

The archives use gzip level 9, timestamp zero and an empty stored filename. Repeated compression in the recorded zlib environment produced identical bytes. Cross-version compression may produce different compressed bytes even when decompressed content is identical.

### Run the search and paired replay

Use a new output directory so the recorded evidence stays intact:

```sh
python3 benchmarks/bench_strategy1728.py \
  --repeats 9 \
  --output-dir /tmp/native1728-synthetic-replay
```

Omitting source paths uses an explicitly synthetic topology. To reproduce the original-source workload, supply your authorized local original files:

```sh
python3 benchmarks/bench_strategy1728.py \
  --registry path/to/ariadne-atlas-v07.json \
  --topics path/to/openalex_to_ariadne_ALL_4516.csv \
  --repeats 9 \
  --output-dir /tmp/native1728-original-source-replay
```

New timings depend on the machine and workload. Preserve a new report even when its measured result is worse.

### Run the exact-source federation

Obtain an Atlas-Intelligence checkout containing the pinned EX1728 revision `389965f3aaa90c99815f8c727836ca342ef7f313` with unchanged package bytes. From that checkout, build the canonical plan:

```sh
npm run excellence:build
```

Then, from this package:

```sh
python3 benchmarks/native1728/run_federation_demo.py \
  --repository-root ../.. \
  --excellence-root path/to/Atlas-Intelligence \
  --plan path/to/Atlas-Intelligence/programs/excellence1728/outputs/ATLAS_EXCELLENCE_1728_PLAN.json \
  --registry path/to/ariadne-atlas-v07.json \
  --topics path/to/openalex_to_ariadne_ALL_4516.csv \
  --output /tmp/native1728-federation-receipt.json
```

The canonical plan digest is `47084b895a6317db16275a92c3878a340d31af15fb9ab479db7101953c18e49c`. The loader verifies the pinned commit is present in the checkout history and the complete mounted package has the exact pinned bytes. Merely having a directory with the expected name is insufficient. Omit registry/topics for the source implementation's explicit fallback; that does not reproduce the original-source verification result.

### Verify local behavior

```sh
python3 -m unittest discover -s tests_beast20 -p 'test_strategy_lab.py'
python3 -O -m unittest discover -s tests_beast20 -p 'test_strategy_lab.py'
python3 -m unittest discover -s tests_beast20 -p 'test_tool_policy.py'
python3 -m unittest discover -s tests_beast20 -p 'test_federation.py'
```

The current release work recorded 30 strategy tests in normal and optimized Python, 26 Python policy tests, and 15 native JavaScript policy tests. The native composer and API/UI checks are maintained with their owner-host source. A final deployed version should carry its own live receipt; these local checks do not substitute for that receipt.

## Release validation

The final local gates passed 584 distinct Python tests, 220 SwarmChat tests and 270 Atlas ONE tests. Three optional fixture checks were skipped across the named gates; repeated normal and optimized Python runs are not counted twice. The exact gates and source-manifest check are recorded in [LOCAL_VERIFICATION.json](benchmarks/native1728/LOCAL_VERIFICATION.json).

Atlas ONE also completed its two new read APIs in production: all 1,728 configuration records are represented by the pinned summary and the existing GrokSeek compiler prepared the six-step plan. Queue revision and observed model calls stayed unchanged. See [the live service receipt](benchmarks/native1728/ATLAS_ONE_LIVE_SERVICE_CHECK.json). SwarmChat production advertised all six new native tools through its authenticated status tool; its twelve-step demo and the three-step retrieval-evolution composition were executed through the actual local MCP dispatcher. Direct live invocation of the new SwarmChat tools was not available in this conversation's cached tool catalog, and browser inspection of the owner-only lab stopped at sign-in.
