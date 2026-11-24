"""Behavioral policy tests with local functions only; no paid or remote calls."""
import asyncio
import math
import unittest

from src.beast20.tool_policy import (
    InvocationContext, KnownNotExecuted, ToolEffect, ToolOutcome,
    ToolRegistration, ToolRegistry, retry_decision,
)


class RetryPolicyTests(unittest.TestCase):
    def test_reads_and_keyed_writes_may_retry_uncertain_outcomes(self):
        for outcome in (ToolOutcome.UNKNOWN_OUTCOME, ToolOutcome.TIMEOUT, ToolOutcome.CANCELLED):
            for effect, key in ((ToolEffect.READ_ONLY, None), (ToolEffect.IDEMPOTENT_WRITE, "call-1")):
                decision = retry_decision(effect, outcome, attempt=1, idempotency_key=key)
                self.assertTrue(decision.allowed)
                self.assertEqual((decision.attempts_remaining, decision.delay_ms), (2, 100))

    def test_child_launches_and_unsafe_writes_never_auto_replay(self):
        for effect in (ToolEffect.NON_IDEMPOTENT_WRITE, ToolEffect.INTERNAL_CHILD_LAUNCH):
            for outcome in (ToolOutcome.UNKNOWN_OUTCOME, ToolOutcome.TIMEOUT, ToolOutcome.NOT_EXECUTED):
                self.assertFalse(retry_decision(effect, outcome, attempt=1,
                                                idempotency_key="provided").allowed)

    def test_idempotent_effect_requires_actual_key(self):
        result = retry_decision(ToolEffect.IDEMPOTENT_WRITE, ToolOutcome.UNKNOWN_OUTCOME, attempt=1)
        self.assertEqual(result.reason, "IDEMPOTENCY_KEY_REQUIRED")
        for bad in ("", " spaces ", True, 1, "x" * 161):
            with self.assertRaises(ValueError):
                retry_decision(ToolEffect.IDEMPOTENT_WRITE, ToolOutcome.TIMEOUT,
                               attempt=1, idempotency_key=bad)

    def test_success_denial_and_exhaustion_are_terminal(self):
        for outcome in (ToolOutcome.SUCCESS, ToolOutcome.AUTHORIZATION_DENIED, ToolOutcome.BUDGET_EXHAUSTED):
            self.assertFalse(retry_decision(ToolEffect.READ_ONLY, outcome, attempt=1).allowed)
        self.assertFalse(retry_decision(ToolEffect.READ_ONLY, ToolOutcome.TIMEOUT, attempt=3).allowed)

    def test_budget_and_backoff_are_finite(self):
        self.assertFalse(retry_decision(ToolEffect.READ_ONLY, ToolOutcome.TIMEOUT,
                                       attempt=1, remaining_budget_ms=100).allowed)
        self.assertTrue(retry_decision(ToolEffect.READ_ONLY, ToolOutcome.TIMEOUT,
                                      attempt=1, remaining_budget_ms=101).allowed)
        decision = retry_decision(ToolEffect.READ_ONLY, ToolOutcome.TIMEOUT,
                                  attempt=11, max_attempts=12)
        self.assertEqual(decision.delay_ms, 10_000)

    def test_numbers_are_strict_and_finite(self):
        for bad in (0, -1, True, 1.0, math.inf, math.nan, "1"):
            with self.assertRaises((ValueError, TypeError)):
                retry_decision(ToolEffect.READ_ONLY, ToolOutcome.TIMEOUT, attempt=bad)
        for bad in (0, 13, True, math.inf):
            with self.assertRaises(ValueError):
                retry_decision(ToolEffect.READ_ONLY, ToolOutcome.TIMEOUT, attempt=1, max_attempts=bad)

    def test_unknown_effect_or_outcome_rejected(self):
        with self.assertRaises(ValueError):
            retry_decision("user_says_safe", ToolOutcome.TIMEOUT, attempt=1)
        with self.assertRaises(ValueError):
            retry_decision(ToolEffect.READ_ONLY, "maybe_good", attempt=1)

    def test_context_is_work_scoped_and_frozen(self):
        for bad in ("PLAY", "SOCIAL", "IMAGINE", "QUIET"):
            with self.assertRaises(ValueError):
                InvocationContext("p", "s", "1", bad)
        with self.assertRaises(ValueError):
            InvocationContext("", "s", "1")
        context = InvocationContext("p", "s", "1")
        with self.assertRaises(AttributeError):
            context.rights_epoch = "2"


class DispatchPolicyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.context = InvocationContext("local-test", "public-source", "1")
        self.calls = []

    async def echo(self, arguments, context, key):
        self.calls.append((arguments, context, key))
        return {"value": arguments["value"]}

    def registration(self, **kwargs):
        return ToolRegistration("echo", kwargs.pop("effect", ToolEffect.READ_ONLY),
                                kwargs.pop("handler", self.echo),
                                kwargs.pop("validate_arguments", lambda a: set(a) == {"value"}),
                                **kwargs)

    async def test_external_registration_requires_authorizer(self):
        with self.assertRaises(ValueError):
            ToolRegistry([self.registration()], authorize=None)
        with self.assertRaises(ValueError):
            ToolRegistry([self.registration()], authorize=True)

    async def test_unregistered_names_and_duplicate_registration_denied(self):
        registry = ToolRegistry([self.registration()], authorize=lambda *a: True)
        with self.assertRaises(ValueError):
            await registry.dispatch("admin.exec", {"value": 1}, self.context)
        with self.assertRaises(ValueError):
            ToolRegistry([self.registration(), self.registration()], authorize=lambda *a: True)
        self.assertEqual(self.calls, [])

    async def test_schema_is_checked_before_authorization_and_dispatch(self):
        seen = []
        registry = ToolRegistry([self.registration()], authorize=lambda *a: seen.append(a) or True)
        with self.assertRaises(ValueError):
            await registry.dispatch("echo", {"value": 1, "effect": "READ_ONLY"}, self.context)
        self.assertEqual((seen, self.calls), ([], []))

    async def test_nonfinite_oversize_reserved_and_non_json_arguments_fail(self):
        registry = ToolRegistry([self.registration()], authorize=lambda *a: True)
        for value in (math.nan, math.inf, object(), "x" * 65_536, {"__proto__": {}}, 2**60):
            with self.assertRaises(ValueError):
                await registry.dispatch("echo", {"value": value}, self.context)
        self.assertEqual(self.calls, [])

    async def test_permission_callback_must_return_literal_true(self):
        for answer in (False, 1, "yes", None, {"allowed": True}):
            registry = ToolRegistry([self.registration()], authorize=lambda *a: answer)
            receipt = await registry.dispatch("echo", {"value": 1}, self.context)
            self.assertEqual(receipt["outcome"], "AUTHORIZATION_DENIED")
            self.assertFalse(receipt["dispatched"])
        self.assertEqual(self.calls, [])

    async def test_return_revocation_withholds_result_without_retry(self):
        stages = []
        def authorize(tool, context, args, stage):
            stages.append(stage)
            return stage == "DISPATCH"
        registry = ToolRegistry([self.registration()], authorize=authorize)
        receipt = await registry.dispatch("echo", {"value": 1}, self.context)
        self.assertEqual(stages, ["DISPATCH", "RETURN"])
        self.assertEqual(receipt["outcome"], "AUTHORIZATION_DENIED")
        self.assertTrue(receipt["dispatched"])
        self.assertNotIn("result", receipt)
        self.assertFalse(receipt["retry"]["allowed"])

    async def test_successful_result_is_detached_and_has_receipt(self):
        result = {"values": [1]}
        async def handler(*args):
            return result
        registry = ToolRegistry([self.registration(handler=handler)], authorize=lambda *a: True)
        receipt = await registry.dispatch("echo", {"value": 1}, self.context)
        result["values"].append(2)
        self.assertEqual(receipt["result"], {"values": [1]})
        self.assertEqual(len(receipt["result_digest"]), 64)
        self.assertFalse(receipt["retry"]["allowed"])

    async def test_handler_and_authorizer_mutations_do_not_change_other_views(self):
        seen = []
        async def handler(arguments, context, key):
            arguments["value"].append("handler")
            return arguments
        def authorize(tool, context, arguments, stage):
            seen.append((stage, list(arguments["value"])))
            arguments["value"].append("authorizer")
            return True
        registry = ToolRegistry([self.registration(handler=handler)], authorize=authorize)
        original = {"value": [1]}
        receipt = await registry.dispatch("echo", original, self.context)
        self.assertEqual(original, {"value": [1]})
        self.assertEqual(seen, [("DISPATCH", [1]), ("RETURN", [1])])
        self.assertEqual(receipt["result"], {"value": [1, "handler"]})

    async def test_idempotent_write_key_required_and_forwarded(self):
        registry = ToolRegistry([self.registration(effect=ToolEffect.IDEMPOTENT_WRITE)],
                                authorize=lambda *a: True)
        with self.assertRaises(ValueError):
            await registry.dispatch("echo", {"value": 1}, self.context)
        receipt = await registry.dispatch("echo", {"value": 1}, self.context,
                                          idempotency_key="same-operation")
        self.assertEqual(receipt["outcome"], "SUCCESS")
        self.assertEqual(self.calls[0][2], "same-operation")

    async def test_timeout_is_uncertain_and_does_not_auto_dispatch_again(self):
        count = 0
        async def slow(*args):
            nonlocal count
            count += 1
            await asyncio.sleep(10)
        registry = ToolRegistry([self.registration(handler=slow, timeout_ms=5,
                                effect=ToolEffect.NON_IDEMPOTENT_WRITE)], authorize=lambda *a: True)
        receipt = await registry.dispatch("echo", {"value": 1}, self.context)
        self.assertEqual(receipt["outcome"], "TIMEOUT")
        self.assertFalse(receipt["retry"]["allowed"])
        self.assertEqual(count, 1)

    async def test_generic_error_is_unknown_and_does_not_echo_secrets(self):
        async def failing(*args):
            raise RuntimeError("private-url-and-secret")
        registry = ToolRegistry([self.registration(handler=failing)], authorize=lambda *a: True)
        receipt = await registry.dispatch("echo", {"value": 1}, self.context)
        self.assertEqual(receipt["outcome"], "UNKNOWN_OUTCOME")
        self.assertNotIn("private-url-and-secret", str(receipt))

    async def test_trusted_not_executed_signal_is_explicit(self):
        async def rejected(*args):
            raise KnownNotExecuted()
        registry = ToolRegistry([self.registration(handler=rejected)], authorize=lambda *a: True)
        receipt = await registry.dispatch("echo", {"value": 1}, self.context)
        self.assertEqual(receipt["outcome"], "NOT_EXECUTED")
        self.assertTrue(receipt["retry"]["allowed"])

    async def test_invalid_return_is_unknown_and_withheld(self):
        async def invalid(*args):
            return {"value": math.nan}
        registry = ToolRegistry([self.registration(handler=invalid)], authorize=lambda *a: True)
        receipt = await registry.dispatch("echo", {"value": 1}, self.context)
        self.assertEqual(receipt["outcome"], "UNKNOWN_OUTCOME")
        self.assertNotIn("result", receipt)

    async def test_zero_budget_never_authorizes_or_dispatches(self):
        authorizations = []
        registry = ToolRegistry([self.registration()], authorize=lambda *a: authorizations.append(a) or True)
        receipt = await registry.dispatch("echo", {"value": 1}, self.context, remaining_budget_ms=0)
        self.assertEqual(receipt["outcome"], "BUDGET_EXHAUSTED")
        self.assertEqual((authorizations, self.calls), ([], []))

    async def test_async_permission_failure_is_closed(self):
        async def authorize(*args):
            await asyncio.sleep(0)
            raise RuntimeError("private auth failure")
        registry = ToolRegistry([self.registration()], authorize=authorize)
        receipt = await registry.dispatch("echo", {"value": 1}, self.context)
        self.assertEqual(receipt["outcome"], "AUTHORIZATION_DENIED")
        self.assertEqual(self.calls, [])

    async def test_permission_timeout_does_not_dispatch(self):
        async def authorize(*args):
            await asyncio.sleep(10)
            return True
        registry = ToolRegistry([self.registration(timeout_ms=5)], authorize=authorize)
        receipt = await registry.dispatch("echo", {"value": 1}, self.context)
        self.assertEqual(receipt["outcome"], "AUTHORIZATION_DENIED")
        self.assertEqual(self.calls, [])

    async def test_concurrent_handlers_are_bounded(self):
        active = peak = 0
        async def handler(*args):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return "done"
        registry = ToolRegistry([self.registration(handler=handler)],
                                authorize=lambda *a: True, max_inflight=2)
        results = await asyncio.gather(*(registry.dispatch("echo", {"value": n}, self.context)
                                        for n in range(7)))
        self.assertEqual(peak, 2)
        self.assertTrue(all(r["outcome"] == "SUCCESS" for r in results))

    async def test_caller_cancellation_propagates(self):
        started = asyncio.Event()
        async def handler(*args):
            started.set()
            await asyncio.sleep(10)
        registry = ToolRegistry([self.registration(handler=handler)], authorize=lambda *a: True)
        call = asyncio.create_task(registry.dispatch("echo", {"value": 1}, self.context))
        await started.wait()
        call.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await call


if __name__ == "__main__":
    unittest.main()
