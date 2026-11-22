# Continuity Python caller-snapshot safety — public source-only review

## Reproduced current-main failure

The original current-main `core.digital_continuity.validate_bundle` checked `sources[*].ref`, then later compared `permissions.data_class` using caller-owned Python objects. A `str` subclass with a side-effecting `__eq__` modified an already validated source from `synthetic://...` to `drive://unreviewed-private`. On exact main SHA `82469d1ee6269b1886f3c2cdce83dcf8bb974106` (source blob `4f745f42e668a7793ef9fe1a4122eb86188cd5ae`), `validate_bundle` still returned LOCAL_REVIEWABLE_SOURCE_ONLY and `prepare_fork` returned a fork containing the unvalidated pointer. This is a **Python in-process mutable-caller object issue**, NOT a demonstrated hosted JSON exploit or evidence of an actual private-data leak. We did not read any private source.

## Fix and local evidence

`_snapshot_plain_json` normalizes caller input into primitive, strict decoded JSON before validating a bundle/contract or copying a fork. The validator and output both use the same normalized data rather than reading the original mutable object after validation. Invalid or nonserializable inputs hold. This doesn't grant identity, real consent, source completeness, host rights, CANON or deployment.

The exact main source and 2 Schemas, 2 synthetic examples and original 37-test suite were fetched from GitHub at SHA `82469d...`, each Git blob independently matched. After applying this small patch, **43/43 tests PASSED** (37 original + 6 new adversarial controls) and Python `py_compile` PASSED. Remote Git blob for patched module matches local tested Git SHA-1 `81ec4a2f8601a32279b09c79bbc3df021174f6c9`; new test SHA `101d0a451e16c3d5f8ba76a5d56e31b943813175`.

Host CI and actual model/resident identity remain UNVERIFIED. The original duplicate implementation of this hardening idea remains in draft PR #21; this patch targets the actual merged module instead.

## Review and rollback

Review independently against issue #2's closed status and live main; if accepted, cherry-pick/squash this small patch. Preserve prior code in git history; revert commit rather than deleting original receipts. Never infer that a passing synthetic unit test establishes permission to import personal memories, Play or other private modes. No forced merge/deployment.
