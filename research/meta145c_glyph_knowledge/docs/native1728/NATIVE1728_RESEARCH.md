# Native1728: selected open-source integration findings

Research date: November 23, 2026, Pacific/Honolulu.

## Completed implementation

The source-backed improvement implemented in this work is an adaptation of Eigent's tool replay classification into Atlas. The Python module is `src/beast20/tool_policy.py`; the native JavaScript mirror is `lib/native1728-tool-policy.mjs` in the companion SwarmChat host. The policy has four effects: read-only, idempotent write, non-idempotent write, and internal child launch. It returns bounded retry decisions and dispatches one registered attempt at a time.

The adaptation uses Eigent revision `9840d8aeb304b4af62838331a35c818f128a7be9`, `backend/app/run_policy.py`, Git blob `96186890d6f02cb022d84c7f22b454d0b9a84605`. The source portions are `ToolSafetyClass` and `automatic_tool_replay_allowed` (upstream lines 115–130 for the function). The original four-way replay distinction is retained; Atlas adds finite counters, deadlines, input validation, immutable server registration, dispatch/return authorization, detached results, and explicit uncertain outcomes.

The repo includes an Apache-2.0 license copy and modification/attribution notice under `docs/native1728/`. This is actual adapted source, not merely a design citation. The remaining reviewed frameworks are references or optional dependencies unless separately integrated by the parent build.

## Native host contract

Use the existing authenticated SwarmChat MCP server and its installed SDK convention. A native MCP tool can expose local/host computations to ChatGPT without adding a direct model API client. Define focused actions with explicit inputs, structured output schemas, stable result identifiers and accurate annotations. Request authorization belongs in the server; metadata hints do not confer authority.

The present OpenAI plugin documentation favors `_meta.ui.resourceUri` for optional MCP Apps UI resources; `openai/outputTemplate` remains a compatibility alias. Keep useful summaries in `structuredContent` and `content`. Component-only `_meta` is neither a permission grant nor secure secret storage.

Primary sources:
- https://developers.openai.com/plugins/build/mcp-server
- https://developers.openai.com/plugins/reference
- https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- https://modelcontextprotocol.io/specification/2025-11-25/basic/transports

For the protocol transport, use the existing Streamable HTTP path. A client accepts JSON and event-stream responses. Keep protocol errors distinct from executed tool failures; the latter use `isError` with actionable, bounded information. Maintain actual host authorization and origin validation.

## Source and dependency selection

The machine-readable `NATIVE1728_OSS_LEDGER.json` records ten immutable repository pins, inspected files and blob hashes, license evidence, adoption decisions and twelve integration recommendations. This is a selected survey, not a claim to cover every open-source platform. Mutable upstream observations below describe the pinned research snapshot; later repository state may differ.

Two current-source surprises matter:
- MCP TypeScript SDK main is in an Apache-2.0/MIT licensing transition, with separate documentation terms. Do not describe the entire current repository as MIT.
- Microsoft AutoGen is archived. Its root documentation license is CC-BY-4.0 while implementation code has a separate MIT `LICENSE-CODE`. Use exact files and their terms.

LangGraph's useful architectural distinction is run-scoped checkpoints versus longer-lived stores. Its durable replay restores completed task results but an interrupted task may execute again; this supports explicit idempotency/reconciliation boundaries. The current BEAST20 executor can retain those boundaries without adding a second graph engine.
- https://docs.langchain.com/oss/python/langgraph/persistence
- https://github.com/langchain-ai/docs/blob/main/src/oss/langgraph/functional-api.mdx

OpenManus supplies explicit plan progress and executor selection, but its outer planning flow invokes models. Only progress/state machinery is a suitable credential-independent adaptation. Eigent additionally offers run-state and semantic-event references. DuckDB is an optional analytical/reporting adapter; its own tuning guide distinguishes large analytical workloads from many small concurrent operations, so replacing SQLite receipts without measurement is not supported.
- https://duckdb.org/docs/guides/performance/how-to-tune-workloads

## Integration limits

The host must supply trusted identity/rights and attempt counts from durable receipts. Request-provided counters, names, effect declarations or idempotency keys do not prove history or authorization. A keyed write is replay-safe only if the registered remote implementation actually enforces idempotency. Neither module claims exactly-once remote execution.

Python accepts cooperative async handlers and queues admission inside a deadline. JavaScript rejects full admission as `NOT_EXECUTED`, and unresolved calls retain slots until settlement. JavaScript cannot preempt a synchronous event-loop block; Python async timeouts cannot guarantee remote cancellation. Python receipts include implementation-local hashes; the JS mirror leaves cross-runtime receipt hashing to the host.

No model API was called. No API credential was inspected or created. No production service was changed by this workstream.
