# Atlas OneBuild R15 — source-pinned adaptive detail renderer

**Review-only source. Not merged, installed on SwarmChat, or independently host-attested.**

This additive candidate patches the existing owner-held OneBuild R14 offline HTML viewer after checking an **exact SHA-256 source pin**. It does not include that private viewer, original Ariadne registry, private Work messages, Iron Empire text or raw 1,728-node benchmark records.

## Scope
- Replace initial construction of 1,728 node-detail profiles with a 96-profile bounded on-demand FIFO cache. This retains the full source index in memory and all coordinates remain addressable.
- Update invariant project note DOM content once; change edition text only when the selected edition changes.
- Preserve eager keyword indexing because the tested deferred-index variant hurt first-search latency.
- Keep an explicit label on R14 historical metrics; R15 measurements are separate.
- Reject changed source bytes and missing/modified renderer/search anchors, including with Python -O. No cache admission, authentication, Work posting, provider wake, deployment or CANON authority is added.

## Source pins
- R14 input SHA-256: b750e56445e0dd05c7a5b6a1294e9df84bf01577128a586f938289b85bf9b3ac
- R15 local output SHA-256: 3fd74921bded4da9c81fb1e68d3245df4df1fde9c18ea1fca83d55a6761cac3e

## Reproduction
With the owner's separate, correctly pinned source file:

\`\`\`bash
python tools/onebuild-r15/src/build_adaptive.py R14_PINNED_BASELINE.html R15_CANDIDATE.html
python -m unittest discover -s tools/onebuild-r15/tests_public -p 'test_*.py'
python -O -m unittest discover -s tools/onebuild-r15/tests_public -p 'test_*.py'
\`\`\`

**Actual local verification:** 23/23 owner-file and Chromium tests, 12/12 portable synthetic tests in normal and optimized Python. Original embedded node and metric datasets unchanged, 1,728 exact node-detail text comparisons passed, 144 Sphere filters and 12 editions preserved.

**Performance, local Chromium only:** median script startup 30.45→27.25 ms in one 20-sample paired run, ~1.12× faster; median paired handler throughput 1.75× and 1.67× faster in two separate full-node, reversed-order runs. 1,528 nodes cleared gain margin in both; 2 recurring noisy regressions were nonreproducing in focused 1,200-repeat retests. Individual node microsecond measurements are not statistically established gains. No hosted latency, paint, resident activation, real permissions or release approval was measured.

The full owner-private package has the original byte-pinned baseline, R15 viewer, 1,728-node metrics, positive and negative experiments and rollback artifacts. Keep human review and publisher verification separate.
