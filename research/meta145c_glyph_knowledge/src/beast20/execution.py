"""E07–E12: scoped, durable execution of explicitly registered local Work jobs.

Async jobs may overlap I/O; synchronous jobs do not acquire CPU parallelism.
Checkpoints provide replay suppression for successful pure/idempotent handlers,
not exactly-once external effects. A scope digest is an isolation key, not an
identity or permissions attestation. The host must authorize READ and RETURN.
"""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from graphlib import TopologicalSorter
import hashlib
import inspect
import json
import math
import re
import sqlite3
import time
from typing import Any, Awaitable, Callable, Mapping
import uuid


_NAME = re.compile(r"[A-Za-z0-9_.:-]{1,160}\Z")
_HOUSE = re.compile(r"H(?:0[1-9]|1[0-2])\Z")
_DIGEST = re.compile(r"[a-f0-9]{64}\Z")
_SUCCESS = {"SUCCEEDED", "CACHED"}


def _json(value: Any) -> str:
    """Snapshot only JSON primitives: no custom encoders, reprs or pickle."""
    def check(x: Any, depth: int = 0) -> None:
        if depth > 64:
            raise ValueError("JSON_DEPTH_LIMIT")
        if type(x) in (str, int, bool, type(None)):
            return
        if type(x) is float and math.isfinite(x):
            return
        if type(x) is list:
            for item in x:
                check(item, depth + 1)
            return
        if type(x) is dict and all(type(k) is str for k in x):
            for item in x.values():
                check(item, depth + 1)
            return
        raise ValueError("PLAIN_FINITE_JSON_REQUIRED")

    check(value)
    result = json.dumps(value, sort_keys=True, separators=(",", ":"),
                        ensure_ascii=False, allow_nan=False)
    if len(result.encode("utf-8")) > 4 * 1024 * 1024:
        raise ValueError("JSON_SIZE_LIMIT")
    return result


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    handler: str
    payload: Any = None
    dependencies: tuple[str, ...] = ()
    house: str = "H01"
    version: str = "1"
    provider: str = "local"
    max_attempts: int = 3


@dataclass
class GraphResult:
    outputs: dict[str, Any]
    receipts: dict[str, dict[str, Any]]
    stats: dict[str, int]

    @property
    def succeeded(self) -> bool:
        return all(r["status"] in _SUCCESS for r in self.receipts.values())


@dataclass
class _Flight:
    task: asyncio.Task
    waiters: int = 0


@dataclass
class _Breaker:
    failures: int = 0
    open_until: float = 0.0
    probing: bool = False


