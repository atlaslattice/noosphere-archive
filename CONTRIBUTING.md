# Contributing to Noosphere Archive

Make a focused, reversible improvement and leave enough evidence for someone else to check it.

## Choose the right surface

1. Search [open issues](https://github.com/atlaslattice/noosphere-archive/issues) and [open pull requests](https://github.com/atlaslattice/noosphere-archive/pulls) for overlapping work. Read the original acceptance criteria and any dependency or companion-PR notes.
2. Start from the current target branch. Record its commit and the branch being reviewed with `git rev-parse HEAD`.
3. Keep code, tests and the relevant component guide together. Put broader research or historical editions in their existing source location with explicit provenance; do not rewrite an old record to make a new result appear historical.

## Run the relevant checks

Run commands from the repository root with Python 3.11 or later. The current Python suite needs only the standard library.

| Change | Check |
| --- | --- |
| Any Python contract or shared input | `python -m unittest discover -s tests -v` |
| Public registry | `python -m registry.public_registry` and `python -m unittest discover -s tests -p 'test_public_registry.py' -v` |
| Synthetic digital continuity | `python -m core.digital_continuity` and `python -m unittest discover -s tests -p 'test_digital_continuity.py' -v` |
| SwarmHub contracts | `python -m unittest discover -s tests -p 'test_swarmhub_contracts.py' -v` |
| Contract comparison | `python -m unittest discover -s tests -p 'test_contract_crosswalk.py' -v` |
| EX1728 source reference | `python -m unittest discover -s tests -p 'test_excellence_source_port.py' -v` |
| Civilization R01 reference | `python -m unittest discover -s tests -p 'test_civilization_kernel_*.py' -v` |

For a behavior change, include a positive example and a regression or negative case that demonstrates the failure being fixed. For a documentation-only change, verify the referenced paths and commands; do not invent a test count.

The existing workflows are [SwarmHub contracts](.github/workflows/swarmhub-contracts.yml), [public registry](.github/workflows/public-repo-registry.yml) and [digital continuity](.github/workflows/digital-continuity-v0.yml). Their triggers select particular changed paths. A missing run is not a pass, and a local result is not a GitHub Actions result. Retain exact commit, run and job links when reporting CI evidence.

## Prepare a useful pull request

Explain the problem, the resulting behavior, the source issue and any dependency PR. List the commands actually run, their outcomes and the Python version. If something is blocked, state the missing evidence and the concrete next action.

Preserve original sources, dissent, edition pins and attribution. Use a follow-up correction or explicit supersession relationship instead of silently replacing history. Keep unrelated cleanup out of the same patch.

Avoid automatic closing keywords for partially satisfied or shared acceptance criteria. A stacked or companion PR should name its intended parent and what remains unresolved. Merge, release and deployment decisions require their own applicable acceptance evidence.

## Source and publication boundaries

Use synthetic or explicitly authorized Work inputs. Do not include credentials, personal information, private room transcripts, revoked material, or protected Play, Social, Imagine, Dream, Quiet, Habitat, Brain or Palace bodies in an issue, test fixture or public patch.

Public visibility does not establish reuse rights. Preserve each artifact's existing license and attribution, and verify permission before copying third-party content. This repository has no root license file at the reviewed base; this guide does not grant a new license or relicense historical material.

For a suspected sensitive-data exposure, share the affected path and minimal context through an already authorized private channel to the owner. Do not reproduce the sensitive value in a public issue.

## Report a problem

Use the bug template for a reproducible failure or the work-item template for a bounded improvement. Include the exact path and commit, expected and observed behavior, and a small safe example. Source and permission limits belong in the report when they affect reproduction.
