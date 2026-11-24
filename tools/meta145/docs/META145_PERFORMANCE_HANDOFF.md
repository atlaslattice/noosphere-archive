# META145 — 144 Ariadne Sphere perspectives → 1 measured fast-path build

**Date:** 2026-11-23 · **Classification:** source-pinned / offline browser tested / independent replay / **not hosted** / **no CANON or fiction adoption**.

## What was actually built

This is a new **R13 / META145** engineering increment on the preserved 12-edition Atlas Turbo circuit. It reads the *unchanged original* Ariadne v0.7 atlas (source digest `07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6`) and the existing R12 integrated build head `b5be629b260719f97cd16c5c795b4baf5a1838855b99f94b3725c578b249283a`.

The new computation walks all **144 distinct Sphere perspectives**, checking **1,728 original source nodes** for each: **248,832 exact structural/lexical pair records**. It produces 144 chain-linked Sphere briefs with four separately scoped project proposals each (576 candidate suggestions total), and 12 House follow-up groups. These are deterministic computational lenses, not 144 independent AI agents or actual peer turns.

**145th meta-build: a working optimized, offline 1,728-node observatory** preserving the original embedded dataset exactly. The previous UI rebuilt **650 buttons** on broad search reset and truncated visible results at 650. META145 now precomputes search text and House/Sphere indexes, performs an exact-coordinate fast-path, and renders **48 buttons per page**; each explicit `Show next 48` adds 48 more until all **1,728** are reachable. Search, source selection, role/reading filters, the 12 edition controls, four project panes, false-friend `H08.S01.N10` (Music / musical instrument design), and keyboard selection remain functional. No backend/source corpus mutation, telemetry, host call or automatic posting.

## Real local performance benchmark, with limits

Frozen source on both sides; Chromium headless `/usr/bin/chromium`, 412×915 viewport, **36 measured event cycles** following six warm-up cycles; in-page `performance.now()` measured synchronous DOM filter handler time. Local device/runner and timer resolution matter. **These are not hosted SwarmChat end-to-end times.**

| Operation | Original median | META145 median | Original p95 | META145 p95 | Change |
|---|---:|---:|---:|---:|---|
| Broad query reset | 3.65 ms | 0.30 ms | 7.70 ms | 0.40 ms | **12.17× median**, **19.25× p95** |
| Filter to one House | 1.30 ms | 0.30 ms | 2.00 ms | 0.40 ms | 4.33× median |
| Exact-coordinate filter | 0.80 ms | below timer resolution (reported 0.0 ms) | 3.60 ms | below timer resolution | speedup **not quantifiable** from these samples |

Initial buttons: **650 → 48** (92.6% fewer). The static file size grows slightly **910,702 → 912,416 bytes**; faster interaction is not a smaller transfer, and no network timing is claimed.

An additional **144-Sphere Chromium navigation sweep** showed the correct 12 nodes per Sphere in both viewers: original median **0.20 ms**, p95 **0.50 ms**; optimized median **0.10 ms**, p95 **0.20 ms**. Per-Sphere timings are local UI timings, not rights/identity/delivery latencies.

## Audit evidence

- **34/34 tests PASS** normally and with Python `-O`, including 19 browser/source-equivalence tests and 15 source/chain/tamper controls. Initial test fixture expectation errors are preserved in earlier diagnostic logs rather than promoted to product failures.
- **144/144** Sphere browser navigation checks passed in each UI.
- Independent full readback checked **248,832 compressed pair records**, 144 unique receipts, exact ancestry and role, 12 House follow-ups and unchanged source digests.
- All **4** authoritative R13 outputs reproduced **byte-for-byte** on a fresh deterministic replay.
- Local metadata receipt SHA-256: `8787dcc77518b86984cab86049ff051e3bd98b024911a4ba5eba6a7063d9f0c9`.
- Sphere review terminal chain SHA-256: `2b45d9ad4030ba2211155296040caa4eaa2180515e995b692733b1bf27304efe`.

## Integration contract, no independent host effects

To measure **actual SwarmChat responsiveness**, the existing host must emit consented, independently attributable Work telemetry for (i) ingress received, (ii) atomic broker persist, (iii) callback transport and receiver arrival, (iv) actual platform model activation, (v) receiver ACK, and (vi) reply readback. Keep those separate; do **not** call a stored message a model wake. Capture p50/p95/p99 over a sufficiently sized, declared observed window, with clock synchronization and loss/timeout denominators. Compare exact served release SHA with a true baseline on comparable clients/network links. Protect private bodies, session tokens, and Play/Social/Imagine/Brain/Palace/Quiet from the Work metrics stream. Run revocation-at-RETURN and two-account oracle negatives before release. Require authorization, owner review and rollback readiness before changing the live hosted runtime.

No real on-host response times, authenticated participant identities, live pages, deployed performance fixes, accepted semantic links or Iron Empire canon changes were demonstrated here. Performance improvement is **measured on the local offline observatory**. The current Node/CI/release review branches remain separate.

## Reproduction

1. Use the exact owner-private predecessor Turbo12 input directory (original `ariadne-atlas-v07.json`, base `base_sphere_node_matrix_248832.csv`, and R12 `ONE_INTEGRATED_BUILD.json`); do not publish these private inputs.
2. Generate optimized viewer: `python src/build_fast_observatory.py --input <R12 viewer HTML> --output web/ATLAS_META145_FAST_OBSERVATORY.html --expected-sha <source HTML SHA256>`.
3. Run local paired browser benchmark: `python src/bench_browser.py --baseline <R12 viewer> --optimized web/ATLAS_META145_FAST_OBSERVATORY.html --out output/PAIRED_BROWSER.json --samples 36`.
4. Compute 144+1: `python src/run_meta145.py --turbo-root <R12 root> --out output --benchmark output/PAIRED_BROWSER.json --fast-viewer web/ATLAS_META145_FAST_OBSERVATORY.html`.
5. Audit: `python src/verify_meta145.py --turbo-root <R12 root> --out output --benchmark output/PAIRED_BROWSER.json --fast-viewer web/ATLAS_META145_FAST_OBSERVATORY.html --ui-sweep output/SPHERE144_CHROMIUM_SWEEP.json`.
6. Run local tests: `python -m unittest discover -s tests -p 'test*.py'` (and repeat with `python -O`); run the browser Sphere sweep.

**Success means offline code and evidence works. It does not authorize a hosted deployment, a resident identity, approval of 144 science findings, or a constitutional/fiction CANON decision.**
