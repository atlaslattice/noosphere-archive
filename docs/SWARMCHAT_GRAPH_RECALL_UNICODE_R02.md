# Recall-auditor raw-offset correction R02

This source-only patch extends the existing recall auditor. It changes no live
search index, room state, permissions, deployment or release decision.

## Source and independently reproduced defect

Baseline: noosphere-archive draft PR #32 at commit
`2e5aba2a54b0d8ffab2fa7539a8698861424313a`, auditor Git blob
`a4030a50c8304a59a1da19fd4f29dcf229dd0364`.

The baseline searches `body.toLowerCase()` and reports the resulting index as an
original-text offset. U+0130 expands from one original UTF-16 unit into two units
when lowercased. Synthetic source `İ TOKEN` contains `TOKEN` at raw offset 2,
but the baseline reports 3; slicing the original at 3 yields `OKEN`.

## Repair and compatibility

The existing query validator admits only ASCII letters, digits and underscores.
Fold ASCII A–Z only, as the related Atlas ONE WorkFullBodySearchPort already does
in PR #18 at commit `9372bb66a01fa90701a3cead88a576b88822c4aa`, source Git blob
`e77b15679711aaa9fe06e4e12323f11a1d4936e6`. This preserves source length and exact
UTF-16 positions, and makes the two source candidates agree on case matching.

All previous fields remain. Two additive metadata fields state the contract:

- `literalOffsetUnit: RAW_SOURCE_UTF16_CODE_UNITS`
- `caseFolding: ASCII_A_Z_ONLY`

This deliberately does not provide Unicode normalization, locale-aware Turkish
matching or compatibility equivalence. ASCII `Istanbul` matches `ISTANBUL`;
`İstanbul` and `ıstanbul` do not. The ASCII suffix `STANBUL` still matches inside
`İstanbul` at raw offset 1. `KELVIN` no longer matches ASCII `KELVIN` through the
old Unicode lowercase alias. This is an explicit narrow-contract change, covered
by tests; callers requiring Unicode equivalence need a separate source-mapped
search contract rather than reuse these offsets.

An exact raw substring can begin or end inside a grapheme cluster. These offsets
are not rendered DOM locations, visual highlight permission, source-map proof,
current authorization, or hosted evidence.

## Local verification

Run from the candidate directory:

```sh
node --test tests/graph_recall_audit.test.mjs
node --jitless --test tests/graph_recall_audit.test.mjs
```

The original 23 tests are retained verbatim, with nine new test groups covering
expanding Unicode prefixes, repeated prefixes, astral UTF-16 counting, ASCII case,
combining marks, grapheme limits, Turkish suffixes and explicit matching limits.
Only generic synthetic text is used. No account-private Work body is included.

Status: SOURCE_PINNED and LOCAL_CANDIDATE. No hosted CI, merge or deployment is
claimed. Preserve the original baseline and dissent before any remote update.
