# META145C memory integrity integration

## Source lineage and scope

This change builds on Noosphere PR36 `90672cb4336e17d8af52b1bd651588e46d6309c3` and PR38 `fba6086b434bd7a20e4ba59fceff8858db3040e5`. PR38's original memory blob was `b46ce598e232a756441f820c46a863b4af779e91`. Work-room findings #78, #82 and #91 in `atlas-v32-evolution-50-work-20261123-s01` remain attributed to their contributors. The separate GF8 numerical-claim repair in Noosphere PR41 is not silently included here.

The original 48 source-free tests passed. An additional 22-test suite exposed ten failing integrity/transaction test methods, four missing migration API cases and eight passing controls on the exact PR38 baseline. The seven altered-field subtests belong to one test method and are not counted as seven independent changes.

## Implemented behavior

- `append` acquires `BEGIN IMMEDIATE` before reading and validating the prior chain. Separate SQLite connections cannot create sibling events from the same tip. Any insert or validation failure rolls back. An already active caller transaction is rejected without committing or rolling back that caller's unrelated work.
- `verify`, `triage_delta` and `verified_triage_batch` use a common validator for both hashes and persisted event semantics. Rehashed private-mode rows, malformed sources and invalid compensating retractions are rejected.
- `verified_triage_batch` retains PR38's independent expected-tip/count contract and aggregates the same materialized snapshot it validates. It never verifies one snapshot and consumes a later one.
- `topic_view` migrates from repeated legacy scans to one verified batch. If memory is supplied without a checkpoint, it fails closed before returning any page, count or candidate. No-memory calls keep historical ordering.
- `append` optionally accepts the same checkpoint. A successful receipt includes the new count and hash so the caller can advance its independently retained anchor.
- Both local examples retain their expected anchor outside the SQLite ledger and reuse it after reopening. They begin from a known-empty synthetic trial and deliberately reject an unexpected existing ledger.

Existing payload serialization, stored hashes and SQLite schema remain unchanged. No source registry, OpenAlex candidate relationship, CANON or host service is changed.

## Caller migration

```python
# Start only when the caller independently knows this is a new empty ledger.
checkpoint = {"expected_tip": "0" * 64, "expected_count": 0}
receipt = memory.append(event, **checkpoint)
checkpoint = {
    "expected_tip": receipt["event_hash"],
    "expected_count": receipt["count"],
}
page = topic_view(db, hsn, memory, memory_checkpoint=checkpoint)
```

For an existing ledger, restore the checkpoint from independently trusted custody. Do not replace a rejected checkpoint with values obtained from `memory.verify()`; that would re-trust a possible rollback. Durable checkpoint storage, recovery after a crash between event commit and checkpoint persistence, and host rights epochs belong to the integrating publisher. This module creates no second host authority. A stale or lost checkpoint yields a hold until the publisher reconciles the known writes through its trusted procedure.

The legacy `triage_delta` remains as an integrity-checked local convenience. Its lack of a checkpoint means it cannot detect a valid-prefix rollback. `verify()` now explicitly labels the result `UNANCHORED_LOCAL_CHAIN_ONLY`.

## Verification

From `research/meta145c_glyph_knowledge`:

```sh
python -m unittest discover -s tests_public -v
python -O -m unittest discover -s tests_public -v
```

The new tests include deterministic concurrent writers, corrupted reads and writes, transaction recovery, caller transaction ownership, deleted middle/tail/all events, fully rehashed rewrite, stale append, invalid Work scope/retractions, 1,728-coordinate output parity, one-snapshot consumption and the actual topic-page consumer. They require no private registry or external service.

These results establish local integrity and consumer behavior. They do not establish authenticated reviews, an independently deployed checkpoint service, physical cymatic validation, two-account host revocation, model-weight learning or hosted latency gains. The current publisher must recheck rights at actual RETURN and withhold protected counts, rows, labels and export tokens when access is denied.
