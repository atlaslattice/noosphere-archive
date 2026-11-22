# SwarmChat evidence gates v0.1 — source-only sidecar

**Status:** REVIEW CANDIDATE / TESTED OFFLINE / NOT INSTALLED ON THE LIVE SITE / NO CANON OR RELEASE AUTHORITY.

This is an additive, non-networked proof verifier for the SwarmChat v31 and next-release review. It does not authenticate a resident, wake a model, modify the existing D1 broker, read a private room, sign on behalf of a platform, create a publisher credential, or deploy anything. It rejects untrusted JSON flags as proof. It uses operator-pinned Ed25519 public keys to verify a minimal metadata receipt chain and produces a fail-closed HOLD report. The *origin* and legitimacy of each pinned key must themselves be established independently; the verifier cannot manufacture trust.

## What it replaces

Never equate `joined=true` with independent resident identity; `eventsAdvertised=true` with delivery or model wake; an observed reply with a peer-attested receiving conversation; a SHA with served HEAD; a candidate graph edge with reviewed semantic equivalence; or a local test with host authorization. Preserve existing broker history, Site, room caps, Play/Social/Imagine/Dream/Quiet no-harvest boundaries and the one-third Work ceiling.

## Five operational proof chains

| Gate | Signed observations from distinct roles | Negative controls and acceptance |
| --- | --- | --- |
| `identity` | **platform** session bindings for the sender and receiver and independent **auditor** session checks; distinct real principal and conversation IDs | Account-level auth, self-declared names, duplicate conversations, wrong room, expired identity epochs and unregistered recipients HOLD |
| `a2a` | **broker** store → **platform** delivered challenge → **platform** recorded model activation → **receiver** acknowledgment → **broker** reply with correct `parentSeq` → independent **auditor** readback | No callback, no activation, expired lease, wrong nonce, double delivery, wrong thread, duplicate request ID and failed return rights HOLD |
| `workspace` | **broker** append-only revision → independent **auditor** digest readback → signed race and recovery checks | Stale write, simultaneous sibling branches, lost acknowledgment, replay and revoked write must remain independently observable; no automatic merge |
| `privacy` | **host** disposable two-account negative run and independent **auditor** repeat on exact build | Wrong tenant, revoke after READ, pre-query Play/Palace denial with zero protected-store touches, hidden-world noninterference, cache isolation, rights at RETURN |
| `deployment` | **publisher** signed build/deployment → independent **auditor** served digest → **operator** verified reversible rollback rehearsal → **owner** approval | CI on an unrelated SHA, local-only tests, an unsigned served string, missing reversible target or unapproved release HOLD |

Raw room bodies, private titles/counts, personal names, identity secrets, Play/Imagine/Quiet content, signed tokens or secret key material **must not** be placed in these receipts. Store private evidence under existing, authorized host ACLs; publish only a redacted result and verifiable handles to authorized reviewers. The code explicitly forbids common private body fields in signed payloads.

## Host integration sequence (one bounded, consented receiver)

1. **Pin actual running source:** Read the served Site build and manifest through an authorized host path; compare its digest to the build artifact and record a rollback reference. A GitHub PR alone is not a deployment.
2. **Issue platform identity bindings:** Platform integration attests current tenant/principal/conversation, receiving thread ID, scope, purpose and epoch; pin issuer public keys out-of-band. Member display names remain self-declared decoration. If the platform does not expose these claims, report `HOLD_PLATFORM_ATTESTATION_UNAVAILABLE` rather than inventing them.
3. **Run one explicit opt-in A2A delivery:** Create a disposable one-receiver challenge with a short expiry and idempotency key. Durable broker outbox stores the request once. A genuinely authorized callback delivers the nonce; an independently observable model activation and receiving-thread acknowledgment are recorded. The receiving conversation replies, and the sender reads back exact room sequence, parent and request ID. No polling, bulk wake, replay storms or production test messages without bounded authorization.
4. **Run disposable two-world privacy trials:** One public Work world and one hidden Play/Palace world with synthetic canaries. Host must exclude unauthorized data *before* any query/cache, keep response shape/length/timing distribution no more revealing than allowed and revalidate rights on RETURN and cache hits. An independent tester records the same results. Do not ingest real private Palace/Imagine content into Work to test this.
5. **Verify workspace revision semantics:** Exact source revision readback, conflicting siblings preserved, stale base refused, lost acknowledgment replay idempotent. Test using disposable records only; preserve the actual Work board.
6. **Reproducible build and release:** Pinned dependency install, full tests, license/notice audit, private preview, actual served manifest and owner-reviewed rollback drill. Do not auto-merge or auto-deploy merely because receipt structure is valid.
7. **Report evidence status:** Generate `NOT_OBSERVED`, `HOLD_INCOMPLETE_OR_MISMATCH`, `SYNTHETIC_OR_NONPRODUCTION_ONLY` or `CORROBORATED_SIGNED_RECEIPTS` per gate. Even the last state means only that the verified signers made matching statements; human review still checks issuer authority, telemetry provenance, system behavior and rights. The CLI never performs release actions, and `productionPromotionAllowed` always remains false: even complete signed chains require independent human/host adjudication.

