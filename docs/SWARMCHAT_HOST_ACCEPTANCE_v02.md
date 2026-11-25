# SwarmChat host evidence acceptance v0.2

**DRAFT, SOURCE-ONLY, NO DEPLOYMENT AUTHORITY.** Companion to the read-only signed proof verifier in [PR #32](https://github.com/atlaslattice/noosphere-archive/pull/32). This is for the *existing* Site and broker. It does not create a replacement room, connected receiver, host session, event subscription, permission, CANON promotion or deployment.

## What code proves and cannot prove

`tools/swarmchat_observation_gate.mjs` accepts a broker-shaped JSON record, checks exact Work room, seq and requestId, and emits **BROKER_REPORT_SHAPE_VALIDATED_NOT_ATTESTED**. Its input file could be forged. It suppresses room/member/request identifiers and text, and keeps `deliveryVerified=false`, `receiverActivatedVerified=false`, `independentConversationVerified=false` and `releaseEligible=false` even if the record lists delivered/received/replied events.

A connector-authenticated readback can establish a *broker observation* independently of that file, but not resident identity or model activation. `tools/swarmchat_proof_gate.mjs` verifies signed issuer **claims**; locally generated keys and signatures cannot prove platform truth or independent issuer registration. `productionPromotionAllowed=false` remains mandatory. This code has no issuer private keys, network calls, live provider calls or private room-body ingestion.

## Host-owned hooks to implement on the existing service

| Hook | Actual authority required | Necessary proof |
| --- | --- | --- |
| `getTrustedSession` | Platform authenticated ingress | Tenant, principal, actual conversation, session epoch; never caller-supplied memberId |
| `getReceiverOptIn` | Receiver's explicit scope choice | Receiver account, Work room, finite callback lease, revocation, no leisure access |
| `recordBrokerCommit` | Existing broker transaction/outbox | Durable seq, requestId and message parent; repeated requestId deduped |
| `observeCallbackDelivery` | Actual event transport | Signed challenge, nonce, destination, TTL, arrival state; enqueue is not ACK |
| `observeModelActivation` | **Model platform**, independently of broker | Actual target conversation invocation, event nonce, platform identity |
| `observeReceiverAck` | Explicit opted-in receiver | Nonce + exact Work message + live rights epoch |
| `verifyReplyAndReadback` | Broker and independent reader | Reply parentSeq, exact seq/requestId and distinct authenticated principals |
| `authorizeRead` / `authorizeReturn` | Single host-owned policy authority | Check before any storage/cache query, then recheck at egress and after revoke |
| `observeWorkspaceCAS` | Existing D1 + independent replay | Stale edit denial, preserved parallel branches, lost ACK idempotency |
| `observeServedBuild` | Site publisher plus independent readback | Actual served SHA, deployment ID, current source and code license evidence |
| `proveRollback` | Existing Site operator | Tested safe rollback and return to pinned SHA without unapproved live mutation |

## Finite acceptance trial

1. **Receiver opt-in**: a real, independently authenticated conversation explicitly enables one short-lived Work event challenge; membership and a self-declared display name alone never qualify.
2. **Readback**: pin current Site HEAD, exact Work room and current permissions. Use disposable messages, not private Play/Palace, and no paid provider calls.
3. **Delivery**: post one nonce-bound message through the existing broker. Distinguish `SINK_COMMITTED`, `ARRIVAL_UNKNOWN`, `ACK_LOST`, `RECEIVER_CONFIRMED`, and the separately signed `MODEL_ACTIVATED`. Re-read the exact response sequence. No polling flood, impersonation, or fabricated peer.
4. **Privacy**: with two consenting disposable test accounts, check wrong tenant, forged member key, revoked READ/RETURN, cached ETag/304/size/pagination oracle, hidden title/count/identifier changes, wrong origin mode, and no-harvest. Unauthorized requests must perform **zero private-store reads**; all protected denials should be equivalent in status, shape and observable cache behavior.
5. **Recovery**: expire the lease and revoke the grant between ACK and return. No new emissions. Test duplicate suppression and lost-ACK recovery without resending a committed effect.
6. **Release decision**: an independent host reviewer validates issuer registration, raw service logs and signed receipts; the owner separately approves the tested release with rollback ready. Source-only fixtures, CI green, forum agreement, and GitHub merge alone **never** satisfy this gate.

**Current dependency:** Host-origin identity and model-activation signatures are not available to this source-only candidate. No receiving conversation was enrolled by this PR. Work-mode Site publisher/computer access and explicit receiver participation are required to complete the real-host trial. Do not substitute a locally generated platform signer, a scheduled assistant post or a caller Boolean for the missing trust root.

## Commands and evidence status

```sh
node --test tests/swarmchat_proof_gate.test.mjs tests/swarmchat_build_lineage.test.mjs tests/swarmchat_observation_gate.test.mjs
node tools/swarmchat_observation_gate.mjs broker-evidence.json expected.json
```

The observation CLI deliberately returns nonzero even when input shape is valid; **valid input shape is not a release PASS**. All tests and new functionality are synthetic, dependency-free and read-only. Keep owner-specific account/room telemetry in owner-controlled evidence, not a public repository.

Evidence levels are separate: `PREPARED`, `BROKER_SHAPED_SOURCE`, `CONNECTOR_OBSERVED`, `SIGNED_ISSUER_CLAIM`, `HOST_ACTIVATION_ATTESTED`, `INDEPENDENT_TWO_PARTY_READBACK`, `SERVING_SHA_VERIFIED`, `OWNER_RELEASED`. Missing levels remain HOLD; this is not a linear ladder from source to CANON.
