"""Behavioral tests for the integrated Work-job executor; no model/network jobs."""
import asyncio
from graphlib import CycleError
import json
from pathlib import Path
import tempfile
import unittest

from src.beast20.execution import AsyncExecutor, TaskSpec


class ExecutionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "execution.sqlite"
        self.executors = []

    def tearDown(self):
        for executor in self.executors:
            executor.close()
        self.tmp.cleanup()

    def executor(self, handlers=None, **kwargs):
        executor = AsyncExecutor(
            self.path, handlers or {"echo": lambda payload, parents: payload},
            scope_key=kwargs.pop("scope_key", "a" * 64), **kwargs)
        self.executors.append(executor)
        return executor

    async def test_dag_dependencies_and_cache(self):
        calls = []
        def add(payload, parents):
            calls.append(payload)
            return payload + sum(parents.values())
        executor = self.executor({"add": add}, workers=2)
        tasks = [TaskSpec("a", "add", 3), TaskSpec("b", "add", 5, house="H02"),
                 TaskSpec("sum", "add", 1, dependencies=("a", "b"))]
        first = await executor.run_graph(tasks)
        second = await executor.run_graph(tasks)
        self.assertEqual(first.outputs["sum"], 9)
        self.assertEqual(first.outputs, second.outputs)
        self.assertEqual(len(calls), 3)
        self.assertEqual(second.stats["cache_hits"], 3)
        self.assertTrue(first.succeeded)

    async def test_parallel_async_jobs_bounded(self):
        active, peak = 0, 0
        gate = asyncio.Event()
        async def work(payload, parents):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            if active == 3:
                gate.set()
            await gate.wait()
            await asyncio.sleep(0)
            active -= 1
            return payload
        executor = self.executor({"work": work}, workers=3)
        result = await executor.run_graph([TaskSpec(f"job{i}", "work", i) for i in range(12)])
        self.assertEqual(peak, 3)
        self.assertEqual(result.stats["max_admitted"], 3)
        self.assertEqual(result.stats["max_active"], 3)
        self.assertEqual(len(result.outputs), 12)

    async def test_fair_house_rotation(self):
        order = []
        def record(payload, parents):
            order.append(payload)
            return payload
        executor = self.executor({"record": record}, workers=1)
        tasks = [TaskSpec(f"a{i}", "record", f"A{i}", house="H01") for i in range(4)]
        tasks += [TaskSpec(f"z{i}", "record", f"Z{i}", house="H12") for i in range(2)]
        await executor.run_graph(tasks)
        self.assertEqual(order[:4], ["A0", "Z0", "A1", "Z1"])

    async def test_duplicate_inflight_jobs_share_work(self):
        calls = 0
        async def slow(payload, parents):
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.01)
            return {"value": payload}
        executor = self.executor({"slow": slow}, workers=8)
        result = await executor.run_graph([TaskSpec(f"duplicate{i}", "slow", 42) for i in range(8)])
        self.assertEqual(calls, 1)
        self.assertEqual(result.stats["coalesced"], 7)
        result.outputs["duplicate0"]["value"] = 99
        self.assertEqual(result.outputs["duplicate1"], {"value": 42})

    async def test_concurrent_graphs_share_global_capacity_and_flights(self):
        calls, active, peak = 0, 0, 0
        async def slow(payload, parents):
            nonlocal calls, active, peak
            calls += 1
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.005)
            active -= 1
            return payload
        executor = self.executor({"slow": slow}, workers=2)
        graph = [TaskSpec(f"job{i}", "slow", i) for i in range(5)]
        a, b = await asyncio.gather(executor.run_graph(graph), executor.run_graph(graph))
        self.assertEqual(calls, 5)
        self.assertLessEqual(peak, 2)
        self.assertEqual(a.outputs, b.outputs)

    async def test_restart_suppresses_completed_jobs(self):
        calls = []
        handler = lambda value, parents: calls.append(value) or value
        first = self.executor({"handler": handler})
        await first.run_graph([TaskSpec("done", "handler", 1)])
        first.close()
        self.executors.remove(first)
        second = self.executor({"handler": handler})
        result = await second.run_graph([TaskSpec("done", "handler", 1),
                                        TaskSpec("new", "handler", 2, ("done",))])
        self.assertEqual(calls, [1, 2])
        self.assertEqual(result.stats["cache_hits"], 1)

    async def test_scope_version_input_and_parent_digest_invalidate(self):
        calls = []
        def total(payload, parents):
            calls.append(payload)
            return payload + sum(parents.values())
        executor = self.executor({"total": total})
        graph = [TaskSpec("source", "total", 1), TaskSpec("derived", "total", 2, ("source",))]
        await executor.run_graph(graph)
        changed = [TaskSpec("source", "total", 5), graph[1]]
        result = await executor.run_graph(changed)
        self.assertEqual(result.outputs["derived"], 7)
        self.assertEqual(result.stats["executed"], 2)
        version = await executor.run_graph([TaskSpec("source", "total", 5, version="2")])
        self.assertEqual(version.stats["executed"], 1)
        other = self.executor({"total": total}, scope_key="b" * 64)
        self.assertEqual((await other.run_graph(graph)).stats["cache_hits"], 0)

    async def test_failure_retries_then_succeeds_with_bounded_backoff(self):
        calls, delays = 0, []
        async def sleep(delay):
            delays.append(delay)
        def flaky(payload, parents):
            nonlocal calls
            calls += 1
            if calls < 3:
                raise OSError("transient")
            return "recovered"
        executor = self.executor({"flaky": flaky}, sleep=sleep, backoff_base=0.2,
                                 max_backoff=0.3, circuit_threshold=5)
        result = await executor.run_graph([TaskSpec("job", "flaky")])
        self.assertEqual(result.outputs["job"], "recovered")
        self.assertEqual(delays, [0.2, 0.3])
        self.assertEqual(result.stats["retries"], 2)

    async def test_dead_letter_is_durable_and_descendant_blocked(self):
        calls = []
        def fail(payload, parents):
            calls.append("fail")
            raise RuntimeError("never include secret request body in receipt")
        def child(payload, parents):
            calls.append("child")
        executor = self.executor({"fail": fail, "child": child}, circuit_threshold=5)
        tasks = [TaskSpec("bad", "fail", max_attempts=2),
                 TaskSpec("blocked", "child", dependencies=("bad",)),
                 TaskSpec("independent", "child", 12, provider="other")]
        result = await executor.run_graph(tasks)
        self.assertFalse(result.succeeded)
        self.assertEqual(calls.count("fail"), 2)
        self.assertEqual(calls.count("child"), 1)
        self.assertEqual(result.receipts["blocked"]["status"], "BLOCKED_DEPENDENCY")
        self.assertNotIn("secret", json.dumps(result.receipts))
        await executor.run_graph(tasks)
        self.assertEqual(calls.count("fail"), 2)

    async def test_circuit_half_open_recovery(self):
        now, failures = [100.0], [True]
        calls = []
        def provider(payload, parents):
            calls.append(payload)
            if failures[0]:
                raise ConnectionError("down")
            return payload
        executor = self.executor({"provider": provider}, clock=lambda: now[0],
                                 circuit_threshold=1, circuit_reset=5)
        first = await executor.run_graph([TaskSpec("a", "provider", 1)])
        self.assertEqual(first.receipts["a"]["status"], "DEFERRED_CIRCUIT")
        self.assertEqual(len(calls), 1)
        still_open = await executor.run_graph([TaskSpec("b", "provider", 2)])
        self.assertEqual(still_open.stats["executed"], 0)
        now[0], failures[0] = 106, False
        recovered = await executor.run_graph([TaskSpec("a", "provider", 1)])
        self.assertTrue(recovered.succeeded)
        next_job = await executor.run_graph([TaskSpec("b", "provider", 2)])
        self.assertTrue(next_job.succeeded)

    async def test_circuit_provider_isolation(self):
        def handler(payload, parents):
            if payload == "fail":
                raise OSError()
            return payload
        executor = self.executor({"handler": handler}, workers=1, circuit_threshold=1)
        result = await executor.run_graph([
            TaskSpec("a", "handler", "fail", provider="feed-a", max_attempts=1),
            TaskSpec("b", "handler", "ok", provider="feed-b")])
        self.assertEqual(result.outputs["b"], "ok")

    async def test_cancelled_last_waiter_cleans_checkpoint_and_resumes(self):
        started = asyncio.Event()
        cancelled = asyncio.Event()
        async def wait(payload, parents):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()
        executor = self.executor({"work": wait})
        job = TaskSpec("job", "work", max_attempts=1)
        run = asyncio.create_task(executor.run_graph([job]))
        await started.wait()
        run.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await run
        self.assertTrue(cancelled.is_set())
        state, attempts = executor.db.execute("SELECT state,attempts FROM beast_execution").fetchone()
        self.assertEqual((state, attempts), ("PENDING", 0))
        executor.handlers["work"] = lambda payload, parents: "resumed"
        result = await executor.run_graph([job])
        self.assertEqual(result.outputs["job"], "resumed")

    async def test_cancelled_follower_does_not_cancel_shared_job(self):
        started, finish = asyncio.Event(), asyncio.Event()
        calls = 0
        async def wait(payload, parents):
            nonlocal calls
            calls += 1
            started.set()
            await finish.wait()
            return "done"
        executor = self.executor({"wait": wait})
        tasks = [TaskSpec("job", "wait")]
        first = asyncio.create_task(executor.run_graph(tasks))
        await started.wait()
        second = asyncio.create_task(executor.run_graph(tasks))
        for _ in range(4):
            await asyncio.sleep(0)
        second.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await second
        finish.set()
        result = await first
        self.assertEqual(result.outputs["job"], "done")
        self.assertEqual(calls, 1)

    async def test_graph_backpressure_recovers_after_completion(self):
        started, finish = asyncio.Event(), asyncio.Event()
        async def work(payload, parents):
            started.set()
            await finish.wait()
            return payload
        executor = self.executor({"work": work}, max_graphs=1)
        graph = [TaskSpec("job", "work", 1)]
        first = asyncio.create_task(executor.run_graph(graph))
        await started.wait()
        with self.assertRaisesRegex(RuntimeError, "GRAPH_BACKPRESSURE"):
            await executor.run_graph(graph)
        finish.set()
        await first
        self.assertTrue((await executor.run_graph(graph)).succeeded)

    async def test_timeout_becomes_dead_letter(self):
        async def hang(payload, parents):
            await asyncio.Event().wait()
        executor = self.executor({"hang": hang}, task_timeout=0.005, lease_seconds=1)
        result = await executor.run_graph([TaskSpec("hang", "hang", max_attempts=1)])
        self.assertEqual(result.receipts["hang"]["status"], "DEAD_LETTER")
        self.assertEqual(result.receipts["hang"]["error_kind"], "TimeoutError")

    async def test_other_executor_live_lease_defers(self):
        entered, finish = asyncio.Event(), asyncio.Event()
        calls = 0
        async def work(payload, parents):
            nonlocal calls
            calls += 1
            entered.set()
            await finish.wait()
            return payload
        first = self.executor({"work": work})
        second = self.executor({"work": work})
        job = TaskSpec("job", "work", 1)
        running = asyncio.create_task(first.run_graph([job]))
        await entered.wait()
        result = await second.run_graph([job])
        self.assertEqual(result.receipts["job"]["status"], "DEFERRED_BUSY")
        finish.set()
        await running
        self.assertEqual(calls, 1)
        self.assertEqual((await second.run_graph([job])).stats["cache_hits"], 1)

    async def test_expired_crash_lease_replays_without_false_failure(self):
        executor = self.executor()
        job = TaskSpec("job", "echo", 7, max_attempts=1)
        key = executor._key(job, {})
        executor.db.execute("""INSERT INTO beast_execution
            (cache_key,scope_key,state,attempts,owner,lease_until) VALUES(?,?,'RUNNING',1,'dead',0)""",
            (key, "a" * 64))
        result = await executor.run_graph([job])
        self.assertEqual(result.outputs["job"], 7)

    async def test_crash_during_backoff_preserves_observed_failure_budget(self):
        calls = []
        def fail(payload, parents):
            calls.append(payload)
            raise OSError()
        executor = self.executor({"fail": fail})
        job = TaskSpec("job", "fail", 7, max_attempts=2)
        key = executor._key(job, {})
        executor.db.execute("""INSERT INTO beast_execution
            (cache_key,scope_key,state,attempts,owner,lease_until)
            VALUES(?,?,'RETRY_WAIT',1,'crashed',0)""", (key, "a" * 64))
        result = await executor.run_graph([job])
        self.assertEqual(len(calls), 1)
        self.assertEqual(result.receipts["job"]["attempts"], 2)
        self.assertEqual(result.receipts["job"]["status"], "DEAD_LETTER")

    async def test_cancel_during_backoff_preserves_failure_budget(self):
        sleeping = asyncio.Event()
        async def backoff(delay):
            sleeping.set()
            await asyncio.Event().wait()
        def fail(payload, parents):
            raise OSError()
        executor = self.executor({"fail": fail}, sleep=backoff)
        run = asyncio.create_task(executor.run_graph([TaskSpec("job", "fail", max_attempts=2)]))
        await sleeping.wait()
        run.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await run
        row = executor.db.execute("SELECT state,attempts FROM beast_execution").fetchone()
        self.assertEqual(row, ("PENDING", 1))

    async def test_half_open_allows_only_one_probe(self):
        now, healthy = [10.0], [False]
        entered, finish = asyncio.Event(), asyncio.Event()
        calls = []
        async def provider(payload, parents):
            calls.append(payload)
            if not healthy[0]:
                raise OSError()
            entered.set()
            await finish.wait()
            return payload
        executor = self.executor({"provider": provider}, circuit_threshold=1,
                                 circuit_reset=1, clock=lambda: now[0])
        await executor.run_graph([TaskSpec("bad", "provider", 0, max_attempts=1)])
        healthy[0], now[0] = True, 12.0
        first = asyncio.create_task(executor.run_graph([TaskSpec("probe", "provider", 1)]))
        await entered.wait()
        other = await executor.run_graph([TaskSpec("other", "provider", 2)])
        self.assertEqual(other.receipts["other"]["status"], "DEFERRED_CIRCUIT")
        finish.set()
        self.assertTrue((await first).succeeded)
        self.assertEqual(calls, [0, 1])

    async def test_expired_owner_cannot_overwrite_new_owner_checkpoint(self):
        now = [100.0]
        started, finish = asyncio.Event(), asyncio.Event()
        async def old_handler(payload, parents):
            started.set()
            await finish.wait()
            return "old"
        first = self.executor({"work": old_handler}, clock=lambda: now[0])
        second = self.executor({"work": lambda p, d: "new"}, clock=lambda: now[0])
        job = TaskSpec("job", "work")
        old = asyncio.create_task(first.run_graph([job]))
        await started.wait()
        now[0] = 200.0
        self.assertEqual((await second.run_graph([job])).outputs["job"], "new")
        finish.set()
        with self.assertRaisesRegex(RuntimeError, "CHECKPOINT_LEASE_LOST"):
            await old
        self.assertEqual((await second.run_graph([job])).outputs["job"], "new")

    async def test_cache_corruption_is_not_returned(self):
        executor = self.executor()
        job = TaskSpec("job", "echo", {"source": "original"})
        await executor.run_graph([job])
        executor.db.execute("UPDATE beast_execution SET output_json='{}'")
        with self.assertRaisesRegex(ValueError, "CHECKPOINT_OUTPUT_CORRUPTED"):
            await executor.run_graph([job])

    async def test_cycles_unknown_dependencies_and_unknown_handlers_run_nothing(self):
        calls = []
        executor = self.executor({"echo": lambda p, d: calls.append(p)})
        bad = [([TaskSpec("a", "echo", dependencies=("b",)),
                 TaskSpec("b", "echo", dependencies=("a",))], CycleError),
               ([TaskSpec("a", "echo", dependencies=("missing",))], ValueError),
               ([TaskSpec("a", "os.system", "echo unsafe")], ValueError)]
        for tasks, error in bad:
            with self.subTest(tasks=tasks), self.assertRaises(error):
                await executor.run_graph(tasks)
        self.assertEqual(calls, [])
        self.assertEqual(executor.db.execute("SELECT COUNT(*) FROM beast_execution").fetchone()[0], 0)

    async def test_payload_snapshot_cannot_change_during_wait(self):
        entered, finish = asyncio.Event(), asyncio.Event()
        async def wait(payload, parents):
            entered.set()
            await finish.wait()
            return payload
        executor = self.executor({"wait": wait})
        payload = {"value": [1, 2]}
        running = asyncio.create_task(executor.run_graph([TaskSpec("job", "wait", payload)]))
        await entered.wait()
        payload["value"].append(99)
        finish.set()
        self.assertEqual((await running).outputs["job"], {"value": [1, 2]})

    async def test_task_admission_and_plain_json(self):
        executor = self.executor(max_tasks=1)
        cases = [[TaskSpec("a", "echo"), TaskSpec("b", "echo")],
                 [TaskSpec("bad", "echo", float("nan"))],
                 [TaskSpec("bad", "echo", {1: "not a string key"})],
                 [TaskSpec("bad", "echo", object())],
                 [TaskSpec("bad", "echo", house="H00")],
                 [TaskSpec("bad", "echo", max_attempts=0)]]
        for tasks in cases:
            with self.subTest(tasks=tasks), self.assertRaises(ValueError):
                await executor.run_graph(tasks)

    async def test_non_json_handler_output_fails_closed(self):
        executor = self.executor({"bad": lambda p, d: float("inf")})
        result = await executor.run_graph([TaskSpec("job", "bad", max_attempts=1)])
        self.assertEqual(result.outputs, {})
        self.assertEqual(result.receipts["job"]["status"], "DEAD_LETTER")

    def test_scope_private_mode_and_timing_bounds(self):
        for options in ({"mode": "PALACE"}, {"scope_key": "unverified-name"},
                        {"workers": True}, {"workers": 0},
                        {"lease_seconds": 5, "task_timeout": 10},
                        {"backoff_base": float("nan")}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.executor(**options)


if __name__ == "__main__":
    unittest.main()
