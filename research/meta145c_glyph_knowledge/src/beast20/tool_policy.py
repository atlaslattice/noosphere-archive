# Copyright 2025-2026 @ Eigent.ai. Licensed under the Apache License, Version 2.0.
# Adapted from Eigent backend/app/run_policy.py at
# 9840d8aeb304b4af62838331a35c818f128a7be9, automatic_tool_replay_allowed.
# Modifications: Atlas effect names, finite retry budgets, strict JSON validation,
# registered dispatch, authorization at dispatch/return, and explicit ambiguity.
# See docs/native1728/THIRD_PARTY_NOTICES.md and LICENSE-EIGENT-APACHE-2.0.txt.
"""Policy for registered external tools; no provider credentials or model calls.

A replay decision is permission to retry under an existing grant, not a grant.
The registry invokes one attempt only. The host must persist receipts and supply
an authorizer backed by actual identity/rights. Caller names and keys are not
identity. Async timeout/cancellation can leave remote effects uncertain; neither
this policy nor an idempotency key implements exactly-once remote execution.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import inspect
import json
import math
import re
import time
from types import MappingProxyType
from typing import Any, Awaitable, Callable, Iterable


_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,159}\Z")
_KEY = re.compile(r"[A-Za-z0-9_.:@/-]{1,160}\Z")
MAX_ATTEMPTS = 12
MAX_TIMEOUT_MS = 120_000
MAX_JSON_BYTES = 65_536


class ToolEffect(str, Enum):
    READ_ONLY = "READ_ONLY"
    IDEMPOTENT_WRITE = "IDEMPOTENT_WRITE"
    NON_IDEMPOTENT_WRITE = "NON_IDEMPOTENT_WRITE"
    INTERNAL_CHILD_LAUNCH = "INTERNAL_CHILD_LAUNCH"


class ToolOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    NOT_EXECUTED = "NOT_EXECUTED"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


def _bounded_int(value: Any, name: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name}_OUT_OF_RANGE")
    return value


def _key(value: str | None) -> str | None:
    if value is not None and (type(value) is not str or not _KEY.fullmatch(value)):
        raise ValueError("INVALID_IDEMPOTENCY_KEY")
    return value


def _plain_json(value: Any) -> tuple[Any, str]:
    def check(item: Any, depth: int = 0) -> None:
        if depth > 24:
            raise ValueError("JSON_DEPTH_LIMIT")
        if type(item) in (str, bool, type(None)):
            return
        if type(item) is int and abs(item) <= 2**53 - 1:
            return
        if type(item) is float and math.isfinite(item) and (not item.is_integer() or abs(item) <= 2**53 - 1):
            return
        if type(item) is list:
            for child in item:
                check(child, depth + 1)
            return
        if type(item) is dict and all(type(k) is str for k in item):
            if any(k in {"__proto__", "constructor", "prototype"} for k in item):
                raise ValueError("RESERVED_JSON_KEY")
            for child in item.values():
                check(child, depth + 1)
            return
        raise ValueError("PLAIN_FINITE_JSON_REQUIRED")
    check(value)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False)
    if len(encoded.encode("utf-8")) > MAX_JSON_BYTES:
        raise ValueError("JSON_SIZE_LIMIT")
    return json.loads(encoded), hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RetryDecision:
    allowed: bool
    reason: str
    attempts_remaining: int
    delay_ms: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def retry_decision(effect: ToolEffect | str, outcome: ToolOutcome | str, *,
                   attempt: int, max_attempts: int = 3,
                   idempotency_key: str | None = None,
                   remaining_budget_ms: int | None = None) -> RetryDecision:
    """Bounded adaptation of Eigent's automatic-tool-replay classification."""
    effect, outcome = ToolEffect(effect), ToolOutcome(outcome)
    _bounded_int(max_attempts, "MAX_ATTEMPTS", 1, MAX_ATTEMPTS)
    _bounded_int(attempt, "ATTEMPT", 1, max_attempts)
    _key(idempotency_key)
    if remaining_budget_ms is not None:
        _bounded_int(remaining_budget_ms, "REMAINING_BUDGET_MS", 0, 600_000)
    remaining = max_attempts - attempt
    def deny(reason: str) -> RetryDecision:
        return RetryDecision(False, reason, remaining, 0)
    if outcome is ToolOutcome.SUCCESS:
        return deny("ALREADY_SUCCEEDED")
    if outcome in {ToolOutcome.AUTHORIZATION_DENIED, ToolOutcome.BUDGET_EXHAUSTED}:
        return deny(outcome.value)
    if remaining == 0:
        return deny("ATTEMPT_BUDGET_EXHAUSTED")
    # The classification below is adapted from the pinned Eigent implementation.
    if effect is ToolEffect.INTERNAL_CHILD_LAUNCH:
        return deny("CHILD_LAUNCH_REQUIRES_RECONCILIATION")
    if effect is ToolEffect.NON_IDEMPOTENT_WRITE:
        return deny("NON_IDEMPOTENT_EFFECT_REQUIRES_RECONCILIATION")
    if effect is ToolEffect.IDEMPOTENT_WRITE and idempotency_key is None:
        return deny("IDEMPOTENCY_KEY_REQUIRED")
    delay = min(100 * 2 ** (attempt - 1), 10_000)
    if remaining_budget_ms is not None and remaining_budget_ms <= delay:
        return deny("TIME_BUDGET_EXHAUSTED")
    return RetryDecision(True, "REPLAY_SAFE_UNDER_EXISTING_AUTHORIZATION", remaining, delay)


