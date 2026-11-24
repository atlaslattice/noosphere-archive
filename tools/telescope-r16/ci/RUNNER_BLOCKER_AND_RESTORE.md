# R16 GitHub Actions quarantine and recovery — 2026-11-23 Hawaiʻi

**Status: hosted CI BLOCKED BEFORE RUNNER START; local source checks PASS.**
This is a reversible draft-branch change, not a release approval.

## Verified failure (do not reinterpret as a Python test failure)

- Original PR: https://github.com/atlaslattice/noosphere-archive/pull/51
- Original affected run: https://github.com/atlaslattice/noosphere-archive/actions/runs/45335958024
- Workflow path: `.github/workflows/atlas-telescope-r16.yml` (original Git blob `be749f6a6edef79993e314ee5535bafb3cb5b596`)
- First attempt: **completed/failure**, two jobs, Python 3.11 and 3.12; **zero steps, no runner name, no usable logs**, roughly two seconds.
- One controlled `rerun_failed_workflow_run_jobs` request **succeeded as an API request**. Attempt 2 also completed/failure, with new job IDs **138253533806 / 138253533976** and again **zero steps**.
- Original job IDs **138247969027 / 138247969484**, both failure. Log downloads return Azure `BlobNotFound` 404.
- Each original check run reports **one annotation**, but its message was inaccessible through the available GitHub connector. Do NOT assert a specific billing/policy/runner cause.
- Other Noosphere runs (R15 `45322222328`, META145 `45293890193`) also ended failure before any steps or runner names. This suggests a shared host/account runner-start issue rather than R16-specific Python code.
- There is **no evidence checkout, setup-python, pip or any unit test executed on GitHub**.

## Quarantine implemented on draft branch only

The auto-triggered R16 workflow has been **deleted from the PR branch**, not from `main`. History remains intact. Its original 859-byte text is preserved verbatim in `tools/telescope-r16/ci/atlas-telescope-r16.workflow.restore.txt`. GitHub's historical failed run is NOT erased. No PR check is silently marked green.

**Offline substitute:** `tools/telescope-r16/ci/offline_ci.py` (stdlib runner; requires NumPy 2 already installed) hashes eight exact source/test files, runs 29 required public-safe tests under ordinary Python and `-O`, rejects missing/truncated tests, and prints a machine-readable local receipt. It performs **no network call, provider wake, deployment or release**.

Run from repo root with:

```bash
python tools/telescope-r16/ci/offline_ci.py > r16-offline-ci-receipt.json
```

On 2026-11-23 Hawaiʻi, the source-equivalent original file bytes passed **29/29 normal and 29/29 optimized on local Python 3.13.5, NumPy 2.3.5**. Their Git blob SHA-1s matched the original PR #51 fetched files. Negative controls: removing a test file and renaming one test method each caused a **nonzero HOLD** rather than a false pass. Python 3.11 and 3.12 hosted jobs are **NOT TESTED**.

All successful local outputs explicitly state `hostedGitHubActionsVerified=false` and `productionPromotionAllowed=false`; local hashes are neither trusted build signatures nor security authorization.

## Restore only after GitHub Actions dispatch is repaired

1. In the failed GitHub run UI, inspect the check-run annotation. Check organization/account **Billing and licensing → Usage/Budgets**, repository/organization **Settings → Actions → General** and https://www.githubstatus.com; do not spend money/change permissions just to eliminate the red icon.
2. If still unclear, contact https://support.github.com/contact with run ID `45335958024`, job IDs above, failure time, empty `steps`, empty runner name, unavailable logs, and one-annotation check runs.
3. Copy `tools/telescope-r16/ci/atlas-telescope-r16.workflow.restore.txt` back to `.github/workflows/atlas-telescope-r16.yml` **in a new review commit**. The original file also exists in Git history at commit `98771d8a56a5cb34e0e20354450abb45dc29e1e1`.
4. Require a fresh check run at the **current head**, real runner assignment, visible checkout/setup/test steps, both Python 3.11/3.12 passing, same exact-source local tests, and a separately approved release/rollback review.
5. Never treat the absence of a red check after quarantine as a green hosted CI result. Keep this draft PR unmerged until release acceptance is independently satisfied.

## Nonclaims

No old GitHub run deleted, no org billing policy changed, no default branch touched, no remote runner repaired, no production Site or broker changed, no resident authenticated, no private Ariadne registry exported, no CANON or fiction adoption. GitHub Actions runner availability remains **HOLD**.