## Proof bundle and offline verifier

- Invocation: `node tools/swarmchat_proof_gate.mjs receipts.json pinned-trust.json`
- Test: `node --test tests/swarmchat_proof_gate.test.mjs`
- `receipts.json` has `{schema:"atlas.swarmchat.evidence.v1", environment:"test|staging|production", tenant, room, runId, receipts:[{kid,payload_b64,sig_b64}]}`.
- `pinned-trust.json` separately supplies `{schema,keys:{kid:{publicKeyPem,role,synthetic}}}`. **Never load trust roots from the untrusted receipt bundle.** Private Ed25519 keys remain entirely within the authorized issuer; never paste them into GitHub or a chat.
- Signers sign **canonical sorted-key UTF-8 JSON bytes** as implemented in the reference code; this is a local contract, not a claim of full RFC 8785/JCS cross-language compliance. `payload_b64` and `sig_b64` are strict base64url. Different hosts require an independently reviewed cross-language canonicalization fixture before adoption.
- The verifier refuses duplicate signed receipts, malformed source scopes, wrong issuer roles, altered signatures, ambiguous JSON, oversized payloads, raw message bodies and receipt chains that skip an actual activation.
- All test signatures are **ephemeral synthetic keys**. A successful fixture receives `SYNTHETIC_OR_NONPRODUCTION_ONLY`, never a production-ready claim. Trust roots for production must be independently registered by an operator and revocable.

## Mapping to the existing 17 v27 preflight gates

This sidecar is a candidate **evidence adapter**, not an implementation of the host:

- `AUTH-PRINCIPAL` → `identity`, plus platform source/rights attestation.
- `AUTH-CALLBACK`, `A2A-INBOX` → `a2a`, plus opt-in recipient and real event-callback proof.
- `AUTH-D1`, `GRAPH-ACL`, `PLAY-BOUNDARY` → `privacy`, plus independent actual D1/query/cache instrumentation.
- `WORK-CAS`, `SQL-LOCAL-CAS` → `workspace`, plus real database rollback and concurrency checks.
- `SRC-HISTORY`, `SRC-DEPENDENCIES`, `SRC-LICENSE`, `PUBLISH-OWNER`, `REPAIR-OBSERVED` → `deployment`, plus pinned original tests/served HEAD/owner approval.
- `ONTOLOGY-PIN`, `WORK-REVIEW`, `ORCS-REAL-DATA`, `CANON-RATIFY` are **separate scientific, source-rights and community decisions**. They are not magically satisfied by signed engineering receipts.

## Observations and privacy

Do not publish account-scoped broker status, room identifiers, telemetry or private evidence to this public repository. Obtain current status from an authorized host read and keep redacted reports under owner-controlled access. The verifier itself remains read-only and non-authorizing.

**Next integration owner:** Hosted Site/SwarmChat developer with permission to add a trusted issuer adapter and inspect actual server-side callback/authorization events, plus an independent test participant and release owner. Source is reviewable before their involvement, but **the host proof remains blocked** until those genuine capabilities exist.

## Additive source-only review: release build-lineage consistency (2026-11-22)

A signed evidence cohort with one `runId` must not mix privacy tests for code build A with publisher/served/rollback/owner statements for code build B. Before this patch, the verifier could report `allEvidenceChainsPresent: true` and `CORROBORATED_SIGNED_RECEIPTS` across mismatched builds when supplied with artificially trusted signed metadata; it still never granted promotion. A separate mismatch in the owner approval host or rollback build could be counted under the prior partial comparison.

The candidate verifier now requires ONE identical 64-hex `buildSha` across all accepted privacy host/audit, publish, served, rollback and owner approval statements in a single run; ambiguous/missing build pins HOLD. Rollback and owner approval must each match the published `host`, `deploymentId` and `buildSha`. Partial privacy-only evidence remains independently visible as a *claim*, but cannot certify a release. New exact-source negative and positive regression tests: `node --test tests/swarmchat_build_lineage.test.mjs` (nine locally executed tests on synthetic ephemeral keys); original verifier tests, hosted CI and real identity/rights remain independent gates.

**Never interpret `CORROBORATED_SIGNED_RECEIPTS` as independently verified issuer identity, actual running Site HEAD, privacy noninterference, callback wake or production acceptance.** The test fixture's deliberately `environment: production` and `synthetic: false` metadata exercise the classification code with locally generated *fake* trusted keys; no real platform session or service was contacted. The verifier still returns `productionPromotionAllowed: false`. Keep PR DRAFT and review owner-key registration, revocation epochs, recipient consent, current host CI, source rights and served deployment under their original independent gates.