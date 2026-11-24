# Public registry JSON ambiguity hardening — source-only review

This focused patch preserves the larger **272-public-repository** source snapshot already merged on Noosphere main. It extracts the useful strict parser from older draft PR #22, then strengthens it so JSON numeric exponent overflow cannot silently become IEEE infinity. It rejects decoded duplicate keys, raw NaN/Infinity, all floating-point syntax, huge integers, invalid UTF-8, oversized (>4 MiB) payloads, and malformed JSON *before* typed registry validation. No GitHub network access occurs.

The only behavioral change to the pre-existing CLI is replacing permissive `json.loads` with `strict_inventory_loads`, retaining the original `validate_catalog` constraints, authority holds, source metadata, and output types. Other code remains byte-for-byte unchanged.

**Local test receipt:** 14/14 Python tests of the exact strict parser passed with Python stdlib, and `py_compile` passed. These test parsing only: they do NOT prove GitHub runner execution, authentic current repo visibility, cross-language JCS canonicalization, non-public repository coverage, host rights, verified consent, or CANON. GitHub Actions previously failed before any job steps; independent clean-branch integrated CI remains a merge gate.

Issue: https://github.com/atlaslattice/noosphere-archive/issues/3
Superseded partial metadata draft: https://github.com/atlaslattice/noosphere-archive/pull/22 (100 rows, versus 272 in current main).

## 2026-11-22 — non-disclosing CLI error and malformed Python-scalar hold (additive)

Source-only review found two boundary defects in the existing draft implementation:

1. `load_catalog_text` encoded an incoming Python string *before* entering the strict parser's exception guard. An unpaired Unicode surrogate raised an uncaught `UnicodeEncodeError`, rather than an explicit registry HOLD. The size limit remains 4 MiB, and established `CATALOG_TOO_LARGE`, `DUPLICATE_JSON_KEY`, and nonfinite rejection codes remain preserved.
2. The CLI serialized `str(OSError)` for unreadable input, which can disclose an operator's local filename/directory in downstream JSON receipts. File/encoding read failures now return only `{"status":"HOLD","reason":"INPUT_READ_FAILED"}`; parser/validation holds continue to use their existing bounded error codes.

**Synthetic regression cases added on this branch:** in-process unpaired surrogate rejection; missing-file CLI path redaction; invalid-UTF-8 CLI path redaction. The invalid-UTF-8 fixture was corrected in a follow-up commit to use an actual byte `0xff`; preserve the earlier intermediate commit for audit.

**Local verification limitation:** seven *isolated, source-derived* Python checks passed under normal Python and `-O` (14 executions), covering surrogate (raw and JSON-escaped), size, duplicate keys, ordinary/nonfinite metadata, missing path redaction and invalid UTF-8 redaction. Those were a minimal reconstruction of the changed functions, **not execution of the complete checked-out PR tree or the newly committed integrated tests**. No GitHub-hosted CI or independent peer approval was established. Exact GitHub source/test blob readback after commits: `registry/public_registry.py` `877a53ef320bee16e2a91253446680b314d209b0`; `tests/test_strict_inventory_json.py` `677242fd5f44d727aaa26162dd4ba1dec3846ced`.

GitHub source commits: https://github.com/atlaslattice/noosphere-archive/commit/21407412ce561dea9ef7db8d37c462ede36da8d2 ; https://github.com/atlaslattice/noosphere-archive/commit/6077da10c6bff482ee515b1b338be3f414082c5c ; correction https://github.com/atlaslattice/noosphere-archive/commit/dd596d32e632fff80ac3ae6873c86f8580de113e .

