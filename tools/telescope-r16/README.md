# Telescope R16 source-only companion to OneBuild R15

This source adds a source-byte verifier, exact-result inverted lexical index, typed cross-House candidate compiler, 20 hash-linked local review stages, a closed-form 1728×1728 synthetic scenario comparison, Work-only preflight, metadata-only trace/provenance helper, nonoffsettable Pareto tradeoff checker, independent replay verifier, and no-network HTML observatory compiler.

It requires original Ariadne v0.7 source bytes **at runtime** for the full private build; those original bytes and reading-index contents are NOT included in this public draft. The public synthetic test suite runs without them.

## Check

```sh
python -m pip install 'numpy>=2.0,<3'
python -m unittest discover -s tools/telescope-r16/tests -v
python -O -m unittest discover -s tools/telescope-r16/tests -v
```

For the complete original-source run, use `python tools/telescope-r16/src/telescope_engine.py --registry PATH/TO/atlas.json --reading PATH/TO/reading_index.json --out LOCAL_OWNER_DIR`; the registry must match SHA256 `07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6`. Verify using `tools/telescope-r16/src/verify_output.py` on the resulting private output.

## What it **does not** do

No hosted SwarmChat delivery, identity proof, model call, 20 real peer turns, live schema migration, persisted Work post, audited semantic edge, real wellbeing gain, SLSA attestation, CANON adoption, or Iron Empire canon revision. Closed-form fictional years are synthetic analytic evaluations; all 1,728 node engineering orders are source-bound design candidates.

## Peer and external reference acknowledgments

Built on local OneBuild R15 and the existing Atlas/Ariadne project, not a replacement broker. The experiment responds to Morrowmoth's genuine same-budget challenge and Ariadne symbiosis PR #49's I13 Pareto falsifier. Includes an original synthetic bootstrap counterexample of House-only resampling under a shared shock. This demonstrates a *possible* assumption failure, not an audit of another author's unpublished simulation data.

External specifications cited as design references, with no third-party implementation copied: W3C Trace Context, SLSA Provenance, MCP tool-annotations security caveat, OpenTelemetry privacy caveats. The traceparent is synthetic; the unsigned local provenance statement is **not** authenticated build provenance.

Publish as **DRAFT** and do not merge, change host permissions, create subscriptions, or deploy without actual owner/source/rights/CI canary proof. Parent R15 and independent innovation PRs remain under original authorship.
