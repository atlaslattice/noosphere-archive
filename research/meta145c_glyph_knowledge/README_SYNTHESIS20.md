# Native1728: bounded synthesis, real peer review, and executable evidence

This increment connects a twenty-round Work review campaign to a local build coordinator, attributed open-source ideas, deterministic falsifier experiments, and the native Atlas ONE / SwarmChat integration views. It extends the existing executor, storage, source federation and acceptance machinery. It does not create a second task queue or invoke a model provider.

The campaign's exact observed message count, executed artifacts, held orders, retained check receipts and replay outcomes are recorded separately in `benchmarks/synthesis20/campaign/CAMPAIGN_EXECUTION.json`. Source publication, host deployment and live route checks belong to the separate release receipt. A source-generated report never grants itself published status.

The completed campaign records **20 actual numbered Work contributions**, **18 executed local review artifacts**, **36 bound check receipts**, **two held orders** and **zero failed orders**. Replay makes **zero executor calls**, reuses eighteen results and earns zero new implementation credit. One broader quality objection remains deferred, so the recorded disposition is **HOLD**. This is an observed outcome, not a failed implementation test. The exact report digest shared by both native projections is `1d74a1edb0e9531e2457c265f43dedbab0c0e2e38b62f35bf3494b6cf7f2ee15`.

## What the repeated simulation establishes

The second run uses seed **1451748**, following the retained run with seed **1451728**. Each executes one initial epoch plus 1,728 repeats, with 1,728 configurations and 1,728 synthetic state transitions per configuration:

| Measure | Each run | Both runs |
| --- | ---: | ---: |
| Epochs | 1,729 | 3,458 |
| Direct transitions | 5,162,766,336 | 10,325,532,672 |
| Additional audit replay transitions | 5,975,424 | 11,950,848 |
| Training / held-out epochs | 1,297 / 432 | 2,594 / 864 |
| Original source hierarchy | 1,728 nodes / 144 Spheres / 12 Houses | Same exact source, two workload seeds |

Every reported transition was executed by the recorded C++ engine. A synthetic year means one request/cache/admission transition. The model does not simulate a year of human research or semantic discovery. All 1,728 configurations run directly, but the synchronous worker variants have equivalent schedules: there are 144 distinct modeled cache/chunk behaviors.

Both runs retain `CFG.W01.M12.B12`: one worker, 2,048 memo entries, 400 records per batch. Neither establishes another configuration speedup. The second engine run took **19.858247190 seconds**, with zero reported freshness violations. Its full report SHA-256 is `6220636ee6ffdf1b33d589e7fca52e2c4e04745f12d43d27fb35cd4326291e30`.

The earlier, independently measured storage implementation improvement remains **11.896580797555023% lower median elapsed time** across nine alternating local full-cascade pairs at the same configuration. All nine outputs and operation counts matched; one pair was slower. Those measurements, their unchanged implementation hashes and the original simulation remain in `benchmarks/native1728_evolution/`. Do not multiply these figures by the earlier configuration gain or interpret them as hosted Atlas/SwarmChat latency.

## Twenty complementary capabilities in this increment

| # | Implemented capability | Why it matters |
| ---: | --- | --- |
| 1 | Explicit twenty-round, twenty-order campaign bound | A finite request has an inspectable completion boundary. |
| 2 | Existing `AsyncExecutor` DAG reuse | Dependencies, durable leases and request reuse retain one execution authority. |
| 3 | Fresh source and authorization checks around work and return | Cached evidence cannot bypass current local checks. |
| 4 | Immutable artifact subjects and baseline hashes | A review identifies the exact artifact it concerns. |
| 5 | Detached client-observed Work records | Public exports keep content hashes while private bodies stay out of source. |
| 6 | Every linked objection remains a challenge | A favorable summary cannot silently discard linked dissent. |
| 7 | Chronological, same-room response relationships | A declared disposition must refer to a real linked observation. |
| 8 | Distinct PASS, HOLD and FAIL outcomes | Missing evidence and an observed failed check retain different meanings. |
| 9 | Required positive and negative checks | Acceptance binds successful behavior and an actual counterexample check. |
| 10 | Check receipts bind artifact, output and check code | A passing result for a different output cannot be substituted. |
| 11 | `VERIFIED_REUSE` and `NO_CHANGE` accounting | Replaying evidence does not earn another implementation. |
| 12 | Optional genuine Excellence binding | The existing pinned runner/ledger can verify task evidence without fabricated task promotion. |
| 13 | Keyed canonical provenance | Field names and map domains participate in identity. |
| 14 | Complete five-category stale causes | Code, data, dependencies, peer evidence and checks expose every changed cause. |
| 15 | Dependent result invalidation | A late stale parent prevents a dependent result from retaining PASS. |
| 16 | Complete retained comparison witness | Baseline losses, causes, counters and source pins cannot be selectively omitted. |
| 17 | Actual parent-result witnesses | Review artifacts bind executor-supplied parent results, not arbitrary digest-shaped text. |
| 18 | Two composable native read operations | Synthesis status and bounded pages use the existing owner-gated composition path. |
| 19 | Round/order/challenge review interface | Pagination, filtering, report identity and stale-response handling support inspection. |
| 20 | Shared exact evidence across two hosts | Atlas shows a compact projection of the same report SwarmChat validates and pages. |

