"""Behavioral API tests using a scripted backend and the real controller."""
import json
import unittest
from unittest.mock import patch

from nevso import Agent, Tool, format_trace


def emit(name, **arguments):
    return '<tool_call>' + json.dumps({"name": name, "arguments": arguments}) + '</tool_call>'


class Backend:
    def __init__(self, outputs, choice="read_a"):
        self.outputs = iter(outputs)
        self.choice = choice
        self.ranks = 0
        self.prompts = []
        self.closed = False
    def synchronize(self): pass
    def rank(self, request, language, tools, *args):
        self.ranks += 1
        return {"choice": self.choice, "probabilities": {
            s["function"]["name"]: 0.9 if s["function"]["name"] == self.choice else 0.1
            for s in tools}, "elapsed_ms": 1.0}
    def generate(self, messages):
        self.prompts.append(messages)
        return next(self.outputs), 5, False
    def close(self): self.closed = True


def tool(name, handler):
    return Tool(name, {"en": "Read value", "it": "Leggi valore"},
                {"type": "object", "properties": {"id": {"type": "string"}},
                 "required": ["id"]}, handler)


class ApiTests(unittest.TestCase):
    def test_rank_once_dispatch_localized_result_and_trace(self):
        calls = []
        backend = Backend([emit("read_a", id="X-1"), "Il valore è 6.4."])
        with Agent([tool("read_b", lambda **kw: {}),
                    tool("read_a", lambda **kw: calls.append(kw) or {"value": 6.4})], backend=backend) as a:
            row = a.run("Leggi X-1.", language="it")
        self.assertEqual(calls, [{"id": "X-1"}])
        self.assertEqual(backend.ranks, 1)
        self.assertEqual(row["trace"][0]["tool_order"], ["read_a", "read_b"])
        self.assertIn("Leggi valore", backend.prompts[0][0]["content"])
        self.assertIn('6.4', backend.prompts[1][-1]["content"])
        self.assertEqual(row["status"], "answered")
        self.assertIn("Nev initial choice: read_a", format_trace(row))
        self.assertFalse(backend.closed)  # Supplied backends are borrowed.
        with self.assertRaisesRegex(RuntimeError, "closed"):
            a.run("Read X-1")

    def test_selected_mode_cannot_execute_hidden_tool(self):
        calls = []
        b = Backend([emit("read_b", id="X-1"), "Unable."])
        with Agent([tool("read_a", lambda **kw: {}), tool("read_b", lambda **kw: calls.append(kw))],
                   backend=b, strategy="select") as a:
            row = a.run("Read X-1")
        self.assertEqual(row["trace"][0]["tool_order"], ["read_a"])
        self.assertEqual(calls, [])
        self.assertIn("unknown_tool", row["errors"])

    def test_entire_invalid_batch_rejected_before_handlers(self):
        for bad in [emit("read_a", id="INVENTED"), emit("read_a", id="X-1", extra=True)]:
            with self.subTest(bad=bad):
                calls = []
                b = Backend([emit("read_a", id="X-1") + bad, "Unable."])
                with Agent([tool("read_a", lambda **kw: calls.append(kw))], backend=b) as a:
                    row = a.run("Read X-1")
                self.assertFalse(calls)
                self.assertTrue(row["errors"])

    def test_dedup_cache_is_per_request_and_none_skips_nev(self):
        calls = []
        b = Backend([emit("read_a", id="X-1"), emit("read_a", id="X-1"), "Done.",
                     emit("read_a", id="X-1"), "Done."])
        with Agent([tool("read_a", lambda **kw: calls.append(kw) or {"value": 6.4})],
                   backend=b, strategy="none") as a:
            first = a.run("Read X-1")
            a.run("Read X-1")
        self.assertEqual(b.ranks, 0)
        self.assertEqual(len(calls), 2)
        self.assertTrue(first["trace"][1]["observations"][0]["cached"])

    def test_handler_errors_propagate_without_retry(self):
        calls = []
        def fail(**kw):
            calls.append(kw)
            raise RuntimeError("service unavailable")
        b = Backend([emit("read_a", id="X-1")])
        with Agent([tool("read_a", fail)], backend=b) as a:
            with self.assertRaisesRegex(RuntimeError, "service unavailable"):
                a.run("Read X-1")
        self.assertEqual(len(calls), 1)

    def test_non_json_handler_output_fails_loudly(self):
        b = Backend([emit("read_a", id="X-1")])
        with Agent([tool("read_a", lambda **kw: {"value": float("nan")})], backend=b) as a:
            with self.assertRaises(ValueError):
                a.run("Read X-1")

    def test_registry_validation_happens_before_backend_load(self):
        t = tool("read_a", lambda **kw: {})
        with patch("nevso.api._load", side_effect=AssertionError("Must not load")):
            for tools in ([], [t, t], [object()]):
                with self.assertRaises(ValueError): Agent(tools)
        with self.assertRaises(ValueError): tool("__answer__", lambda **kw: {})

    def test_invalid_requests_do_not_touch_backend(self):
        b = Backend([])
        with Agent([tool("read_a", lambda **kw: {})], backend=b) as a:
            for kw in ({"request": ""}, {"request": "X-1", "language": "fr"},
                       {"request": "X-1", "strategy": "auto"}):
                with self.assertRaises(ValueError): a.run(**kw)
        self.assertEqual(b.ranks, 0)

    def test_owned_backend_closed_on_exception_and_double_close_safe(self):
        b = Backend([emit("read_a", id="X-1")])
        import nevso.api as api
        real_load = api._load
        def loader(path, name):
            if name == "_nevso_cpu_backend":
                class Module:
                    @staticmethod
                    def Backend(**kw): return b
                return Module
            return real_load(path, name)
        def fail(**kw): raise RuntimeError("failed")
        with patch("nevso.api._load", side_effect=loader):
            with self.assertRaisesRegex(RuntimeError, "failed"):
                with Agent([tool("read_a", fail)]) as a: a.run("Read X-1")
        self.assertTrue(b.closed)
        a.close()


if __name__ == "__main__":
    unittest.main()
