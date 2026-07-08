"""Tests for the v0.3 features: pipeline operator, file I/O, script args,
and runtime stack traces. Everything is checked on both engines."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyla import run, parse
from pyla.vm import vm_run
from pyla import objects as obj
from pyla import builtins
from pyla.errors import PylaRuntimeError

ENGINES = [("tree-walker", run), ("vm", vm_run)]


def unwrap(o):
    if isinstance(o, (obj.Integer, obj.Float, obj.String, obj.Boolean)):
        return o.value
    if isinstance(o, obj.Nil):
        return None
    if isinstance(o, obj.Array):
        return [unwrap(e) for e in o.elements]
    return o.inspect()


class BothEnginesMixin:
    def check(self, src, expected):
        for name, engine in ENGINES:
            with self.subTest(engine=name, src=src):
                self.assertEqual(unwrap(engine(src)), expected)


class PipelineTests(BothEnginesMixin, unittest.TestCase):
    def test_desugaring(self):
        cases = {
            "x |> f": "f(x)",
            "x |> f(a)": "f(x, a)",
            "x |> f |> g": "g(f(x))",
            "x |> f(a) |> g(b)": "g(f(x, a), b)",
            "x |> h.f(a)": "(h[\"f\"])(x, a)",
            "x + 1 |> f": "f((x + 1))",
        }
        for src, expected in cases.items():
            program, errors = parse(src)
            self.assertFalse(errors, f"parse errors for {src!r}")
            self.assertEqual(str(program.statements[0].expression), expected,
                             msg=f"for source {src!r}")

    def test_pipeline_evaluation(self):
        self.check("5 |> fn(x) { x * 2 } |> fn(x) { x + 1 }", 11)
        self.check('"  Pyla  " |> trim |> upper', "PYLA")
        self.check("let add = fn(a, b) { a + b }; 40 |> add(2)", 42)
        self.check('let l = import("std/list"); '
                   "range(1, 6) |> l.map(fn(x) { x * x }) |> l.sum()", 55)

    def test_pipeline_precedence_vs_assignment(self):
        # `=` binds looser than `|>`: the whole pipeline is the value.
        self.check("let y = 3 |> fn(x) { x * 10 }; y", 30)


class FileIOTests(BothEnginesMixin, unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "t.txt").replace("\\", "/")

    def test_write_read_append_exists(self):
        src = (f'write_file("{self.path}", "hello");'
               f'append_file("{self.path}", " world");'
               f'[read_file("{self.path}"), exists("{self.path}"), '
               f'exists("{self.path}.nope")]')
        self.check(src, ["hello world", True, False])

    def test_read_missing_file_errors(self):
        for name, engine in ENGINES:
            with self.subTest(engine=name):
                with self.assertRaises(PylaRuntimeError) as ctx:
                    engine(f'read_file("{self.path}.missing")')
                self.assertIn("cannot read file", str(ctx.exception))

    def test_args_builtin(self):
        old = list(builtins.SCRIPT_ARGS)
        builtins.SCRIPT_ARGS[:] = ["a", "b"]
        try:
            self.check("args()", ["a", "b"])
        finally:
            builtins.SCRIPT_ARGS[:] = old


class StackTraceTests(unittest.TestCase):
    SRC = ("let inner = fn(x) { x + \"boom\" };\n"
           "let outer = fn() { inner(1) };\n"
           "outer();")

    def test_stack_attached_on_both_engines(self):
        for name, engine in ENGINES:
            with self.subTest(engine=name):
                with self.assertRaises(PylaRuntimeError) as ctx:
                    engine(self.SRC)
                stack = ctx.exception.pyla_stack
                self.assertIsNotNone(stack)
                self.assertEqual([s[0] for s in stack], ["outer", "inner"])

    def test_format_error_shows_source_and_stack(self):
        from pyla.diagnostics import format_error
        with self.assertRaises(PylaRuntimeError) as ctx:
            vm_run(self.SRC)
        text = format_error(ctx.exception, self.SRC, "demo.pyla")
        self.assertIn("type mismatch", text)
        self.assertIn('x + "boom"', text)      # source line shown
        self.assertIn("in outer", text)
        self.assertIn("in inner", text)


class BomToleranceTests(unittest.TestCase):
    def test_module_with_bom_loads(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "bommed.pyla")
        with open(p, "w", encoding="utf-8-sig") as f:
            f.write("let answer = 42;")
        src = f'import("{p.replace(chr(92), "/")}").answer'
        self.assertEqual(unwrap(run(src)), 42)


if __name__ == "__main__":
    unittest.main()
