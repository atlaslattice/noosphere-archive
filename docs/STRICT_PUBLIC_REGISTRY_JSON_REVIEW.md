# Public registry JSON ambiguity hardening — source-only review

This focused patch preserves the larger **272-public-repository** source snapshot already merged on Noosphere main. It extracts the useful strict parser from older draft PR #22, then strengthens it so JSON numeric exponent overflow cannot silently become IEEE infinity. It rejects decoded duplicate keys, raw NaN/Infinity, all floating-point syntax, huge integers, invalid UTF-8, oversized (>4 MiB) payloads, and malformed JSON *before* typed registry validation. No GitHub network access occurs.

The only behavioral change to the pre-existing CLI is replacing permissive `json.loads` with `strict_inventory_loads`, retaining the original `validate_catalog` constraints, authority holds, source metadata, and output types. Other code remains byte-for-byte unchanged.

**Local test receipt:** 14/14 Python tests of the exact strict parser passed with Python stdlib, and `py_compile` passed. These test parsing only: they do NOT prove GitHub runner execution, authentic current repo visibility, cross-language JCS canonicalization, non-public repository coverage, host rights, verified consent, or CANON. GitHub Actions previously failed before any job steps; independent clean-branch integrated CI remains a merge gate.

Issue: https://github.com/atlaslattice/noosphere-archive/issues/3
Superseded partial metadata draft: https://github.com/atlaslattice/noosphere-archive/pull/22 (100 rows, versus 272 in current main).
