# Noosphere Archive

Source contracts, public repository metadata and historical reference material for the Atlas ecosystem.

**Start with the local software below.** The repository contains runnable validators and tests; the archived records retain their own dates, provenance and review status. A source contract or passing local test does not establish a hosted service, identity, permission or release approval.

## Find what you need

| I want to… | Start here |
| --- | --- |
| Understand SwarmHub's review and preservation contracts | [SwarmHub contracts](docs/SWARMHUB_CONTRACTS_v01.md) and [implementation](core/swarmhub_contracts.py) |
| Find public Atlas repository pointers | [Registry guide](registry/README.md) |
| Validate a synthetic archival context bundle | [Digital continuity specification](specs/digital-continuity-protocol-v0.md) and [public-safety scope](docs/public-safety-disclaimer.md) |
| Follow a pinned Atlas engineering program | [EX1728 source port](docs/EXCELLENCE_1728_SOURCE_PORT.md) |
| Follow the optional Civilization R01 kernel reference | [Source-reference guide](docs/CIVILIZATION_R01_SOURCE_REFERENCE.md) |
| Make a focused change or report a problem | [Contributing](CONTRIBUTING.md) |

## Run the local checks

Use Python 3.11 or later from the repository root. These commands use the Python standard library; no package installation, provider account or API key is needed.

```bash
python -m unittest discover -s tests -v
python -m registry.public_registry
python -m core.digital_continuity
```

The first command runs the repository's Python test suite. The other two validate the checked-in public registry and synthetic continuity examples. They do not fetch private source material, contact a model provider or deploy anything.

To inspect one registered public pointer:

```bash
python -m registry.public_registry --lookup atlaslattice/noosphere-archive
```

See [focused check commands](CONTRIBUTING.md#run-the-relevant-checks) when changing a single component. GitHub Actions results are available in the [Actions tab](https://github.com/atlaslattice/noosphere-archive/actions); inspect the run attached to the exact commit under review.

## Repository map

| Path | Purpose |
| --- | --- |
| [`core/`](core/) | Python review contracts and pinned source-reference adapters |
| [`registry/`](registry/) | Dated public repository metadata, validator and source-reference records |
| [`schemas/`](schemas/) | JSON contracts for artifacts and synthetic continuity examples |
| [`examples/`](examples/) | Redacted synthetic fixtures used by the continuity checks |
| [`tests/`](tests/) | Offline Python regressions |
| [`tools/`](tools/) | Evidence-contract comparison utilities |
| [`docs/`](docs/) | Component guides, policy records and dated reviews |
| `archive/`, `orc/`, `00_Council_Logs/`, `DailyOS/`, `snrs/` | Historical source and edition records; consult their own provenance before reuse |

Historical files stay at their original paths. New guides provide navigation; they do not supersede an edition, ratify a proposal or discard an objection.

## Understand the evidence

Report these separately: **source present**, **locally tested**, **CI passed for an exact commit**, **merged**, and **deployed with hosted verification**. An open pull request can contain useful tested work while remaining a candidate. Public metadata is a discovery pointer, not permission to ingest a repository's contents.

For code and documentation changes, use the [contribution guide](CONTRIBUTING.md). It explains small reviewable patches, reproducible checks and how to preserve source rights and historical records.