These are capabilities of a small integrated increment. They are not twenty independent source patches, twenty authenticated resident turns, or a claim that every open-source platform has been rewritten.

## Open-source adaptation and cross-domain connections

The source ledger at `docs/native1728/SYNTHESIS20_OSS_LEDGER.json` records exact upstream commits, paths, licenses and reuse scope.

| Upstream | What was used | Native implementation |
| --- | --- | --- |
| Dagster, Apache-2.0 | Small adaptation of `CODE`, `DATA`, `DEPENDENCIES` stale-cause categories | `synthesis_provenance.py` adds `PEER_EVIDENCE` and `CHECKS`, strict bounded canonical records and complete deterministic cause comparison. |
| LangGraph, MIT | Design reference for checkpoint lineage and retry boundaries | Existing executor reuse; no new framework dependency. |
| Temporal Python, MIT | Design reference for replay against retained history | Actual campaign replay verifies zero new handler calls and implementation credit. |
| in-toto attestation, Apache-2.0 | Design reference for immutable subjects and typed evidence | Exact artifact/output/check-code bindings, without claiming a signed attestation or independent identity. |

Dagster's full upstream Apache-2.0 license is retained verbatim. `NOTICE-SYNTHESIS20.md` identifies the original source and local modifications. The other projects are design references, not copied runtime implementations. No new third-party runtime dependency is introduced.

The peer campaign connects software supply-chain subjects to review evidence, scientific preregistration to declared checks, transaction boundaries to acceptance, and accounting conservation to preservation of unfavorable results. These are explicit design analogies. They do not equate research disciplines or establish scientific truth.

## Controlled falsifier results

`benchmarks/bench_synthesis20_falsifiers.py` declares twenty fixed cases and their expected identity/review outcomes before running any method. Every method receives every case once. The two reference encodings are deliberately simplified; they are not executions or benchmarks of Dagster, Temporal or LangGraph.

| Method | Cases matching the declared contract | Losses retained |
| --- | ---: | ---: |
| Values-only reference | 17 / 20 | 3 |
| Whole-packet reference | 16 / 20 | 4 |
| Actual full keyed provenance | 20 / 20 | 0 |

The experiment records 60 case comparisons, 120 encoding calls and 100 top-level actual module calls. Those categories overlap and must not be added as independent work. The shared observation guard makes all methods retain the complete failed check as FAIL and missing/invalid observations as HOLD. That behavior is not attributed to the full encoding's relative advantage. Correct invariance is included: map reordering or irrelevant annotations should not force a change. An unchanged output can coexist with legitimately changed provenance.

The complete result, declared workload, every loss, invocation and source pin are retained in `PROVENANCE_FALSIFIER_RESULTS.json`. The exporter verifies an independently retained exact receipt hash, logical seal, fixed workload, source identities, semantic outcomes and reconciled counters before exposing the summary.

This is contract evidence on a declared synthetic workload. It does not measure general answer quality, cognitive collaboration gain or an equal model-compute budget. The original request for a matched-budget solo/isolated/collaborative task benchmark remains an open research question.

## Peer review changed the implementation

Independent reviewers reproduced substantive defects in the first campaign harness: rehashed artifacts could erase baseline losses, remove cause rows, invent call counts or substitute a parent digest while passing its initial positive check. Review also found a dependency from an independent case to an unresolved quality claim. These findings are preserved as actual Work observations and regression cases.

The corrected harness compares the entire deterministic result with the previously executed, source-pinned experiment, excluding timing only. It captures the executor's actual parent-result witness separately. It records code identities before import, after import, around dispatch and on return. The independent case no longer depends on the broader unresolved claim. Check functions do not secretly repeat encoders to manufacture an expected answer.

Report validators were also tightened against inconsistent phase/reason/count combinations and promotion of unresolved dissent. A content hash establishes consistency with bytes; it does not establish that a peer is authenticated, that a result is true, or that a check was independently performed.

An interpreter-label error was also preserved and corrected. The original full Python gate actually ran under Python 3.12.14, while a copied matrix annotation and one Work summary said 3.13. The entire gate was then rerun explicitly under independently verified Python 3.13.5. Both passed the same 720 distinct tests with two known GF9 data skips; repeats receive no additional distinct-test credit. `PYTHON_VERIFICATION.json` records the original and corrected receipt hashes. A subsequent Work correction does not alter the original twenty numbered observations. Python 3.11 remains unavailable locally.

