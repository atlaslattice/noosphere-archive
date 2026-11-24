"""Explicit local CLI; no hidden worker, provider call, or background schedule."""
from __future__ import annotations

import argparse
import asyncio
from hashlib import sha256
import json
from pathlib import Path

from ..core import SourceSnapshot
from ..gf8 import Plate, mode_hz
from ..glyph import REGISTRY_SHA
from ..memory import LocalMemory
from .execution import AsyncExecutor
from .feeds import FeedPoller, PublicHTTPTransport
from .runtime import AtlasBeastRuntime, CascadeCompiler
from .storage import ArtifactStore, Scope


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    demo = sub.add_parser("demo", help="Run local verified-memory and physics-reuse demo")
    cascade = sub.add_parser("cascade", help="Run the original source-pinned 1,885-job circuit")
    cascade.add_argument("--registry", type=Path, required=True)
    cascade.add_argument("--topics", type=Path)
    cascade.add_argument("--state", type=Path, required=True)
    cascade.add_argument("--node-inputs", type=Path)
    feed = sub.add_parser("feed", help="Explicit bounded public-source refresh")
    feed.add_argument("--url", required=True)
    feed.add_argument("--host", required=True)
    feed.add_argument("--state", type=Path, required=True)
    feed.add_argument("--allow-network", action="store_true", required=True)
    feed.add_argument("--query")
    strategy = sub.add_parser("strategy-summary", help="Verify and inspect a completed 1,728-strategy report")
    strategy.add_argument("--report", type=Path, required=True)
    evolution = sub.add_parser("evolution-summary", help="Verify and inspect a completed source-bound long-horizon report")
    evolution.add_argument("--report", type=Path, required=True)
    evolution_bundle = sub.add_parser("evolution-bundle", help="Verify and export a completed long-horizon report for a native host")
    evolution_bundle.add_argument("--report", type=Path, required=True)
    evolution_bundle.add_argument("--output", type=Path, required=True)
    federation = sub.add_parser("federation", help="Delegate to explicitly configured source-pinned Atlas packages")
    federation.add_argument("--config", type=Path, required=True)
    federation.add_argument("--component", choices=("excellence", "gf9", "unified"))
    federation.add_argument("--action")
    federation.add_argument("--arguments", type=Path)
    args = parser.parse_args()
    if args.operation == "demo":
        scope = Scope(REGISTRY_SHA, "ariadne-reader/v0.7", "local-synthetic-demo", 1)
        with ArtifactStore() as store:
            runtime = AtlasBeastRuntime(scope, store, lambda *_: True)
            memory = LocalMemory(":memory:")
            try:
                runtime.verified_memory(memory, ["H01.S01.N01"], expected_tip="0" * 64, expected_count=0)
                plate = Plate()
                packets = [runtime.reasoning_context(hsn=f"H01.S01.N{i:02d}",
                    gf7=f"GF7.B01.M01.C{i:02d}", plate=plate,
                    drive_hz=mode_hz(plate, 1, 1), grid=17, max_mode=4) for i in range(1, 13)]
                result = {"status": "LOCAL_DEMO_COMPLETED", "contexts": len(packets),
                          "stats": dict(runtime.stats), "network_requests": 0,
                          "model_calls": 0, "hosted_authorization_proven": False}
            finally:
                memory.close()
    elif args.operation == "cascade":
        snapshot = SourceSnapshot(args.registry, args.topics)
        args.state.mkdir(parents=True, exist_ok=True)
        scope = Scope(snapshot.registry_sha, "ariadne-reader/v0.7", "owner-local-cascade", 1)
        inputs = json.loads(args.node_inputs.read_text()) if args.node_inputs else None
        compiler = CascadeCompiler(snapshot)
        with ArtifactStore(str(args.state / "objects.sqlite")) as store:
            runtime = AtlasBeastRuntime(scope, store, lambda *_: True)
            with AsyncExecutor(args.state / "tasks.sqlite", compiler.handlers(), scope_key=scope.key) as executor:
                graph = asyncio.run(runtime.run_cascade(compiler, executor, inputs))
                result = {"status": "LOCAL_CASCADE_COMPLETED" if graph.succeeded else "LOCAL_CASCADE_INCOMPLETE",
                          "source_sha256": snapshot.registry_sha, "stats": graph.stats,
                          "meta": graph.outputs.get("META145"), "model_calls": 0,
                          "hosted_authorization_proven": False}
    elif args.operation == "strategy-summary":
        from .strategy_lab import compact_summary
        result = compact_summary(json.loads(args.report.read_text(encoding="utf-8")))
    elif args.operation in {"evolution-summary", "evolution-bundle"}:
        from .long_horizon import report_summary, export_bundle
        report = json.loads(args.report.read_text(encoding="utf-8"))
        if args.operation == "evolution-summary":
            result = report_summary(report)
        else:
            bundle = export_bundle(report)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(bundle, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
            result = {"status": "VERIFIED_BUNDLE_EXPORTED", "reportSha256": bundle["reportSha256"]}
    elif args.operation == "federation":
        from .federation import PinnedFederation
        config = json.loads(args.config.read_text(encoding="utf-8"))
        allowed = {"inventory", "roots", "plan_path", "expected_plan_sha256", "registry_path", "topics_path"}
        if type(config) is not dict or set(config) - allowed or not {"inventory", "roots"} <= set(config):
            raise ValueError("FEDERATION_CONFIG_INVALID")
        inventory = json.loads(Path(config.pop("inventory")).read_text(encoding="utf-8"))
        with PinnedFederation.from_inventory(inventory, **config) as mounted:
            if args.component:
                if not args.action:
                    raise ValueError("FEDERATION_ACTION_REQUIRED")
                arguments = json.loads(args.arguments.read_text(encoding="utf-8")) if args.arguments else {}
                result = mounted.call(args.component, args.action, arguments)
            else:
                if args.action or args.arguments:
                    raise ValueError("FEDERATION_COMPONENT_REQUIRED")
                result = mounted.status()
    else:
        args.state.mkdir(parents=True, exist_ok=True)
        scope = Scope(sha256(args.url.encode()).hexdigest(), "public-feed/v1", "owner-local-feed", 1)
        transport = PublicHTTPTransport({args.host})
        poller = FeedPoller(str(args.state / "feeds.sqlite"), allowed_hosts={args.host},
                            transport=transport, authorize=lambda *_: True)
        try:
            with ArtifactStore(str(args.state / "objects.sqlite")) as store:
                runtime = AtlasBeastRuntime(scope, store, lambda *_: True)
                result = runtime.refresh_public_feed(poller, args.url)
                if args.query:
                    result["search_hits"] = [{"id": row["id"], "score": row["score"],
                                              "source_digest": row["source_digest"]}
                                             for row in runtime.search_public(args.query)]
                result["hosted_authorization_proven"] = False
        finally:
            poller.close()
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
