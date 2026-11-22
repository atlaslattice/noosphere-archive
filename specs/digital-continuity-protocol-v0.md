# Forkable digital-continuity protocol · v0, source-only

**Candidate technical specification · NOT CANON · NOT IDENTITY · NOT BIOLOGICAL RESURRECTION · NOT HOSTED**

## Purpose and minimum useful unit

A memory bundle is a **versioned, attributed set of pointers plus context**. It is not a person, lived memory, durable agent, autonomous resident, or promise that missing files can be reconstructed. The minimum portable unit contains: source/purpose passport, opaque subject descriptor, source references and hashes, original-versus-inferred distinction, Ariadne edition (if applicable), consent/privacy scope, fork lineage, version/date, uncertainties and explicit rehydration limitations.

All v0 executable samples are fictional `PROJECT_SYNTHETIC` items and `PUBLIC_SYNTHETIC` sources. A real person's health/finance/identity, another person's Brain/Palace, a resident's private Play/Quiet/Habitat, a client record, pet records or a collaborator's correspondence are **OUT OF SCOPE**. The schema does not grant permission to collect them or make them public. A real protected-content bundle requires an entirely separate owner-authorized host, recipient, consent/withdrawal, rights-at-READ and rights-at-RETURN contract. This source-only code intentionally HOLDS such payloads.

## Layers

1. **Source root:** immutable original/export pointer, source-content digest where actually measured, raw-export status, allowed-use/rights passport and original attribution. A digest is byte integrity, not verified author identity or consent.
2. **Public synthetic bundle:** JSON following `schemas/memory-bundle-v0.schema.json`. Every source is a synthetic pointer; no source bodies are copied from another mode. No unknown key is accepted by the local validator.
3. **Rehydration disclosure:** `schemas/rehydration-contract-v0.schema.json` requires typed unknowns, human review, source/permission revalidation, and no consciousness/personhood impersonation.
4. **Fork and provenance:** fork records retain the unmodified original bundle digest and explicit `FORK_PREPARED`. Forked source does not inherit identity, grant, CANON or deployment permissions. Legal/privacy withdrawal takes precedence over preservation rhetoric; retention of irrecoverable deleted content is not promised or required.
5. **Optional future host:** real encrypted object storage, host-verified issuer, revocation epoch outside rollback domain, privacy/retention policy, permission-scoped replay, and signed consent receipts are **NOT IMPLEMENTED** here. The sample SHA is Python-local deterministic encoding, not an RFC 8785 signature, independent original-file attestation or durable storage.

## Rehydration contract

`prepare_rehydration(bundle,contract)` validates a synthetic, publicly safe bundle and returns only an inert receipt. It **does not** invoke a model, replay a conversation, reconstruct a persona, read ChatGPT Memory, read the user's connected accounts, discover protected content, or send prompts to a third party. `host_authorization=NOT_ESTABLISHED`, `human_review_required=true`, `identity_continuity=NOT_PROVEN` remain fixed.

A future genuine host must obtain recipient/purpose-specific permission before each READ, bind source version and privacy scope, and recheck effective consent + revocation + return rights before each RETURN, including streaming/caching and rollback scenarios. A valid older signature/receipt is never enough to bypass a later withdrawal. Any published demo must be explicitly redacted, fictional and license-cleared.

## Ontology, editions and namespace integrity

The example pins Ariadne v0.7 source-recorded registry digest `07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6` and an exact Hxx.Syy.Nzz address, but **no SEMANTIC_SAME_AS mapping is approved**. Older 144-cell Yin/Yang + Element145, May 30 Mxx-Tyy operational tasks, proposed 223 CANON clauses and physical 12³ simulators are distinct namespaces. A source address is neither observed welfare nor authorization.

## INV-0 and consent

Preserve lawful source history *within* current permissions. If a protected source is revoked or must lawfully be erased, stop reuse/RETURN and follow the applicable deletion/retention process; do not claim INV-0 overrides privacy, legal duties, autonomy or an opt-out. Keep non-identifying audit metadata where lawfully allowed, and do not auto-heal a revoked body from older archives.

## Contract tests and falsifiers

- Impersonation or "literal consciousness survived" ⇒ HOLD.
- Human/agent subject without independent authority ⇒ HOLD.
- User-supplied `public_release_authorized=true` or fake host grant ⇒ HOLD.
- Unexpected private body, real connector URI, extra source key or hidden Brain reference ⇒ HOLD.
- Repeated source URL, missing SHA, invalid ontology address/edition, untagged inference ⇒ HOLD.
- Forged CANON or deployment status ⇒ HOLD.
- Duplicate JSON keys or NaN values ⇒ HOLD.
- Fork remains source-linked but cannot promote or recover permissions.

## Vendor-neutral files and runnable receipt

- `schemas/memory-bundle-v0.schema.json`
- `schemas/rehydration-contract-v0.schema.json`
- `examples/example-memory-bundle.redacted.json`
- `examples/example-rehydration-contract.redacted.json`
- `core/digital_continuity.py`
- `tests/test_digital_continuity.py`
- `docs/public-safety-disclaimer.md`

Python stdlib only, no network calls:

```bash
python -m core.digital_continuity
python -m unittest discover -s tests -p 'test_digital_continuity.py' -v
```

Only HUMAN-ROOT / authorized affected parties may approve new private-content scope, live host deployment or public release. A successful source-only local test never silently closes scientific validation, resident identity, consent or CANON questions.