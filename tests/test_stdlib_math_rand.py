"""Tests for the from-scratch transcendental math (exp/tanh/sigmoid) and the
seeded PRNG that the neural-network demo is built on. Both engines, and a
fast end-to-end check that a tiny network actually learns via backprop."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyla import run
from pyla.vm import vm_run

ENGINES = [("tree-walker", run), ("vm", vm_run)]


def num(src, engine):
    return engine(src).value


class MathTests(unittest.TestCase):
    def check_close(self, src, expected, tol=1e-9):
        for name, engine in ENGINES:
            with self.subTest(engine=name, src=src):
                self.assertAlmostEqual(num(src, engine), expected, delta=tol)

    def test_exp(self):
        self.check_close('import("std/math").exp(0)', 1.0)
        self.check_close('import("std/math").exp(1)', 2.718281828459045, tol=1e-9)
        self.check_close('import("std/math").exp(0 - 2)', 0.1353352832366127, tol=1e-9)
        self.check_close('import("std/math").exp(5)', 148.4131591025766, tol=1e-6)

    def test_sigmoid_and_tanh(self):
        self.check_close('import("std/math").sigmoid(0)', 0.5)
        self.check_close('import("std/math").tanh(0)', 0.0)
        self.check_close('import("std/math").tanh(1)', 0.7615941559557649, tol=1e-9)
        # sigmoid is symmetric about 0.5
        self.check_close('let m = import("std/math"); m.sigmoid(2) + m.sigmoid(0 - 2)', 1.0, tol=1e-9)


class RandTests(unittest.TestCase):
    def test_deterministic_same_seed(self):
        src = ('let r = import("std/rand"); let a = r.floats(123); '
               'let b = r.floats(123); [a() == b(), a() == b(), a() == b()]')
        for name, engine in ENGINES:
            with self.subTest(engine=name):
                out = [e.value for e in engine(src).elements]
                self.assertEqual(out, [True, True, True])

    def test_floats_in_range(self):
        src = ('let r = import("std/rand"); let g = r.floats(9); '
               'let ok = true; '
               'for (let i = 0; i < 200; i = i + 1) { let v = g(); '
               'if (v < 0 or v >= 1) { ok = false; } } ok')
        for name, engine in ENGINES:
            with self.subTest(engine=name):
                self.assertTrue(engine(src).value)

    def test_uniform_in_range(self):
        src = ('let r = import("std/rand"); let g = r.uniform(4); '
               'let ok = true; '
               'for (let i = 0; i < 200; i = i + 1) { let v = g(); '
               'if (v < 0 - 1 or v >= 1) { ok = false; } } ok')
        for name, engine in ENGINES:
            with self.subTest(engine=name):
                self.assertTrue(engine(src).value)


class TinyNetLearnsTests(unittest.TestCase):
    """A 30-epoch single-neuron net that learns logical AND -- proves the
    backprop math works, fast enough for the suite, identical on both engines."""

    SRC = """
    let m = import("std/math");
    let rand = import("std/rand");
    let X = [[0, 0], [0, 1], [1, 0], [1, 1]];
    let Y = [0, 0, 0, 1];
    let rng = rand.uniform(1);
    let w = [rng(), rng()];
    let b = rng();
    for (let e = 0; e < 400; e = e + 1) {
        for (let n = 0; n < 4; n = n + 1) {
            let x = X[n];
            let net = b + x[0] * w[0] + x[1] * w[1];
            let o = m.sigmoid(net);
            let d = 2.0 * (o - Y[n]) * o * (1.0 - o);
            w[0] = w[0] - 0.5 * d * x[0];
            w[1] = w[1] - 0.5 * d * x[1];
            b = b - 0.5 * d;
        }
    }
    let correct = 0;
    for (let n = 0; n < 4; n = n + 1) {
        let x = X[n];
        let o = m.sigmoid(b + x[0] * w[0] + x[1] * w[1]);
        let g = if (o > 0.5) { 1 } else { 0 };
        if (g == Y[n]) { correct = correct + 1; }
    }
    correct
    """

    def test_learns_and_on_both_engines(self):
        for name, engine in ENGINES:
            with self.subTest(engine=name):
                self.assertEqual(engine(self.SRC).value, 4)


if __name__ == "__main__":
    unittest.main()
