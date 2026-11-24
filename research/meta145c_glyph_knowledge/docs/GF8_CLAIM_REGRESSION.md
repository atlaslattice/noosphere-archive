# Reproducible GF8 claim and refresh regressions

The repair already exists in Noosphere PR41. This follow-up adds its missing public regression suite without changing the repair or merging the independent memory-checkpoint stack.

| Source | Exact Git identity | Result in the same 16-test suite |
| --- | --- | --- |
| PR39 original | commit `343778241425502a746aed292b65e47a951fdf74`, reasoning-filter blob `899b288753c7188e259a8cc11683e66c161ec6e7` | 11 pass, 4 fail, 1 error |
| PR41 repaired | commit `6ea414d8d353f614a39f61a50b0787a61eb65227`, reasoning-filter blob `004864ace8d51f1cc809cb8a9dafdcd17bf7718a` | 16 pass |

Unlike the earlier isolated handoff's dependency stubs, this suite uses the existing real GF8 `Plate`, mode calculation, context builder and SQLite review memory. These remain local analytic calculations, not physical measurements or hosted authorization.

## Observed defects reproduced

1. A NaN model claim passed numerical parity because comparisons against NaN were false.
2. An oversized integer raised `OverflowError` instead of producing the numerical hold.
3. Review-tip refresh re-sealed a modified frequency with a new valid self-hash.
4. Review-tip refresh re-sealed modified authorization metadata.
5. Review-tip refresh accepted a packet whose original receipt was removed.

The existing PR41 finite-number guard and pre-refresh receipt validation fix these cases. The remaining controls cover infinities, boolean/string/far frequencies, scientific-grade inflation, unsupported authority claims, legitimate immutable refresh, corrupted memory and all existing nonclaims.

## Replay

From this package directory, the repaired source runs with:

```sh
python tests/replay_pr41_regression.py
python -O tests/replay_pr41_regression.py
python -m unittest discover -s tests -v
python -O -m unittest discover -s tests -v
python -m unittest discover -s tests_public -v
python -O -m unittest discover -s tests_public -v
```

To reproduce the exact historical failures, from the repository root:

```sh
git show 343778241425502a746aed292b65e47a951fdf74:research/meta145c_glyph_knowledge/src/reasoning_filter.py > /tmp/atlas_gf8_pr39_reasoning_filter.py
python research/meta145c_glyph_knowledge/tests/replay_pr41_regression.py --source-file /tmp/atlas_gf8_pr39_reasoning_filter.py
```

That command intentionally exits unsuccessfully on the original source. The focused suite has 16 distinct cases; the full GF8 suite has 69 (53 inherited plus 16 new), and the unchanged META145C public suite has 48. Running them with and without `-O` exercises the same cases twice and is not counted as new functionality.

## Remaining boundary

The packet receipt is a self-hash, not a signature or host authority. `with_local_review_tip` in this independent PR41 stack still checks only its local chain; the separately reviewed checkpoint migration must be integrated by the publisher before claiming rollback freshness. Actual READ/RETURN revocation, source custody, physical calibration and hosted performance remain separate. No CANON or source-coordinate changes occur here.
