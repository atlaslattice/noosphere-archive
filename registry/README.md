# Atlas public repository registry · source-only v0.1

**CANDIDATE / PUBLIC METADATA ONLY / NOT CANON / NOT HOSTED / NO PERMISSION GRANT**

This registry is the public-only, non-destructive Wave A deliverable for [Noosphere issue #3](https://github.com/atlaslattice/noosphere-archive/issues/3). It unifies public GitHub repository pointers for Noosphere, Alexandria, Ariadne and GPTBrain **without asserting their contents are equivalent**. The associated core-repo map is a design routing guide, not live interoperation.

## Snapshot boundaries

- `public_repo_inventory_2026-11-22.json`: **272 public repository metadata records** from four GitHub public-search pages (100, 100, 73, 0). **One non-public listing result was excluded entirely**, not recorded by name, ID or URL. This is one non-atomic *public search cut*, not a complete account/private census. Search visibility, branch and archive state may change.
- Source query: `org:atlaslattice`, through the account-connected GitHub repository search. Each record retains exact public source URL and numeric repository ID as returned, public visibility, branch and archived state. No repository contents, credentials, private email, personal health information or leisure history were imported.
- Heuristic `role_candidate` and `sensitivity_name_flag` are **inferred from public repo names only**; neither is semantic content review. `readiness = HOLD_FOR_SOURCE_AND_RIGHTS_REVIEW` even for a repository that is already public. `sphere144_tags` and `related_core_repos` deliberately remain empty until a genuine source/rights/semantic crosswalk.
- Public repository search does not enumerate inaccessible, unindexed or private repositories reliably. Do not infer their nonexistence. A registry URL is not a valid access token.

## Run locally, with Python standard library only

```bash
python -m registry.public_registry
python -m registry.public_registry --lookup atlaslattice/noosphere-archive
python -m registry.public_registry --issue https://github.com/atlaslattice/noosphere-archive/issues/3
python -m unittest discover -s tests -p 'test_public_registry.py' -v
```

All commands are read-only. Validation checks source pagination, strict public scope, exact canonical GitHub URLs, unique repository IDs/names, unexpected private fields, required HOLD statuses, and distinct role/mapping/provenance concepts. Failed validation yields `HOLD` and exit code 2. The lookup tool never fetches source content or asserts an issue exists, and cannot merge, close, promote or deploy.

## Status ladder

`PUBLIC_METADATA_OBSERVED` (current) → `CONTENT_REVIEWED_WITH_RIGHTS` (future) → `SEMANTIC_RELATION_ADJUDICATED` (future) → `HOST_PERMISSIONS_VERIFIED` (future) → authorized implementation (future, separate).

Index coverage must never inflate evidence quality or human flourishing. No automatic mapping to Ariadne v0.7's 12 Houses / 144 Spheres / 1,728 nodes; source edition/digest and review are mandatory for such links. The older 144-cell Yin/Yang/Element-145 editions are unrelated coordinates unless explicitly crosswalked.

## Next waves, deliberately **not completed**

- **Wave B:** obtain per-repo rights and owner review; propose reciprocal links from `manus-artifacts`, `sheldonbrain-rag-api` and other core repos on separate reviewed branches. This package only supplies the Noosphere-facing public source map.
- **Wave C:** independently inspect each public repository for secrets, rights, licenses and domain sensitivities before any README/public release edits. Existing public visibility is not safe-release certification.
- **Wave D:** attach exact Ariadne HSN source/passport, dated provenance and typed, reviewer-signed semantic edges; no auto-join, deploy, or CANON promotion.

The original issue and any conflicting architectures stay visible. No migration, rename, deletion, private cross-mode reads, paid calls, background agents or authority effects happen here.