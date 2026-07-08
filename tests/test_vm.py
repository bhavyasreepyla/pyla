"""Parity tests: the bytecode VM must behave identically to the tree-walker."""

import glob
import io
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyla import run
from pyla.vm import vm_run
from pyla import objects as obj
from pyla.errors import PylaRuntimeError

EXAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")


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


PARITY_SOURCES = [
    # arithmetic & numeric tower
    "2 + 3 * 4",
    "7 / 2",
    "4 / 2",
    "17 % 5",
    "-5 + 3.5",
    "1 + 2.0",
    # strings, bools, comparisons
    '"foo" + "bar"',
    '"ab" < "ac"',
    "1 <= 1 and 2 != 3",
    "!nil",
    "!!0",
    # short circuit (right side would explode)
    "false and (1 / 0)",
    "true or (1 / 0)",
    "nil or 7",
    "1 and 2",
    # if as expression
    "if (1 < 2) { 10 } else { 20 }",
    "if (false) { 10 }",
    "let sign = fn(n) { if (n < 0) { -1 } else if (n > 0) { 1 } else { 0 } }; sign(0) - sign(-9) + sign(4)",
    # let / assignment
    "let x = 5; x = x + 1; x",
    "let a = 1; let b = 2; a = b = 10; a + b",
    # while / for / break / continue
    "let i = 0; let s = 0; while (i < 10) { i = i + 1; if (i % 2 == 0) { continue; } s = s + i; } s",
    "let s = 0; for (let i = 0; i < 100; i = i + 1) { if (i == 5) { break; } s = s + i; } s",
    "let s = 0; for (let i = 0; i < 6; i = i + 1) { if (i % 2 == 0) { continue; } s = s + i; } s",
    "let n = 0; while (true) { n = n + 1; if (n >= 7) { break; } } n",
    # nested loops with break/continue
    ("let total = 0; "
     "for (let i = 0; i < 5; i = i + 1) { "
     "  for (let j = 0; j < 5; j = j + 1) { "
     "    if (j == 3) { break; } "
     "    if (i == 2) { continue; } "
     "    total = total + 1; } } total"),
    # functions, recursion, closures
    "let fib = fn(n) { if (n < 2) { n } else { fib(n-1) + fib(n-2) } }; fib(12)",
    "let sq = fn(n) { n * n }; sq(sq(3))",
    "let make = fn(x) { fn(y) { x + y } }; let add3 = make(3); add3(4)",
    "let c = fn() { let n = 0; fn() { n = n + 1; n } }(); c(); c(); c()",
    "let apply = fn(f, x) { f(x) }; apply(fn(v) { v * 2 }, 21)",
    "let f = fn() { return 1; 2 }; f()",
    "let f = fn() {}; f()",
    # arrays / hashes / indexing
    "[1, 2, 3][1]",
    "[1, 2, 3][-1]",
    "[1, 2, 3][99]",
    "let a = [1, 2, 3]; a[0] = 99; a",
    'let h = {"a": 1}; h["b"] = 2; [h["a"], h["b"], h["missing"]]',
    'let h = {1: "one", true: "yes"}; [h[1], h[true]]',
    "let a = [[1, 2], [3, 4]]; a[1][0] = 30; a",
    'let s = "Pyla"; s[0] + s[-1]',
    # builtins
    "len([1, 2, 3]) + len(\"abcd\")",
    "let a = [1]; push(a, 2); pop(a); a",
    "range(0, 10, 3)",
    "min([4, 2, 9])",
    "max(1, 7, 3)",
    "abs(-3.5)",
    'int("42") + int(3.9)',
    "str(123) + str(true)",
    "chr(72) + chr(105)",
    'ord("A")',
    'contains([1, 2, 3], 2)',
    'contains("hello", "ell")',
    'let h = {"a": 1, "b": 2}; delete(h, "a"); keys(h)',
    # return at top level
    "let x = 1; return 42; x",
]

ERROR_SOURCES = [
    "1 / 0",
    "17 % 0",
    '1 + "a"',
    "nope + 1",
    "x = 5",
    "let x = 5; x(1)",
    "let f = fn(a, b) { a }; f(1)",
    "[1, 2][true]",
    "let a = [1]; a[5] = 0;",
    "-true",
]


class VMParityTests(unittest.TestCase):
    def test_values_match_tree_walker(self):
        for src in PARITY_SOURCES:
            with self.subTest(src=src):
                tree = unwrap(run(src))
                vm = unwrap(vm_run(src))
                self.assertEqual(vm, tree)
                # types must match too (int vs float, etc.)
                self.assertEqual(type(vm), type(tree))

    def test_errors_match_tree_walker(self):
        for src in ERROR_SOURCES:
            with self.subTest(src=src):
                with self.assertRaises(PylaRuntimeError) as tree_err:
                    run(src)
                with self.assertRaises(PylaRuntimeError) as vm_err:
                    vm_run(src)
                self.assertEqual(str(vm_err.exception), str(tree_err.exception))

    # Heavy demos verified for parity manually; skipped here to keep the
    # suite fast (neural_net.pyla trains for thousands of epochs).
    SLOW_EXAMPLES = {"neural_net.pyla"}

    def test_example_programs_produce_identical_output(self):
        paths = sorted(glob.glob(os.path.join(EXAMPLES_DIR, "*.pyla")))
        self.assertTrue(paths, "no example programs found")
        for path in paths:
            if os.path.basename(path) in self.SLOW_EXAMPLES:
                continue
            with self.subTest(example=os.path.basename(path)):
                with open(path, "r", encoding="utf-8") as f:
                    source = f.read()
                tree_out = io.StringIO()
                with redirect_stdout(tree_out):
                    run(source)
                vm_out = io.StringIO()
                with redirect_stdout(vm_out):
                    vm_run(source)
                self.assertEqual(vm_out.getvalue(), tree_out.getvalue())

    def test_deep_recursion_beyond_python_limit(self):
        # The VM keeps its own frame list, so Pyla recursion depth is not
        # limited by the Python recursion limit the tree-walker inherits.
        depth = sys.getrecursionlimit() * 2
        src = ("let count = fn(n) { if (n == 0) { 0 } else { count(n - 1) + 1 } }; "
               f"count({depth})")
        result = vm_run(src)
        self.assertEqual(result.value, depth)


if __name__ == "__main__":
    unittest.main()
