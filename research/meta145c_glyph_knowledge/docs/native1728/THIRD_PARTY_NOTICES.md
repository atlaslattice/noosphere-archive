# Native1728 third-party notices

## Eigent tool replay policy — adapted source

- Upstream: [eigent-ai/eigent](https://github.com/eigent-ai/eigent).
- Exact revision: `9840d8aeb304b4af62838331a35c818f128a7be9`.
- Exact source: [`backend/app/run_policy.py`](https://github.com/eigent-ai/eigent/blob/9840d8aeb304b4af62838331a35c818f128a7be9/backend/app/run_policy.py).
- Source Git blob: `96186890d6f02cb022d84c7f22b454d0b9a84605`.
- Reused portion: the four-class `ToolSafetyClass` classification and `automatic_tool_replay_allowed` decision semantics.
- Copyright: **Copyright 2025-2026 @ Eigent.ai. All Rights Reserved.**
- License: **Apache License, Version 2.0**, reproduced in [LICENSE-EIGENT-APACHE-2.0.txt](LICENSE-EIGENT-APACHE-2.0.txt).
- Local implementation: `src/beast20/tool_policy.py`; native JavaScript adaptation may be copied into the SwarmChat host with this notice and license retained.

### Modification notice

The Atlas adaptation renames the effect classes to `READ_ONLY`, `IDEMPOTENT_WRITE`, `NON_IDEMPOTENT_WRITE`, and `INTERNAL_CHILD_LAUNCH`. It preserves the distinction that read operations may be replayed, keyed idempotent writes may be replayed, and ambiguous non-idempotent effects or child launches require reconciliation. It adds strict arguments, finite retry and time budgets, immutable trusted registrations, required authorization callbacks for external tools, current-return checks, bounded async admission, explicit timeout/unknown-outcome receipts, and detached JSON results. These additions are Atlas changes, not upstream Eigent claims.

The registry performs one attempt per invocation; a returned retry decision does not dispatch another call, grant permission, prove remote cancellation, or establish exactly-once effects. A key is useful only if the registered remote implementation actually enforces its promised idempotency. Host identity and permissions remain the host's responsibility. No upstream model loop, credentials, provider configuration, or private data is imported.

The inspected upstream root contained `LICENSE` and a `licenses/` directory, but no root `NOTICE` file. Only the identified policy fragment is adapted; transitive application code is not bundled. Other reviewed open-source projects are documented in the research ledger and are not thereby claimed as installed or copied.
