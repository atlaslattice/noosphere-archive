# Synthesis20 third-party notice

## Actual small source adaptation: Dagster

Copyright 2025 Dagster Labs, Inc.

Licensed under the Apache License, Version 2.0. The complete inspected upstream
license is included in [LICENSE-DAGSTER-APACHE-2.0.txt](LICENSE-DAGSTER-APACHE-2.0.txt).

The `CODE`, `DATA`, and `DEPENDENCIES` members of `StaleCauseCategory` in
`src/beast20/synthesis_provenance.py` are adapted from Dagster:

- Repository: https://github.com/dagster-io/dagster
- Immutable commit: `be4184924fec7b61de19a828cae73427d33d0187`
- File: `python_modules/dagster/dagster/_core/definitions/data_version.py`, lines 279–282
- Git blob: `08aed0b1ae775478dd3f236b95b7a1bdb30d98a2`
- Source: https://github.com/dagster-io/dagster/blob/be4184924fec7b61de19a828cae73427d33d0187/python_modules/dagster/dagster/_core/definitions/data_version.py
- License Git blob: `82b6b68d6ad4d65757310c2e7dab12ccae01de36`

### Changes

The native module retains these three category names, adds `PEER_EVIDENCE` and
`CHECKS`, uses an explicit category/key order, and returns all changed entries.
The record validation, bounded maps, detached copies, canonical JSON framing,
SHA-256 seal and comparison functions are new local implementation. No Dagster
package or execution engine is imported.

Dagster's `compute_logical_data_version` is **not** copied. At the pinned commit
it concatenates code/input version strings before hashing and omits input names.
The native identity includes field names, dependency labels and strict digest
values in canonical JSON. A self-consistent digest is not authorization or a
verified statement about the underlying sources, peers or check results.

The source file carries a modification notice. No root `NOTICE` file was
present in the inspected Dagster snapshot; this notice does not claim to cover
additional upstream files that are not reused here.

## Design references only

LangGraph checkpoint lineage (MIT), Temporal Python replay validation (MIT), and
in-toto immutable subject/typed predicate binding (Apache-2.0) informed the
campaign design. No code, documentation prose, schema implementation or runtime
from these three projects is copied into this module. Their exact source pins,
inspected file/license Git blobs and primary links are recorded in
[SYNTHESIS20_OSS_LEDGER.json](SYNTHESIS20_OSS_LEDGER.json).

The existing Eigent-derived retry policy and its notices remain separate and
unchanged. This module adds no retry policy, scheduler, host operation or model
call. Its tests exercise record identity, change enumeration and rejection of
malformed or custom Python objects; integration and publication are separate.
