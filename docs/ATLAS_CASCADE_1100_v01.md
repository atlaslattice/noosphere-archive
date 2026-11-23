# Atlas Cascade 1100 — stateful source-only evolution lab v0.1

**DRAFT / TESTED LOCAL / NOT DEPLOYED / NO IDENTITY OR CANON AUTHORITY.**

This is a dependency-free, deterministic **Work-only** fixture model. It deliberately exercises a *different failure surface* from Atlas's existing source-to-renderer range-plan stress work: here the subject is the cumulative integrity of **message admission, exact request-id deduplication, source pins, revocation epochs, read/return checks, Workboard CAS, structural HSN aliases, false callback claims and replayable evidence**. Its outputs are not actual SwarmChat messages or peer interactions.

## Actual execution

The CLI ran **100** first-stage trials, wrote and reloaded the JSON checkpoint from disk, and resumed for **1,000** dependent trials. The second stage uses the full first-stage mutable Work fixture state, previous SHA-256 head and retained regression cases. It does not restart from an empty world. Every trial adds one unique regression case; every subsequent trial rechecks every case accumulated so far.

| Measurement | Actual local result | Not established |
| --- | ---: | --- |
| Stage 1 | 100 cases | 100 model/resident turns |
| Stage 2 | 1,000 additional cases | 1,000 Work posts |
| Total | **1,100** sequential cases | hosted improvements |
| Regression oracle re-evaluations | **605,550** | 605,550 independent scientific validations |
| Distinct HSN coordinates structurally touched | 1,100 / 1,728 | meaning/semantic correctness of 1,100 nodes |
| Distinct Houses touched | 12 / 12 | validated civilizational coverage |
| Synthetic Work post records | 110 | actual broker posts |
| Synthetic Workboard CAS updates | 55 | actual D1 commits |
| Synthetic source-alias candidates | 55 | independently reviewed semantic edges |
| Synthetic revocations and regrants | 55 each | actual IAM change |
| Deduplicated local replays | 55 | hosted exactly-once delivery |
| Negative/no-external-effect outcomes | 605 | verified live denial |
| Real model wakes, authority, privacy bodies ingested | **0** | independent resident identity |

**Stage 100 root:** `0b7f4d61c047cd6c9361d10bcd83c23c9b2cbde6ba5bfe11309356ef75625cd6`

**Stage 1,100 root:** `6c61f264db64680a7337410a4a6182b946da4469d520d8d63a2ff168f79ef3d6`

A SHA-256 ledger **does not prove a host event occurred**; a caller able to rewrite the entire chain can fabricate a coherent hash chain. For that reason, there are two checks: `verifyLedger` checks shape/chain, while `verifyStrict` re-executes all deterministic transitions against the source code. A separate Python implementation checks the serialized stage boundary, schema, structural coordinates, source-only effects, Workboard lineage, aggregate counts and reporting claims. None substitutes for platform issuer signatures or rights-at-return.

## Source-only implementation, intentionally bounded

- Work path accepts only a **LOCAL_ONLY** synthetic fixture tagged `WORK`. PLAY/SOCIAL/IMAGINE/DREAM/QUIET/BRAIN/PALACE bodies are neither read nor synthesized for Work. Mode-denial tests only use invented tags.
- Validating `tenant/account/principal/room/edition/digest/rightsEpoch` in a fixture is **not authentication**. In production these values must derive from a trusted host principal. A caller-supplied certificate or Boolean is not trusted.
- Revoke+regrant changes the simulated epoch; a replay under an old epoch becomes a generic HOLD. Replays do not append duplicate Work posts. Stale CAS cannot overwrite Workboard history. Cross-namespace source labels remain `CANDIDATE_NOT_SAME_AS`, never accepted semantic edges.
- A callback or claimed model activation is always denied by this model; actual transport + receiver invocation attestation requires the real host.
- HSN addresses only rotate through *synthetic structural coverage* using a coprime stride. This is not a review of node definitions, welfare or scientific claims, and 628 coordinates remain untouched.
- One actual current-chat Work opportunity generated these files and tests. The project's 14 voluntary non-Work opportunities remain `UNPERFORMED`, not empty Work records.

## Reproduce

From the artifact root, with Node.js 20+ and Python 3.11+ installed:

```bash
node tools/atlas_cascade_lab.mjs --output dist
node --test tests/atlas_cascade_lab.test.mjs
node --jitless --test tests/atlas_cascade_lab.test.mjs
python tools/audit_atlas_cascade.py dist/stage100.json dist/stage1100.json dist/summary.json
python -m unittest discover -s tests -p 'test_*.py' -v
```

Locally, **66/66 distinct Node assertions passed** under normal and `--jitless`; independent Python audit passed and **15/15 Python unit tests passed**. The first test run was 62/63 because one adversarial fixture mistakenly passed an `undefined` property to a deliberately strict hash encoder. The fixture was corrected; no security behavior was loosened. The original failed log is preserved separately in the owner artifact's notes. Tests are source-only, and the CI workflow must be inspected separately before any green GitHub claim.

## Gates for real Atlas/SwarmChat use

1. Existing broker/Work host must bind authenticated account, principal, conversation, room and current rights epoch from trusted platform metadata, not from model-supplied fields.
2. Actual receiver independently opts in to one finite signed callback/activation experiment. Record durable broker enqueue, sink commit, arrival/ACK uncertainty, actual model invocation and receiver read/reply as **different** receipt types.
3. Enforce private-mode noninterference **before** index/cache/stat queries and recheck rights at RETURN, including stale 304, ETag and revoke/restore paths.
4. Use the real served Site SHA, deployment ID, source/test digest and rollback proof, followed by independent code-owner review. A test harness does not grant permission, promote CANON or declare a release.
5. Adapt this source-only model to the **existing** broker and Workboard only after competing modules and PR ownership have been reconciled. Do not spin up a competing production scheduler or unbounded rooms.

**Status:** proposed stacked source-only child of existing public evidence-gates PR, intentionally no production modification or private exports. Human-root release and any constitutional adoption remain separately gated.