class AsyncExecutor:
    """One event-loop-local executor with cross-instance SQLite leases.

    ``scope_key`` must encode source edition/digest, principal and rights epoch.
    Callables are supplied by trusted application code, never selected by eval,
    import strings or a model. Handler signature is ``(payload, parent_outputs)``.
    Retry clocks/sleeps are injectable; persisted leases require an epoch clock
    (``time.time`` by default), not process-relative monotonic timestamps.
    """

    def __init__(self, db_path, handlers: Mapping[str, Callable], *,
                 scope_key: str, mode: str = "WORK", workers: int = 4,
                 max_tasks: int = 4096, max_graphs: int = 16, backoff_base: float = 0.01,
                 max_backoff: float = 1.0, circuit_threshold: int = 3,
                 circuit_reset: float = 30.0, task_timeout: float = 30.0,
                 lease_seconds: float = 60.0,
                 clock: Callable[[], float] = time.time,
                 sleep: Callable[[float], Awaitable] = asyncio.sleep):
        if mode != "WORK" or type(scope_key) is not str or not _DIGEST.fullmatch(scope_key):
            raise ValueError("WORK_SCOPE_KEY_REQUIRED")
        if (type(workers) is not int or not 1 <= workers <= 256 or
                type(max_tasks) is not int or not 1 <= max_tasks <= 100_000 or
                type(max_graphs) is not int or not 1 <= max_graphs <= 1024 or
                type(circuit_threshold) is not int or not 1 <= circuit_threshold <= 100):
            raise ValueError("EXECUTION_BOUNDS_INVALID")
        numbers = (backoff_base, max_backoff, circuit_reset, task_timeout, lease_seconds)
        if any(type(n) not in (int, float) or not math.isfinite(n) or n <= 0 for n in numbers):
            raise ValueError("TIMING_BOUNDS_INVALID")
        if backoff_base > max_backoff or lease_seconds <= task_timeout:
            raise ValueError("LEASE_OR_BACKOFF_BOUNDS_INVALID")
        if not handlers or any(type(k) is not str or not _NAME.fullmatch(k) or
                               not callable(v) for k, v in handlers.items()):
            raise ValueError("EXPLICIT_HANDLER_REGISTRY_REQUIRED")
        self.handlers = dict(handlers)
        self.scope_key, self.workers, self.max_tasks = scope_key, workers, max_tasks
        self.max_graphs = max_graphs
        self.backoff_base, self.max_backoff = backoff_base, max_backoff
        self.circuit_threshold, self.circuit_reset = circuit_threshold, circuit_reset
        self.task_timeout, self.lease_seconds = task_timeout, lease_seconds
        self.clock, self.sleep = clock, sleep
        self.owner = uuid.uuid4().hex
        self._flights: dict[str, _Flight] = {}
        self._breakers: dict[str, _Breaker] = {}
        self._slots = asyncio.Semaphore(workers)
        self._active = 0
        self._graphs = 0
        self.db = sqlite3.connect(db_path, isolation_level=None)
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS beast_execution (
            cache_key TEXT PRIMARY KEY, scope_key TEXT NOT NULL,
            state TEXT NOT NULL, output_json TEXT, output_digest TEXT,
            attempts INTEGER NOT NULL DEFAULT 0, error_kind TEXT,
            owner TEXT, lease_until REAL NOT NULL DEFAULT 0)""")

    def close(self) -> None:
        if self._flights or self._graphs:
            raise RuntimeError("EXECUTOR_STILL_RUNNING")
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _validate(self, tasks) -> dict[str, TaskSpec]:
        if type(tasks) not in (list, tuple) or not 1 <= len(tasks) <= self.max_tasks:
            raise ValueError("GRAPH_ADMISSION_LIMIT")
        normalized = {}
        for task in tasks:
            if type(task) is not TaskSpec:
                raise ValueError("TASK_SPEC_REQUIRED")
            if any(type(v) is not str or not _NAME.fullmatch(v)
                   for v in (task.task_id, task.handler, task.version, task.provider)):
                raise ValueError("TASK_IDENTITY_INVALID")
            if task.task_id in normalized:
                raise ValueError("DUPLICATE_TASK_ID")
            if type(task.house) is not str or not _HOUSE.fullmatch(task.house):
                raise ValueError("HOUSE_INVALID")
            if task.handler not in self.handlers:
                raise ValueError("UNREGISTERED_HANDLER")
            if type(task.max_attempts) is not int or not 1 <= task.max_attempts <= 8:
                raise ValueError("RETRY_BOUND_INVALID")
            if type(task.dependencies) not in (tuple, list) or any(
                    type(d) is not str or not _NAME.fullmatch(d) for d in task.dependencies):
                raise ValueError("DEPENDENCIES_INVALID")
            if len(set(task.dependencies)) != len(task.dependencies):
                raise ValueError("DUPLICATE_DEPENDENCY")
            normalized[task.task_id] = TaskSpec(
                task.task_id, task.handler, json.loads(_json(task.payload)),
                tuple(sorted(task.dependencies)), task.house, task.version,
                task.provider, task.max_attempts)
        if any(d not in normalized for task in normalized.values() for d in task.dependencies):
            raise ValueError("UNKNOWN_DEPENDENCY")
        # Exhaust cycle detection before any handler runs or checkpoint is changed.
        tuple(TopologicalSorter({k: t.dependencies for k, t in normalized.items()}).static_order())
        return normalized

    def _key(self, task: TaskSpec, parent_outputs: dict) -> str:
        return _hash(_json({"schema": "atlas.beast20.job/v1", "scope": self.scope_key,
                           "handler": task.handler, "version": task.version,
                           "provider": task.provider, "max_attempts": task.max_attempts,
                           "input": task.payload,
                           "parents": {k: _hash(_json(v)) for k, v in parent_outputs.items()}}))

    def _claim(self, key: str) -> dict:
        now = self.clock()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute("""SELECT scope_key,state,output_json,output_digest,
                attempts,error_kind,owner,lease_until FROM beast_execution WHERE cache_key=?""",
                                  (key,)).fetchone()
            if row is not None and row[0] != self.scope_key:
                raise ValueError("CHECKPOINT_SCOPE_CORRUPTED")
            if row is not None and row[1] == "SUCCEEDED":
                if type(row[2]) is not str or _hash(row[2]) != row[3]:
                    raise ValueError("CHECKPOINT_OUTPUT_CORRUPTED")
                output = json.loads(row[2])
                if _json(output) != row[2]:
                    raise ValueError("CHECKPOINT_OUTPUT_NONCANONICAL")
                result = {"status": "CACHED", "output": output, "digest": row[3],
                          "attempts": row[4], "cache_key": key}
            elif row is not None and row[1] == "DEAD_LETTER":
                result = {"status": "DEAD_LETTER", "attempts": row[4],
                          "error_kind": row[5], "cache_key": key}
            elif row is not None and row[1] in {"RUNNING", "RETRY_WAIT"} and row[7] > now:
                result = {"status": "DEFERRED_BUSY", "attempts": row[4], "cache_key": key}
            else:
                attempts = row[4] if row else 0
                # A crashed/interrupted attempt is not an observed failure.
                if row is not None and row[1] == "RUNNING":
                    attempts = max(0, attempts - 1)
                self.db.execute("""INSERT INTO beast_execution
                    (cache_key,scope_key,state,attempts,owner,lease_until)
                    VALUES(?,?,'RUNNING',?,?,?) ON CONFLICT(cache_key) DO UPDATE SET
                    state='RUNNING',attempts=excluded.attempts,owner=excluded.owner,
                    lease_until=excluded.lease_until,error_kind=NULL""",
                                (key, self.scope_key, attempts, self.owner, now + self.lease_seconds))
                result = {"status": "CLAIMED", "attempts": attempts, "cache_key": key}
            self.db.execute("COMMIT")
            return result
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def _save(self, key: str, state: str, attempts: int, *, output: str | None = None,
              error: str | None = None, keep_owner: bool = False) -> None:
        changed = self.db.execute("""UPDATE beast_execution SET state=?,attempts=?,
            output_json=?,output_digest=?,error_kind=?,owner=?,lease_until=?
            WHERE cache_key=? AND owner=?""",
            (state, attempts, output, _hash(output) if output is not None else None,
             error, self.owner if keep_owner else None,
             self.clock() + self.lease_seconds if keep_owner else 0, key, self.owner)).rowcount
        if changed != 1:
            raise RuntimeError("CHECKPOINT_LEASE_LOST")

    def _allow(self, provider: str) -> bool:
        breaker = self._breakers.setdefault(provider, _Breaker())
        if breaker.failures < self.circuit_threshold:
            return True
        if self.clock() < breaker.open_until or breaker.probing:
            return False
        breaker.probing = True
        return True

    def _provider_result(self, provider: str, *, success: bool = False,
                         cancelled: bool = False) -> None:
        breaker = self._breakers[provider]
        breaker.probing = False
        if cancelled:
            return
        if success:
            breaker.failures = 0
            breaker.open_until = 0
        else:
            breaker.failures += 1
            if breaker.failures >= self.circuit_threshold:
                breaker.open_until = self.clock() + self.circuit_reset

    async def _invoke(self, task: TaskSpec, parents: dict):
        result = self.handlers[task.handler](json.loads(_json(task.payload)),
                                             json.loads(_json(parents)))
        return await result if inspect.isawaitable(result) else result

    async def _execute(self, task: TaskSpec, parents: dict, key: str, stats: dict) -> dict:
        receipt = self._claim(key)
        if receipt["status"] != "CLAIMED":
            if receipt["status"] == "CACHED":
                stats["cache_hits"] += 1
            return receipt
        attempts = receipt["attempts"]
        attempt_started = False
        try:
            while attempts < task.max_attempts:
                async with self._slots:
                    if not self._allow(task.provider):
                        self._save(key, "DEFERRED", attempts, error="CIRCUIT_OPEN")
                        stats["circuit_deferrals"] += 1
                        return {"status": "DEFERRED_CIRCUIT", "attempts": attempts, "cache_key": key}
                    attempts += 1
                    attempt_started = True
                    self._save(key, "RUNNING", attempts, keep_owner=True)
                    self._active += 1
                    stats["max_active"] = max(stats["max_active"], self._active)
                    stats["executed"] += 1
                    try:
                        result = await asyncio.wait_for(self._invoke(task, parents), self.task_timeout)
                        encoded = _json(result)
                    except asyncio.CancelledError:
                        self._provider_result(task.provider, cancelled=True)
                        raise
                    except Exception as error:
                        self._provider_result(task.provider)
                        kind = type(error).__name__
                        if attempts >= task.max_attempts:
                            self._save(key, "DEAD_LETTER", attempts, error=kind)
                            stats["dead_letters"] += 1
                            return {"status": "DEAD_LETTER", "attempts": attempts,
                                    "error_kind": kind, "cache_key": key}
                        # Preserve an observed failure across a crash during backoff.
                        self._save(key, "RETRY_WAIT", attempts, error=kind, keep_owner=True)
                    else:
                        self._provider_result(task.provider, success=True)
                        self._save(key, "SUCCEEDED", attempts, output=encoded)
                        return {"status": "SUCCEEDED", "output": json.loads(encoded),
                                "digest": _hash(encoded), "attempts": attempts, "cache_key": key}
                    finally:
                        self._active -= 1
                attempt_started = False
                stats["retries"] += 1
                await self.sleep(min(self.max_backoff, self.backoff_base * (2 ** (attempts - 1))))
            self._save(key, "DEAD_LETTER", attempts, error="RETRY_BUDGET_EXHAUSTED")
            stats["dead_letters"] += 1
            return {"status": "DEAD_LETTER", "attempts": attempts,
                    "error_kind": "RETRY_BUDGET_EXHAUSTED", "cache_key": key}
        except asyncio.CancelledError:
            # Interrupted work can be replayed; never retain a false success.
            self._save(key, "PENDING", max(0, attempts - int(attempt_started)), error="CANCELLED")
            raise

    async def _singleflight(self, task: TaskSpec, parents: dict, stats: dict) -> dict:
        key = self._key(task, parents)
        flight = self._flights.get(key)
        if flight is None:
            flight = _Flight(asyncio.create_task(self._execute(task, parents, key, stats)))
            self._flights[key] = flight
        else:
            stats["coalesced"] += 1
        flight.waiters += 1
        try:
            # One cancelled caller must not cancel another caller's shared job.
            return json.loads(_json(await asyncio.shield(flight.task)))
        finally:
            flight.waiters -= 1
            if flight.waiters == 0:
                if not flight.task.done():
                    flight.task.cancel()
                    await asyncio.gather(flight.task, return_exceptions=True)
                if self._flights.get(key) is flight:
                    del self._flights[key]

    async def run_graph(self, tasks: list[TaskSpec] | tuple[TaskSpec, ...]) -> GraphResult:
        """Validate, rotate ready Houses, run bounded jobs and propagate failures.

        Dependencies are required successes. A failed/deferred parent blocks its
        descendants; independent branches continue. Same-instance concurrent
        graphs share a semaphore and per-key in-flight jobs. A second process
        encountering a live SQLite lease gets DEFERRED_BUSY, never duplicate work.
        """
        if self._graphs >= self.max_graphs:
            raise RuntimeError("GRAPH_BACKPRESSURE")
        specs = self._validate(tasks)
        sorter = TopologicalSorter({key: t.dependencies for key, t in specs.items()})
        sorter.prepare()
        ready: dict[str, deque] = {}
        house_order: deque[str] = deque()
        running: dict[asyncio.Task, str] = {}
        outputs, receipts = {}, {}
        stats = dict(submitted=len(tasks), executed=0, cache_hits=0, coalesced=0,
                     retries=0, dead_letters=0, circuit_deferrals=0, blocked=0,
                     max_active=0, max_admitted=0)

        def enqueue(ids):
            for task_id in sorted(ids):
                house = specs[task_id].house
                if house not in ready:
                    ready[house] = deque()
                if not ready[house]:
                    house_order.append(house)
                ready[house].append(task_id)

        self._graphs += 1
        try:
            enqueue(sorter.get_ready())
            while sorter.is_active():
                while house_order and len(running) < self.workers:
                    house = house_order.popleft()
                    task_id = ready[house].popleft()
                    if ready[house]:
                        house_order.append(house)
                    task = specs[task_id]
                    if any(receipts[d]["status"] not in _SUCCESS for d in task.dependencies):
                        receipts[task_id] = {"status": "BLOCKED_DEPENDENCY", "attempts": 0}
                        stats["blocked"] += 1
                        sorter.done(task_id)
                        enqueue(sorter.get_ready())
                        continue
                    parent_outputs = {d: outputs[d] for d in task.dependencies}
                    future = asyncio.create_task(self._singleflight(task, parent_outputs, stats))
                    running[future] = task_id
                    stats["max_admitted"] = max(stats["max_admitted"], len(running))
                if not running:
                    continue
                done, _ = await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
                for future in sorted(done, key=lambda f: running[f]):
                    task_id = running.pop(future)
                    receipt = future.result()
                    if receipt["status"] in _SUCCESS:
                        outputs[task_id] = receipt.pop("output")
                    receipts[task_id] = receipt
                    sorter.done(task_id)
                enqueue(sorter.get_ready())
            return GraphResult(outputs, receipts, stats)
        finally:
            for future in running:
                future.cancel()
            if running:
                await asyncio.gather(*running, return_exceptions=True)
            self._graphs -= 1
