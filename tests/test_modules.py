"""Tests for the module system, dot access, and the string toolkit.

Every behaviour is checked on BOTH engines, including functions that cross
the engine boundary (VM code calling tree-walker module functions and
tree-walker modules receiving VM closures as callbacks).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyla import run
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


class DotAccessTests(BothEnginesMixin, unittest.TestCase):
    def test_dot_read(self):
        self.check('let h = {"a": 1, "b": 2}; h.a + h.b', 3)

    def test_dot_write(self):
        self.check('let h = {"x": 1}; h.x = 10; h.x', 10)

    def test_dot_chained(self):
        self.check('let h = {"inner": {"v": 7}}; h.inner.v', 7)

    def test_dot_method_call(self):
        self.check('let h = {"f": fn(x) { x * 2 }}; h.f(21)', 42)

    def test_dot_missing_key_is_nil(self):
        self.check('let h = {}; h.nothing', None)


class StringBuiltinTests(BothEnginesMixin, unittest.TestCase):
    def test_split_join(self):
        self.check('split("a,b,c", ",")', ["a", "b", "c"])
        self.check('split("abc", "")', ["a", "b", "c"])
        self.check('join(["x", "y"], "-")', "x-y")

    def test_case_and_trim(self):
        self.check('upper("pyla")', "PYLA")
        self.check('lower("PYLA")', "pyla")
        self.check('trim("  hi  ")', "hi")

    def test_replace_and_slice(self):
        self.check('replace("aaa", "a", "b")', "bbb")
        self.check('slice("language", 0, 4)', "lang")
        self.check('slice([1, 2, 3, 4], 1, 3)', [2, 3])
        self.check('slice([1, 2, 3, 4], 2)', [3, 4])
        self.check('slice("abcdef", -2)', "ef")


class ModuleTests(BothEnginesMixin, unittest.TestCase):
    def test_import_std_list(self):
        self.check('let l = import("std/list"); '
                   'l.sum(l.map([1, 2, 3], fn(x) { x * 10 }))', 60)

    def test_import_std_math(self):
        self.check('let m = import("std/math"); m.pow(2, 16)', 65536)
        self.check('let m = import("std/math"); m.gcd(48, 18)', 6)
        self.check('let m = import("std/math"); m.factorial(6)', 720)
        self.check('let m = import("std/math"); '
                   'abs(m.sqrt(2) * m.sqrt(2) - 2) < 0.0000001', True)

    def test_sort_via_module(self):
        self.check('let l = import("std/list"); l.sort([3, 1, 2])', [1, 2, 3])
        self.check('let l = import("std/list"); '
                   'l.sort_by([1, 2, 3], fn(a, b) { a > b })', [3, 2, 1])

    def test_import_is_cached(self):
        # Two imports of the same module return the same hash object.
        src = ('let a = import("std/list"); let b = import("std/list"); '
               'a.marker = 42; b.marker')
        self.check(src, 42)

    def test_module_not_found(self):
        for name, engine in ENGINES:
            with self.subTest(engine=name):
                with self.assertRaises(PylaRuntimeError) as ctx:
                    engine('import("no/such/module")')
                self.assertIn("module not found", str(ctx.exception))

    def test_vm_callbacks_into_module_functions(self):
        # list.filter is a tree-walker function; the predicate is a VM
        # closure. This exercises the engine boundary in both directions.
        result = vm_run('let l = import("std/list"); '
                        'l.filter(range(10), fn(x) { x % 3 == 0 })')
        self.assertEqual(unwrap(result), [0, 3, 6, 9])


if __name__ == "__main__":
    unittest.main()
