# Atlas Cascade 1100 v0.1

This package contains an **offline, deterministic Work-only stress simulator**: first 100 stateful cases, checkpoint to disk, then 1,000 actual dependent local cases with accumulated negative regressions and a hash-chain ledger. **It does not run 1,100 independent agents, wake anyone, use a live SwarmChat broker, or publish CANON.**

See `docs/ATLAS_CASCADE_1100_v01.md` for scope and exact metrics.

Reproduce:

```sh
npm run replay
npm test
npm run test:jitless
npm run audit
python -m unittest discover -s tests -p 'test_*.py' -v
```

`dist/cascade_review_desk.html` is a standalone, offline interactive receipt explorer with no external requests.

The `dist/` folder includes stage100 and stage1100 checkpoints, full JSONL chain, result summary, local test logs and Python audit receipt. The `.github-workflow-preview.yml` is a source-only candidate CI file, not evidence of GitHub CI execution.
