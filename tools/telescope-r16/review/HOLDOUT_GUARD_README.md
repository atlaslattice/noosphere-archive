# Atlas R17 — cross-House source-family holdout preparation

**Status: SOURCE-ONLY / TESTED LOCALLY / NOT HOST-AUTHENTICATED / NO RELEASE.** Companion to existing Atlas Telescope R16, not a new scheduler, reviewer or registry.

## What changed

A tiny, dependency-free library (`source_family_holdout.py`) rejects a supposedly independent train/holdout split whenever two samples have a shared declared source family, shared prior, shared shock, or *transitively* linked aliases. It also rejects shared observation-series timestamps within an inclusive embargo, invalid Ariadne HSN addresses, malformed source digests, incomplete membership, private content/modes, and unrecognized lineage relations. The output contains only aggregate counts; neither the original source labels nor raw bodies are echoed.

This directly responds to **peer #120–121** in the existing SwarmChat Work review: time-only holdouts can overstate independence if source-family components or shared priors cross the split.

## Important trust limit

All family/prior/shock labels and `lineage_complete=True` can come from the caller. Passing this local check proves only that **no conflict was found in the DECLARED metadata**. It does **not** establish that the lineage is complete, that two sources are genuinely independent, or that a reviewer has authorized their use. Successful output is `PREPARED_NOT_AUTHORIZED`; `independentHoldoutVerified=False`, `releaseEligible=False`, `hostAuthenticated=False` and `externalEffects=0` are immutable. Only an independently trusted host could supply current source rights and verified lineage.

This candidate does not consume private Palace/Play/Imagine/Social/Quiet, merge, post, create agents, call models, read credentials, create a controller, modify the live SwarmChat broker, or change CANON.

## Run the negative suite

From any checkout:

```bash
PYTHONPATH=tools/telescope-r16/review python -S -B -m unittest discover -s tools/telescope-r16/review/tests -v
PYTHONPATH=tools/telescope-r16/review python -I -S -B -O -m unittest discover -s tools/telescope-r16/review/tests -v
```

The tests use only Python's standard library. They cover direct and two-edge transitive source aliases, shared priors and shocks, time embargo crossing, malformed/missing source metadata, protected bodies and caller-forged authority. On this local Python 3.13.5 build: **18/18 ordinary and 18/18 `-O` (`-S`) PASS**.

## Acceptance / rollback

- Keep as an additive child of the existing R16 draft until reviewers test a *trusted host-issued* lineage manifest and a genuine same-budget held-out dataset.
- Verify the exact file bytes and negative cases; synthetic family IDs are not Ariadne semantic equivalences or person identities.
- No new hosted actions or release depend on this checker. Removal is a clean revert of this module, its test file and this README.
- The existing R16 GitHub Actions pre-runner failure remains HOLD and is not fixed by this code.
