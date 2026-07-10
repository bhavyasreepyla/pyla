"""Tests for the pipeline flight recorder (`pyla --trace`).

The tracer must report every |> stage with identical output from both
engines, and must be completely silent when disabled."""

import io
import os
import sys
import unittest
from contextlib import redirect_stderr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyla import run
from pyla.vm import vm_run
from pyla import diagnostics

SRC = """let l = import("std/list");
range(1, 6)
    |> l.map(fn(x) { x * x })
    |> l.filter(fn(x) { x > 5 })
    |> l.sum()
    |> print;
"  Pyla  " |> trim |> upper |> print;
"""


def trace_of(engine):
    diagnostics.TRACE_PIPES = True
    buf = io.StringIO()
    try:
        with redirect_stderr(buf):
            engine(SRC)
    finally:
        diagnostics.TRACE_PIPES = False
    return buf.getvalue()


class TraceTests(unittest.TestCase):
    def test_engines_emit_identical_traces(self):
        tree = trace_of(run)
        vm = trace_of(vm_run)
        self.assertEqual(vm, tree)

    def test_trace_reports_every_stage_with_values(self):
        text = trace_of(vm_run)
        lines = [l for l in text.splitlines() if l.startswith("|>")]
        self.assertEqual(len(lines), 7)  # 4 stages + 3 string stages
        self.assertIn("l.map", text)          # dotted label, not desugared
        self.assertIn("[1, 4, 9, 16, 25]", text)
        self.assertIn("l.filter", text)
        self.assertIn("[9, 16, 25]", text)
        self.assertIn("l.sum", text)
        self.assertIn("=>  50", text)
        self.assertIn("trim", text)
        self.assertIn("upper", text)
        self.assertIn("PYLA", text)
        self.assertNotIn('["map"]', text)     # the ugly desugared form

    def test_silent_when_disabled(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            run(SRC)
            vm_run(SRC)
        self.assertEqual(buf.getvalue(), "")

    def test_non_pipe_calls_are_not_traced(self):
        diagnostics.TRACE_PIPES = True
        buf = io.StringIO()
        try:
            with redirect_stderr(buf):
                vm_run("let f = fn(x) { x }; f(1); f(2);")
        finally:
            diagnostics.TRACE_PIPES = False
        self.assertEqual(buf.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
