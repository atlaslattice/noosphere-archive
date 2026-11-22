# Public repository registry — ambiguity and size hardening

**2026-11-22 · Candidate local source fix · No host/CANON authority**

## Problem

The source-only `public_registry` CLI previously used Python `json.loads` with a nonfinite-number hook but without `object_pairs_hook`. Duplicate JSON keys were silently collapsed. An input such as `"visibility":"private", "visibility":"public"` within the same repository record could therefore be interpreted as public when the raw bytes were contradictory. This is an **ingestion ambiguity**, not proof that any actual private repository was exposed.

## Correction

- `load_catalog_text` rejects duplicate JSON keys at every depth with `DUPLICATE_JSON_KEY`, before downstream `validate_catalog` sees the object.
- Limits public metadata text to **4 MiB** before parsing, rejects non-finite literals and scalar roots, and fails closed on excessively deep JSON.
- All previous strict public-only catalog, source-page, no-HSN-mapping, no-authority and URL protections remain.
- No repository visibility changes, private source retrieval, network writes, CANON or hosted deployment.

## Reproducibility

```bash
python -m unittest discover -s tests -p 'test_public_registry.py' -v
python -m py_compile registry/public_registry.py tests/test_public_registry.py
```

The updated 46-case stdlib suite includes nested/top-level duplicate-key attacks, CLI privacy-preserving refusal, 4 MiB overflow, scalar rejection, and the previous positive/negative cases. **TESTED_LOCAL**, not a hosted authenticated parser assessment. The existing 272-entry public snapshot remains preserved unchanged; this patch changes the input reader only.
