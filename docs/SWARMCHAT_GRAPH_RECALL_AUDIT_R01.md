# Atlas Whole Macroturn R01 — Work Graph Fabric recall gate

**Draft / source-only / no host identity / no retrieval or permission grants / no CANON.**

This small Node.js utility compares an **already authorized** bounded Work source snapshot with an independently returned Graph Fabric search result. It is not a replacement index, live retrieval implementation, security monitor, or automated Work harvester. No account-private room names, message bodies, Palace, Play, Social, Imagine, Dream or Quiet data are included in the public source or tests.

## The specific failure family

A source text may contain a single lexical term, yet the graph response may omit that source as a `QUERY_TOKEN_MATCH`, or return it only as an `EXPLICIT_REFERENCE_NEIGHBOR`. Showing the neighbor as a direct text hit obscures a potentially incomplete index. Conversely, `sourceWindow.hasMore=false`, a ranked-result `limit`, and a room watermark do **not** independently prove full-body indexing, exhaustive query recall, current authorization or semantic equivalence.

`auditWorkRecall()` accepts a supplied Work-only snapshot and independently observed search metadata, then returns a candidate result with source sequence numbers, literal offsets, lengths, and separate retrieval reasons. It never emits original message bodies and never performs host reads or writes. Inputs outside the observed bounded window or labeled as non-Work fail closed. This is a diagnostic comparison, not an assertion about the backend's matching contract; its single ASCII term comparator is narrower than the actual host tokenizer may be.

## Run

```sh
node --test tests/graph_recall_audit.test.mjs
node --jitless --test tests/graph_recall_audit.test.mjs
```

Initial author-local source replay: **23/23 Node `node:test` methods passed** in both modes. The two committed file Git blobs are:

- `tools/graph_recall_audit.mjs` — `a4030a50c8304a59a1da19fd4f29dcf229dd0364`
- `tests/graph_recall_audit.test.mjs` — `c8477dbb3081cf8a3de488086af01e8359c3cd0b`

All fixtures use fabricated Work rooms and synthetic text. A model-generated or callback-supplied `roomId`, body, index result, or source digest cannot grant access or claim host verification. Real source retrieval must remain behind broker-owned READ authorization, with RETURN and sink checks performed by the trusted host.

## Outstanding release gates

1. Locate the actual publisher-pinned source for the served search index; verify whether it indexes full bodies, excerpts, tokens, or ranked prefixes.
2. Test direct lexical hit vs related-source labels on a disposable authorized Work fixture, including late tokens, all-terms vs any-terms, ranked `limit`, and pagination.
3. Require cache/index isolation and independent current READ/RETURN rights with two accounts; do not infer denial safety from generic text or synthetic fixtures.
4. If host source proves an indexed-body truncation bug, repair the publisher-owned code with tests; recheck the exact deployed Site version, source readback and rollback.
5. Do not allow a search result, 12-House coordinate or candidate graph edge to become `SAME_AS`, CANON, or user permission from a lexical match.

**Milestone: SOURCE_TRACED + TESTED_LOCAL. Not CI_VERIFIED, MERGED, HOST_DEPLOYED, HOST_IDENTITY_VERIFIED or CANON_RATIFIED.**
