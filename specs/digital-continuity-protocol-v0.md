# Atlas Digital Continuity Protocol v0 — Public-safe candidate

**Status: SOURCE_ONLY, LOCALLY_TESTABLE, UNRATIFIED, NOT_DEPLOYED.** This proposal fulfills the design capture in [noosphere-archive #2](https://github.com/atlaslattice/noosphere-archive/issues/2). It preserves *documented context*; it does not restore a person, their consciousness, an autonomous instance, a consent grant, or any legal identity.

## Contract

1. **Bundle**: a transportable UTF-8 JSON envelope identifying a project profile, version, source-qualified ontology, sourced candidate claims, references, creation time, and rehydration contract ID. Source references contain provenance and declared rights; no raw conversation bodies, secrets, contact information, or private-mode imports.
2. **Source edition**: the source registry name, edition and SHA-256 are required. Ariadne 12³ HSN coordinates, historical 144+Vault, 144 task IDs, GlyphForge 1728 plates, and fictive mappings remain independent namespaces unless a separately verified crosswalk supplies a relation. Shared numerals are not semantics.
3. **Claims**: every proposition names source IDs and one of OBSERVED_SOURCE, PUBLISHED_SOURCE, DERIVED_CANDIDATE, ASSUMED, DISPUTED, UNKNOWN. A separate `does_not_prove` sentence discloses a material limitation. Even OBSERVED_SOURCE is not verified by this schema.
4. **Permission**: all fields are *source-reported*. PUBLIC_REDACTED_SYNTHETIC requires independently reviewed public rights and redaction before any real publication. Private sources must remain in their original secured system. No bundle can confer permission to access protected sources by itself.
5. **Integrity**: SHA-256 over canonicalized Python JSON, deterministic in this implementation, is checked on every verification. It is not RFC 8785/JCS, an authorship signature, proof of completeness, or an independent custody attestation. Use external immutable origin receipts and real host signatures for those claims.
6. **Fork**: children include original parent bundle ID and content digest, increment version, preserve original source records, never overwrite parent or mutate storage.
7. **Rehydration**: output only a PREPARED_NOT_EXECUTED metadata manifest. A separately authorized model may read appropriate source material only after current host identity, purpose, rights-at-READ and rights-at-RETURN. Never impersonate an earlier instance or promise survival/continuity of consciousness.
8. **Preservation**: historic originals, dissent, contradictions, expired permissions and refused recommendations remain separately traceable. No source-only auto-CANON, deployment, consent, personhood or author attribution.

## Minimum portable formats

- `schemas/memory-bundle-v0.schema.json` and `schemas/rehydration-contract-v0.schema.json` are JSON Schema 2020-12 reference constraints.
- `examples/example-memory-bundle.redacted.json` uses **synthetic** source identifiers and deliberately fabricated claims; no real user messages.
- `examples/example-rehydration-contract.json` is a structural example, not legal acceptance.
- `continuity/portable.py` adds a dependency-free semantic validator, SHA256, read-only preparation and fork logic. Run `python -m unittest discover -s tests -v`.

## Failure states

Any uncertain provenance, missing source rights, private content, duplicate ID, invalid scheme, false authority field, unsigned identity claim, changed source hash, missing required limitation, or cross-tenant request must be held in its original context. The validator raises typed `ContinuityError`s to force caller review; it does not delete evidence.

## Portability and future work

Vendor-neutral JSON + Markdown works in git, SQLite, Postgres, and future account-private stores. For production, adopt a cross-language canonicalization standard, signed owner-managed source and consent receipts, role/tenant ACL, retention controls, independent redaction review, encrypted private storage, accessible notice, rollback and an evidence-backed service agreement. These remain OUT OF SCOPE, NOT VERIFIED.