@dataclass(frozen=True)
class InvocationContext:
    principal: str
    scope: str
    rights_epoch: str
    mode: str = "WORK"

    def __post_init__(self) -> None:
        for name in ("principal", "scope", "rights_epoch"):
            value = getattr(self, name)
            if type(value) is not str or not value.strip() or len(value) > 256:
                raise ValueError("INVALID_CONTEXT_" + name.upper())
            if any(ord(c) < 32 for c in value):
                raise ValueError("INVALID_CONTEXT_" + name.upper())
        if self.mode != "WORK":
            raise ValueError("WORK_CONTEXT_REQUIRED")


@dataclass(frozen=True)
class ToolRegistration:
    name: str
    effect: ToolEffect
    handler: Callable[[dict[str, Any], InvocationContext, str | None], Awaitable[Any]]
    validate_arguments: Callable[[dict[str, Any]], bool]
    version: str = "1"
    external: bool = True
    max_attempts: int = 3
    timeout_ms: int = 5_000

    def __post_init__(self) -> None:
        if type(self.name) is not str or not _NAME.fullmatch(self.name):
            raise ValueError("INVALID_TOOL_NAME")
        if type(self.effect) is not ToolEffect:
            raise ValueError("REGISTERED_EFFECT_ENUM_REQUIRED")
        if not inspect.iscoroutinefunction(self.handler) or not callable(self.validate_arguments):
            raise ValueError("ASYNC_HANDLER_AND_VALIDATOR_REQUIRED")
        if type(self.version) is not str or not self.version.strip() or len(self.version) > 128:
            raise ValueError("INVALID_TOOL_VERSION")
        if type(self.external) is not bool:
            raise ValueError("EXTERNAL_BOOLEAN_REQUIRED")
        _bounded_int(self.max_attempts, "MAX_ATTEMPTS", 1, MAX_ATTEMPTS)
        _bounded_int(self.timeout_ms, "TIMEOUT_MS", 1, MAX_TIMEOUT_MS)


class KnownNotExecuted(Exception):
    """A trusted handler establishes that the attempted remote effect never ran."""


