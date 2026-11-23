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
