"""Tests for the 'loved language' features: string interpolation,
'did you mean' hints, and attempt() (errors as values). Both engines."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyla import run, parse
from pyla.vm import vm_run
from pyla import objects as obj
from pyla.errors import PylaRuntimeError

ENGINES = [("tree-walker", run), ("vm", vm_run)]


def unwrap(o):
    if isinstance(o, (obj.Integer, obj.Float, obj.String, obj.Boolean)):
        return o.value
    if isinstance(o, obj.Nil):
        return None
    if isinstance(o, obj.Array):
        return [unwrap(e) for e in o.elements]
    if isinstance(o, obj.Hash):
        return {unwrap(k): unwrap(v) for k, v in o.pairs.values()}
    return o.inspect()


class BothEnginesMixin:
    def check(self, src, expected):
        for name, engine in ENGINES:
            with self.subTest(engine=name, src=src):
                self.assertEqual(unwrap(engine(src)), expected)


class InterpolationTests(BothEnginesMixin, unittest.TestCase):
    def test_basic(self):
        self.check('let n = "world"; "hello ${n}"', "hello world")

    def test_expressions_inside(self):
        self.check('let x = 6; "${x} * 7 = ${x * 7}"', "6 * 7 = 42")
        self.check('let a = [1, 2, 3]; "last=${a[-1]}, len=${len(a)}"',
                   "last=3, len=3")
        self.check('let h = {"k": "v"}; "got ${h.k}"', "got v")

    def test_calls_and_pipes_inside(self):
        self.check('"loud: ${upper("hey")}"', "loud: HEY")
        self.check('"sum: ${range(1, 4) |> len}"', "sum: 3")

    def test_string_literal_inside_interpolation(self):
        self.check('"x${"y"}z"', "xyz")

    def test_only_expression(self):
        self.check('"${1 + 1}"', "2")

    def test_adjacent_and_multiple(self):
        self.check('let a = 1; let b = 2; "${a}${b}"', "12")

    def test_escape_dollar(self):
        self.check(r'"literal \${nope}"', "literal ${nope}")
        self.check('"plain $ sign"', "plain $ sign")

    def test_non_string_values_coerced(self):
        self.check('"v=${nil}, b=${true}, f=${3.5}"', "v=nil, b=true, f=3.5")

    def test_parse_error_inside_reported(self):
        _, errors = parse('"bad ${1 +}"')
        self.assertTrue(errors)
        self.assertIn("interpolation", str(errors[0]))


class DidYouMeanTests(unittest.TestCase):
    def test_suggests_local_variable(self):
        for name, engine in ENGINES:
            with self.subTest(engine=name):
                with self.assertRaises(PylaRuntimeError) as ctx:
                    engine("let counter = 1; countr")
                self.assertIn("did you mean 'counter'?", str(ctx.exception))

    def test_suggests_builtin(self):
        for name, engine in ENGINES:
            with self.subTest(engine=name):
                with self.assertRaises(PylaRuntimeError) as ctx:
                    engine("prnt(1)")
                self.assertIn("did you mean 'print'?", str(ctx.exception))

    def test_no_suggestion_for_distant_names(self):
        for name, engine in ENGINES:
            with self.subTest(engine=name):
                with self.assertRaises(PylaRuntimeError) as ctx:
                    engine("zzqqxx")
                self.assertNotIn("did you mean", str(ctx.exception))

    def test_engines_agree_on_message(self):
        msgs = []
        for _, engine in ENGINES:
            try:
                engine("let value = 1; vlaue")
            except PylaRuntimeError as e:
                msgs.append(str(e))
        self.assertEqual(msgs[0], msgs[1])


class AttemptTests(BothEnginesMixin, unittest.TestCase):
    def test_success(self):
        self.check("let r = attempt(fn() { 6 * 7 }); [r.ok, r.value, r.error]",
                   [True, 42, None])

    def test_caught_error(self):
        self.check('let r = attempt(fn() { 1 / 0 }); [r.ok, r.value, r.error]',
                   [False, None, "division by zero"])

    def test_caught_assert(self):
        self.check('let r = attempt(fn() { assert(false, "nope") }); r.error',
                   "nope")

    def test_program_continues_after_attempt(self):
        self.check('let r = attempt(fn() { missing_fn() }); '
                   'if (r.ok) { "fine" } else { "recovered" }', "recovered")

    def test_pipes(self):
        self.check('fn() { 10 / 2 } |> attempt |> fn(r) { r.value }', 5)


if __name__ == "__main__":
    unittest.main()