class ToolRegistry:
    """Immutable server registry with one-attempt dispatch and explicit receipts.

    An authorization callback is mandatory when any registration is external.
    It receives (registration, context, a fresh arguments copy, stage), where
    stage is DISPATCH or RETURN, and must return the literal boolean True.
    Timeouts request async cancellation but do not prove remote cancellation.
    Unknown tools, invalid arguments, and invalid budgets fail before dispatch.
    The host supplies attempt counts from its durable receipt store; this class
    does not persist retry counts or trust request-provided counters as history.
    """
    def __init__(self, registrations: Iterable[ToolRegistration], *,
                 authorize: Callable[..., bool | Awaitable[bool]] | None,
                 max_inflight: int = 4) -> None:
        items = tuple(registrations)
        if not items or any(type(item) is not ToolRegistration for item in items):
            raise ValueError("TOOL_REGISTRATIONS_REQUIRED")
        if len({item.name for item in items}) != len(items):
            raise ValueError("DUPLICATE_TOOL_NAME")
        if authorize is not None and not callable(authorize):
            raise ValueError("AUTHORIZER_CALLABLE_REQUIRED")
        if any(item.external for item in items) and authorize is None:
            raise ValueError("EXTERNAL_AUTHORIZER_REQUIRED")
        self._tools = MappingProxyType({item.name: item for item in items})
        self._authorize = authorize
        self._slots = asyncio.Semaphore(_bounded_int(max_inflight, "MAX_INFLIGHT", 1, 64))
        self._pending: set[asyncio.Task] = set()

    def list_tools(self) -> list[dict[str, Any]]:
        return [{"name": item.name, "version": item.version, "effect": item.effect.value,
                 "external": item.external, "max_attempts": item.max_attempts,
                 "timeout_ms": item.timeout_ms} for item in self._tools.values()]

    async def _allowed(self, tool: ToolRegistration, context: InvocationContext,
                       arguments: dict[str, Any], stage: str) -> bool:
        if self._authorize is None:
            return not tool.external
        try:
            answer = self._authorize(tool, context, _plain_json(arguments)[0], stage)
            if inspect.isawaitable(answer):
                answer = await answer
            return answer is True
        except Exception:
            return False

    async def dispatch(self, name: str, arguments: dict[str, Any],
                       context: InvocationContext, *, attempt: int = 1,
                       idempotency_key: str | None = None,
                       remaining_budget_ms: int | None = None) -> dict[str, Any]:
        if type(name) is not str or name not in self._tools:
            raise ValueError("UNREGISTERED_TOOL")
        tool = self._tools[name]
        if type(context) is not InvocationContext:
            raise ValueError("INVOCATION_CONTEXT_REQUIRED")
        _bounded_int(attempt, "ATTEMPT", 1, tool.max_attempts)
        key = _key(idempotency_key)
        if tool.effect is ToolEffect.IDEMPOTENT_WRITE and key is None:
            raise ValueError("IDEMPOTENCY_KEY_REQUIRED")
        if type(arguments) is not dict:
            raise ValueError("ARGUMENT_OBJECT_REQUIRED")
        arguments, argument_digest = _plain_json(arguments)
        if tool.validate_arguments(_plain_json(arguments)[0]) is not True:
            raise ValueError("ARGUMENT_SCHEMA_REJECTED")
        if remaining_budget_ms is not None:
            _bounded_int(remaining_budget_ms, "REMAINING_BUDGET_MS", 0, 600_000)
        start = time.monotonic()
        deadline = start + min(tool.timeout_ms, remaining_budget_ms or tool.timeout_ms) / 1000
        def receipt(outcome: ToolOutcome, *, dispatched: bool, result: Any = None) -> dict[str, Any]:
            elapsed = max(0, int((time.monotonic() - start) * 1000))
            budget = None if remaining_budget_ms is None else max(0, remaining_budget_ms - elapsed)
            answer = {"tool": name, "version": tool.version, "effect": tool.effect.value,
                      "outcome": outcome.value, "attempt": attempt, "dispatched": dispatched,
                      "argument_digest": argument_digest, "elapsed_ms": elapsed,
                      "retry": retry_decision(tool.effect, outcome, attempt=attempt,
                          max_attempts=tool.max_attempts, idempotency_key=key,
                          remaining_budget_ms=budget).to_dict()}
            if outcome is ToolOutcome.SUCCESS:
                answer["result"], answer["result_digest"] = _plain_json(result)
            return answer
        if remaining_budget_ms == 0:
            return receipt(ToolOutcome.BUDGET_EXHAUSTED, dispatched=False)
        try:
            allowed = await asyncio.wait_for(self._allowed(tool, context, arguments, "DISPATCH"),
                                             max(0, deadline - time.monotonic()))
        except TimeoutError:
            allowed = False
        if not allowed:
            return receipt(ToolOutcome.AUTHORIZATION_DENIED, dispatched=False)
        if time.monotonic() >= deadline:
            return receipt(ToolOutcome.BUDGET_EXHAUSTED, dispatched=False)
        try:
            await asyncio.wait_for(self._slots.acquire(), max(0, deadline - time.monotonic()))
        except TimeoutError:
            return receipt(ToolOutcome.NOT_EXECUTED, dispatched=False)
        if time.monotonic() >= deadline:
            self._slots.release()
            return receipt(ToolOutcome.BUDGET_EXHAUSTED, dispatched=False)
        task = asyncio.create_task(tool.handler(_plain_json(arguments)[0], context, key))
        self._pending.add(task)
        def finished(done: asyncio.Task) -> None:
            self._pending.discard(done)
            self._slots.release()
            if not done.cancelled():
                done.exception()  # Retrieve delayed failures after a timeout.
        task.add_done_callback(finished)
        try:
            completed, _ = await asyncio.wait({task}, timeout=max(0, deadline - time.monotonic()))
            if not completed:
                task.cancel()
                return receipt(ToolOutcome.TIMEOUT, dispatched=True)
            if time.monotonic() >= deadline:
                return receipt(ToolOutcome.TIMEOUT, dispatched=True)
            if task.cancelled():
                return receipt(ToolOutcome.CANCELLED, dispatched=True)
            result = task.result()
            result, _ = _plain_json(result)
        except KnownNotExecuted:
            return receipt(ToolOutcome.NOT_EXECUTED, dispatched=True)
        except asyncio.CancelledError:
            task.cancel()
            raise  # The caller must reconcile any remote effect before redispatch.
        except Exception:
            return receipt(ToolOutcome.UNKNOWN_OUTCOME, dispatched=True)
        try:
            allowed = await asyncio.wait_for(self._allowed(tool, context, arguments, "RETURN"),
                                             max(0, deadline - time.monotonic()))
        except TimeoutError:
            allowed = False
        if not allowed:
            return receipt(ToolOutcome.AUTHORIZATION_DENIED, dispatched=True)
        return receipt(ToolOutcome.SUCCESS, dispatched=True, result=result)
