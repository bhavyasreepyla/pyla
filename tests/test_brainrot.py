"""Tests for brainrot mode (the Gen Z dialect) and the fact that it is
strictly opt-in: slang words remain ordinary identifiers in normal mode."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyla import run
from pyla.vm import vm_run
from pyla import objects as obj

ENGINES = [("tree-walker", run), ("vm", vm_run)]


def unwrap(o):
    if isinstance(o, (obj.Integer, obj.Float, obj.String, obj.Boolean)):
        return o.value
    if isinstance(o, obj.Nil):
        return None
    if isinstance(o, obj.Array):
        return [unwrap(e) for e in o.elements]
    return o.inspect()


class BrainrotTests(unittest.TestCase):
    def check(self, src, expected):
        for name, engine in ENGINES:
            with self.subTest(engine=name, src=src):
                self.assertEqual(unwrap(engine(src, slang=True)), expected)

    def test_declarations_and_functions(self):
        self.check("fr x = 5; fr double = cook(n) { yeet n * 2 }; double(x)", 10)

    def test_vibecheck_chain(self):
        src = ("fr judge = cook(n) { "
               "vibecheck (n > 10) { \"big\" } nah vibecheck (n > 0) { \"smol\" } "
               "nah { \"negative\" } }; "
               "judge(50) + judge(5) + judge(-1)")
        self.check(src, "bigsmolnegative")

    def test_loops_dip_skip(self):
        self.check("fr s = 0; farm (fr i = 0; i < 10; i = i + 1) { "
                   "vibecheck (i == 7) { dip; } "
                   "vibecheck (i % 2 == 0) { skip; } s = s + i; } s", 9)
        self.check("fr n = 0; grind (nocap) { n = n + 1; "
                   "vibecheck (n >= 3) { dip; } } n", 3)

    def test_literals(self):
        self.check("[nocap, cap, ghosted]", [True, False, None])
        self.check("!cap and nocap", True)

    def test_ident_aliases_resolve_to_builtins(self):
        # yap is print; it returns nil but must be callable.
        self.check('yap("test") == ghosted', True)
        self.check('sheesh(nocap, "fine"); 1', 1)

    def test_recursion_in_slang(self):
        self.check("fr fib = cook(n) { vibecheck (n < 2) { yeet n; } "
                   "yeet fib(n-1) + fib(n-2); }; fib(10)", 55)

    def test_pipelines_still_work(self):
        self.check("fr sq = cook(x) { x * x }; 5 |> sq |> sq", 625)

    def test_slang_words_are_identifiers_in_normal_mode(self):
        # Without slang=True these are just variable names.
        for name, engine in ENGINES:
            with self.subTest(engine=name):
                self.assertEqual(
                    unwrap(engine("let cap = 1; let yeet = 2; cap + yeet")), 3)

    def test_normal_keywords_still_work_in_slang_mode(self):
        # The dialect is additive: let/fn/if remain valid.
        self.check("let a = 1; fr b = 2; a + b", 3)


if __name__ == "__main__":
    unittest.main()