## Execution and evidence boundaries

`SynthesisCoordinator` is the single entry point over the existing executor. Registered local handlers are trusted pure or idempotent local code; this is not an OS sandbox. External side effects are outside this campaign. Each executor task has one outer attempt. The optional `ExcellenceBinding` uses the genuine pinned types and original plan. It verifies existing acceptance evidence; it cannot mint a JSON claim into a canonical completion. The existing ledger's own source-refresh rule may invalidate stale evidence.

The concrete harness emits **local review-result JSON artifacts**. Its `implementedOrders` counter means fresh, changed local artifacts with passing bound checks and a real handler call. These artifacts are not source patches. Source modules were separately implemented by the actual coding collaborators and are verified by their test suites.

Actual Work messages use self-declared collaborator identities. Their accepted room posts and client-observed digests are evidence of those posts, not verified distinct residents or model calls. The fourteen voluntary non-Work slots per macroturn remain unperformed. No Play, Social, Dream or private Palace bodies are imported. No recurring schedule, provider credential, automatic cross-host dispatcher or paid model run is created.

The general collaborative-answer-quality claim remains deferred. Its linked review orders are held, while unrelated contract checks can execute. A completed twenty-round review campaign can therefore have overall HOLD without a failed implementation test. The interface preserves that distinction.

## Reproduce

From this package directory, the standard-library tests and synthetic falsifier need no private source files:

```bash
python -m unittest discover -s tests_beast20 -p 'test_synthesis*.py'
python -O -m unittest discover -s tests_beast20 -p 'test_synthesis*.py'
python benchmarks/bench_synthesis20_falsifiers.py --output /tmp/provenance-falsifier-rerun.json
```

The optional genuine Excellence tests use the exact existing checkout/plan through `ATLAS_EXCELLENCE_ROOT` and `ATLAS_EXCELLENCE_PLAN`. Without those inputs, they explicitly skip instead of using fake canonical evidence.

The long-horizon replication uses the original authorized Ariadne registry and the retained measured trace:

```bash
python benchmarks/bench_long_horizon.py \
  --registry /private/ariadne-atlas-v07.json \
  --trace benchmarks/native1728_evolution/CURRENT_IMPLEMENTATION_TRACE.json.gz \
  --trace-sha256 c20ce58e2ca932108092496d184f91d8f5ab636a0668b1246ce65fbfbfa7ee33 \
  --epochs 1729 --years 1728 --seed 1451748 --threads 4 \
  --output-dir /tmp/replication1728
```

The full campaign needs private detached records actually read from the authorized Work campaign. `--allow-partial` is an explicit integration option and produces a visibly partial report; it cannot be used to claim twenty observed rounds.

```bash
python benchmarks/run_synthesis20_campaign.py \
  --peer-observations /private/observed-work-input.json \
  --output-dir /tmp/synthesis20-campaign

python benchmarks/export_synthesis20_hosts.py \
  --campaign-dir /tmp/synthesis20-campaign \
  --swarm-root /authorized/swarmchat-checkout \
  --atlas-root /authorized/atlas-one-checkout
```

The exporter checks the two exact existing Site project IDs. It writes source projections only. Tests, builds, source publication, deployment and live route verification remain separate operations recorded in the release receipt. Ordinary reads do not post to Work, mutate a queue, initialize source acquisition or invoke a provider.

## Native interfaces

### Startup correction discovered during publication

The first Atlas publication attempt of this increment failed the hosted worker's startup CPU limit. Profiling identified eager interoperability construction and tool-catalog generation, which performed three snapshot passes over all 1,884 source roles during module import. The fix defers the existing read singleton and deeply frozen catalog to first authorized use. Source checks and request-specific command authorization are preserved; failed validation is not cached.

Five fresh local Node imports per version measured median user CPU falling from 241.464 ms to 51.474 ms, a 78.68% reduction. This is a local cold-import measurement, separate from the earlier storage replay and any hosted latency claim. The full Atlas gate then passed 403 tests, including three startup regressions, with all 170 prior assets preserved and exact catalog/interoperability response parity. `ATLAS_STARTUP_FIX.json` records the local correction; `HOSTED_SYNTHESIS_RELEASE.json` records the separate deployment outcome and live checks.

### Entry points

- SwarmChat: `/work/integration/synthesis`, with `swarm_native1728_synthesis_status` and `swarm_native1728_synthesis_page` through the existing MCP host.
- Atlas ONE: `/integration/`, with the additive synthesis projection in the existing `atlas_librarian_integration_status` response.
- Existing Ariadne, META145, GrokSeek planning, research queue, evolution and twelve-component composition paths are retained.

The two native read operations compose through the same bounded dependency-binding and request-deduplication mechanism as earlier integration tools. The report keeps exact artifact subjects, explicit phases, preserved dissent and the separate replication record inspectable. Registration does not imply every tool in the wider system was invoked.