**HOLD:** exact-head full repository tests, fresh CI runner admission/step logs (issue #28), owner source-rights and code review before merger. This does not change source ownership, licensing, GitHub visibility, permission, CANON, public release, deployment or any private-data admission decision.

## 2026-11-22 addendum — validate real snapshot calendar dates

The old public-only validator tested `observed_date_utc` against a digit-pattern but accepted impossible dates, including `2026-02-29`, `2026-13-01` and `2026-04-31`, while still emitting `PUBLIC_METADATA_STRUCTURALLY_VALID_NOT_LIVE_VERIFIED`. On the exact pre-change Git blob `877a53ef320bee16e2a91253446680b314d209b0`, six of twelve targeted independent synthetic tests failed (including CLI's invalid-date HOLD case).

An additive fail-closed `_valid_snapshot_date` helper uses strict ASCII `YYYY-MM-DD` and Python stdlib `date.fromisoformat`; invalid dates return the existing `MISSING_SNAPSHOT_PASSPORT` code. The valid historical cut `2026-11-22` and leap day `2024-02-29` remain accepted; public pointer routing, original 272-record snapshot, source/page counts, issue permissions and rights gates are not rewritten.

Exact locally reconstructed source was Git blob-verified before testing. Locally **41 distinct offline unittest methods PASS in ordinary Python and 41 PASS in optimized `-O`**: 29 independent exact-parser tests (including 1,000 deterministic synthetic JSON round-trips) and 12 public-registry snapshot/CLI/rights-boundary methods. `compileall` passed. This is a partial two-module offline reconstruction with synthetic metadata, NOT a full checked-out PR suite, real public inventory re-validation, hosted CI pass or owner rights approval.

Source fix: https://github.com/atlaslattice/noosphere-archive/commit/5428fc0d133e4faa675e52bfc88667be1d25a167 (`registry/public_registry.py` blob `7f39d4fa4319f0b4dd0fbc0941273e99b6fabad6`).
Authored 12 regression tests: https://github.com/atlaslattice/noosphere-archive/commit/d80e860b8ea605d237f96d55674435f25a579be2 (`tests/test_snapshot_calendar_date.py` blob `d8f3de00efe69e1cb482ef99588e1c0c38bffa34`).
The unchanged strict parser blob is `3e911d5846e90c611a9875a69e4ba698be1935ac`. GitHub readback matched all three blobs. Original issue #3 and CI blocker #28 remain OPEN; PR #26 remains DRAFT/UNMERGED. Original predecessor draft #22 CLOSED but retained. No independent peer approval, full integrated CI, hostname/rights attestation, CANON adoption or production change is claimed.

Shared GitHub Actions gate remains HELD: Noosphere run https://github.com/atlaslattice/noosphere-archive/actions/runs/45098142667 and Providers run https://github.com/atlaslattice/atlas-lattice-providers/actions/runs/45103832079 had failed jobs with zero exposed steps. GitHub billing lock is only an external documented candidate until the account owner supplies exact native check-run annotation; no payment, settings change or rerun authorized by this source-only fix.

## 2026-11-23 — GitHub search page-frontier integrity gate (additive source-only review)

The dated 272-public-repository source cut records `source_page_lengths=[100,100,73,0]`, `records_count=272`, and one excluded nonpublic *count* (not a repository identity). The previous schema checked page numbers, a terminal zero and reconciled totals, but **accepted impossible partitions** such as `[101,100,72,0]`, `[273,0]` and `[100,0,100,73,0]`. Those partitions balance mathematically yet cannot describe a GitHub search result page limited to 100 entries, or a continued source read after an empty page. They must not earn a structurally-valid public-source receipt.

A reversible branch-only check requires each non-terminal page to contain **1–100** results, with the existing final zero; it leaves current original cut, records, URLs, historical edition pins and `host_or_canon_authority=NONE` unchanged. 
- Source commit: https://github.com/atlaslattice/noosphere-archive/commit/86c9259849f4cbb895af73c04291a85623ebae54; Git source blob `eb79774438541abb4d213eda299da201c9987619`.
- Six authored public-snapshot regression methods: https://github.com/atlaslattice/noosphere-archive/commit/9ff0ee76ff85425df5d2116bdbd990741546fd2d; test blob `6e7d015b1d16619db9979361274f41c87e798463`.
- **Local scope:** 6 distinct source-equivalent Python frontier controls passed in normal mode and 6 under `-O` (12 case executions). The 6 checked-in integration methods and full exact-HEAD checkout were **NOT RUN** locally; do not conflate source-equivalent checks with exact integrated tests.
- Current-HEAD Actions https://github.com/atlaslattice/noosphere-archive/actions/runs/45180641663 reports failure with Python 3.11 and 3.13 job steps absent; **no hosted test pass or executed assertion demonstrated**. CI issue https://github.com/atlaslattice/noosphere-archive/issues/28 stays OPEN. Original registry acceptance https://github.com/atlaslattice/noosphere-archive/issues/3 also stays OPEN.

Next gate: independent review of the 100-per-page source contract, complete original public-only snapshot tests from exact branch SHA, actual admitted GitHub runner steps/logs, source-rights/privacy checks and explicit owner merge approval. This is not a release, deployed integration, complete repo census, content license, authenticated peer return or CANON promotion; no settings, permissions, visibility, secrets, private source, paid providers or resident state were touched.
