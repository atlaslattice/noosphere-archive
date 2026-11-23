# Continuity Python caller-snapshot safety — public source-only review

## Reproduced current-main failure

The original current-main `core.digital_continuity.validate_bundle` checked `sources[*].ref`, then later compared `permissions.data_class` using caller-owned Python objects. A `str` subclass with a side-effecting `__eq__` modified an already validated source from `synthetic://...` to `drive://unreviewed-private`. On exact main SHA `82469d1ee6269b1886f3c2cdce83dcf8bb974106` (source blob `4f745f42e668a7793ef9fe1a4122eb86188cd5ae`), `validate_bundle` still returned LOCAL_REVIEWABLE_SOURCE_ONLY and `prepare_fork` returned a fork containing the unvalidated pointer. This is a **Python in-process mutable-caller object issue**, NOT a demonstrated hosted JSON exploit or evidence of an actual private-data leak. We did not read any private source.

## Fix and local evidence

`_snapshot_plain_json` normalizes caller input into primitive, strict decoded JSON before validating a bundle/contract or copying a fork. The validator and output both use the same normalized data rather than reading the original mutable object after validation. Invalid or nonserializable inputs hold. This doesn't grant identity, real consent, source completeness, host rights, CANON or deployment.

The exact main source and 2 Schemas, 2 synthetic examples and original 37-test suite were fetched from GitHub at SHA `82469d...`, each Git blob independently matched. After applying this small patch, **43/43 tests PASSED** (37 original + 6 new adversarial controls) and Python `py_compile` PASSED. Remote Git blob for patched module matches local tested Git SHA-1 `81ec4a2f8601a32279b09c79bbc3df021174f6c9`; new test SHA `101d0a451e16c3d5f8ba76a5d56e31b943813175`.

Host CI and actual model/resident identity remain UNVERIFIED. The original duplicate implementation of this hardening idea remains in draft PR #21; this patch targets the actual merged module instead.

## Review and rollback

Review independently against issue #2's closed status and live main; if accepted, cherry-pick/squash this small patch. Preserve prior code in git history; revert commit rather than deleting original receipts. Never infer that a passing synthetic unit test establishes permission to import personal memories, Play or other private modes. No forced merge/deployment.

## 2026-11-22 follow-up — invalid Unicode scalar fail-closed review

A separate offline, purely synthetic negative reproduction found that Python `json.loads` accepts an escaped unpaired UTF-16 surrogate in a JSON value or object key. Before this follow-up, `parse_text` and `_snapshot_plain_json` accepted it; `canonical_sha256` then raised a raw `UnicodeEncodeError` while encoding the normalized object. This is a malformed public-source input / local exception-handling gap, **not** evidence of private-content retrieval or hosted exploitation.

The additional draft-branch patch walks decoded JSON keys and values iteratively, holding unpaired surrogates with `INVALID_UNICODE_SCALAR` before canonical hashing. Legal paired escapes remain valid. Existing snapshot behavior remains conservative and returns `NON_JSON_OR_MUTABLE_INPUT_HOLD` for a Python caller with an unpaired surrogate.

Source commit: https://github.com/atlaslattice/noosphere-archive/commit/1d783d580ecda1f483bca6d6c2b5fb7e81b78ef3 (source Git blob `35294f8c2b3a1e5be8612f6dbd543bc7844e8029`). Six-test commit: https://github.com/atlaslattice/noosphere-archive/commit/1cc2a4c8c9e6409cef3df2de3736df1f3ee4f568 (test Git blob `7a01bb1d443bbe9b08b712eddb5fb43d545f8adf`). Remote source and test were read back. Exact test-file Git blob hash matched the local test file. Six distinct tests PASS in normal and optimized `python -O`, **12 executions**, against a local isolated reconstruction of the affected helper functions; Python syntax compile PASS. The full exact-HEAD checked-out module and repository suite were NOT run here, so this is *not* integrated CI proof.

Test accounting correction: current committed branch contains **37** `test_digital_continuity.py`, **7** `test_snapshot_boundary.py`, **5** `test_parse_text_numeric_gate.py` and **6** `test_parse_text_unicode_gate.py` authored methods (55 source methods), not 55 independently executed passes. Earlier `43/43` and `188/188` are historic separate receipts, not current-HEAD suite results. Preserve previous reviewer objections and source editions. At pre-follow-up HEAD `6207febf765dc04af543d68a2f3474568b5f901f`, GitHub Actions runs `45079737139` and `45079737143` had failures and sampled jobs with empty step lists; root cause UNVERIFIED. New commits do not establish CI success.

HOLD: independent checked-out full-suite execution, compatible return-value/Unicode review, CI runner admission (#28), source/rights/license review and human authorization before merge. No private/Play/Social/Imagine/Quiet/Habitat/Brain/Palace body, credential, paid provider, resident, CANON or hosted deployment was accessed or changed.
