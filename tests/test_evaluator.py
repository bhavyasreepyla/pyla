import io
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyla import run
from pyla import objects as obj
from pyla.errors import PylaRuntimeError


def val(source):
    """Run source and return the final value as a native Python value."""
    result = run(source)
    return unwrap(result)


def unwrap(o):
    if isinstance(o, (obj.Integer, obj.Float, obj.String, obj.Boolean)):
        return o.value
    if isinstance(o, obj.Nil):
        return None
    if isinstance(o, obj.Array):
        return [unwrap(e) for e in o.elements]
    if isinstance(o, obj.Hash):
        return {unwrap(k): unwrap(v) for k, v in o.pairs.values()}
    return o


def output_of(source):
    buf = io.StringIO()
    with redirect_stdout(buf):
        run(source)
    return buf.getvalue()


class EvalBasicsTests(unittest.TestCase):
    def test_arithmetic(self):
        self.assertEqual(val("2 + 3 * 4"), 14)
        self.assertEqual(val("(2 + 3) * 4"), 20)
        self.assertEqual(val("10 - 2 - 3"), 5)
        self.assertEqual(val("17 % 5"), 2)
        self.assertEqual(val("-5 + 3"), -2)

    def test_integer_float_tower(self):
        self.assertIsInstance(run("4 / 2"), obj.Integer)   # exact -> int
        self.assertEqual(val("4 / 2"), 2)
        self.assertIsInstance(run("7 / 2"), obj.Float)      # inexact -> float
        self.assertEqual(val("7 / 2"), 3.5)
        self.assertIsInstance(run("1 + 2.0"), obj.Float)
        self.assertEqual(val("2.5 * 2"), 5.0)

    def test_booleans_and_comparisons(self):
        self.assertEqual(val("1 < 2"), True)
        self.assertEqual(val("2 <= 2"), True)
        self.assertEqual(val("3 == 3"), True)
        self.assertEqual(val("3 != 3"), False)
        self.assertEqual(val('"a" < "b"'), True)
        self.assertEqual(val("!true"), False)
        self.assertEqual(val("!nil"), True)
        self.assertEqual(val("!0"), False)  # 0 is truthy; only nil/false are falsy

    def test_string_ops(self):
        self.assertEqual(val('"foo" + "bar"'), "foobar")
        self.assertEqual(val('"ab" == "ab"'), True)
        self.assertEqual(val('len("hello")'), 5)

    def test_logical_short_circuit(self):
        # right side must not run if left decides the result
        self.assertEqual(val("false and (1 / 0)"), False)
        self.assertEqual(val("true or (1 / 0)"), True)
        self.assertEqual(val("nil or 7"), 7)
        self.assertEqual(val("1 and 2"), 2)


class EvalControlFlowTests(unittest.TestCase):
    def test_if_expression_value(self):
        self.assertEqual(val("if (true) { 10 } else { 20 }"), 10)
        self.assertEqual(val("if (false) { 10 } else { 20 }"), 20)
        self.assertEqual(val("if (false) { 10 }"), None)

    def test_else_if_chain(self):
        prog = "let sign = fn(n) { if (n < 0) { -1 } else if (n > 0) { 1 } else { 0 } };"
        self.assertEqual(val(prog + " sign(-8)"), -1)
        self.assertEqual(val(prog + " sign(8)"), 1)
        self.assertEqual(val(prog + " sign(0)"), 0)

    def test_while_loop(self):
        self.assertEqual(val("let i = 0; let s = 0; "
                             "while (i < 5) { s = s + i; i = i + 1; } s"), 10)

    def test_for_loop(self):
        self.assertEqual(val("let s = 0; for (let i = 1; i <= 4; i = i + 1) { s = s + i; } s"), 10)

    def test_break_and_continue(self):
        self.assertEqual(val("let s = 0; "
                             "for (let i = 0; i < 100; i = i + 1) { "
                             "  if (i == 5) { break; } s = s + i; } s"), 10)
        self.assertEqual(val("let s = 0; "
                             "for (let i = 0; i < 6; i = i + 1) { "
                             "  if (i % 2 == 0) { continue; } s = s + i; } s"), 9)


class EvalFunctionTests(unittest.TestCase):
    def test_recursion(self):
        prog = "let fib = fn(n) { if (n < 2) { n } else { fib(n-1) + fib(n-2) } };"
        self.assertEqual(val(prog + " fib(10)"), 55)

    def test_closures_capture_environment(self):
        prog = """
        let make_adder = fn(x) { fn(y) { x + y } };
        let add10 = make_adder(10);
        add10(5)
        """
        self.assertEqual(val(prog), 15)

    def test_closure_private_state(self):
        prog = """
        let counter = fn() { let n = 0; fn() { n = n + 1; n } };
        let c = counter();
        c(); c(); c()
        """
        self.assertEqual(val(prog), 3)

    def test_first_class_functions(self):
        prog = """
        let apply = fn(f, x) { f(x) };
        apply(fn(n) { n * n }, 7)
        """
        self.assertEqual(val(prog), 49)

    def test_explicit_return_stops_early(self):
        prog = "let f = fn() { return 1; return 2; }; f()"
        self.assertEqual(val(prog), 1)

    def test_wrong_arity_errors(self):
        with self.assertRaises(PylaRuntimeError):
            run("let f = fn(a, b) { a + b }; f(1)")


class EvalDataStructureTests(unittest.TestCase):
    def test_arrays(self):
        self.assertEqual(val("[1, 2, 3][1]"), 2)
        self.assertEqual(val("let a = [1, 2, 3]; a[0] = 99; a"), [99, 2, 3])
        self.assertEqual(val("let a = [1]; push(a, 2); push(a, 3); a"), [1, 2, 3])
        self.assertEqual(val("first([9, 8, 7])"), 9)
        self.assertEqual(val("last([9, 8, 7])"), 7)
        self.assertEqual(val("rest([1, 2, 3])"), [2, 3])
        self.assertEqual(val("[1, 2, 3][-1]"), 3)
        self.assertEqual(val("[1, 2, 3][99]"), None)  # out of range -> nil

    def test_hashes(self):
        self.assertEqual(val('{"a": 1, "b": 2}["b"]'), 2)
        self.assertEqual(val('let h = {}; h["x"] = 5; h["x"]'), 5)
        self.assertEqual(val('{1: "one", 2: "two"}[2]'), "two")
        self.assertEqual(val('{true: "yes"}[true]'), "yes")
        self.assertEqual(val('{"a": 1}["missing"]'), None)
        self.assertEqual(val('contains({"a": 1}, "a")'), True)
        self.assertEqual(val('let h = {"a":1,"b":2}; delete(h, "a"); keys(h)'), ["b"])

    def test_builtins(self):
        self.assertEqual(val("range(5)"), [0, 1, 2, 3, 4])
        self.assertEqual(val("range(2, 5)"), [2, 3, 4])
        self.assertEqual(val("range(0, 10, 2)"), [0, 2, 4, 6, 8])
        self.assertEqual(val("abs(-7)"), 7)
        self.assertEqual(val("min([3, 1, 2])"), 1)
        self.assertEqual(val("max(3, 9, 5)"), 9)
        self.assertEqual(val('int("42")'), 42)
        self.assertEqual(val("int(3.9)"), 3)
        self.assertEqual(val('float("2.5")'), 2.5)
        self.assertEqual(val("str(123)"), "123")
        self.assertEqual(val('type([1,2])'), "array")

    def test_print_output(self):
        self.assertEqual(output_of('print("hi", 1, true)'), "hi 1 true\n")
        self.assertEqual(output_of('write("a"); write("b")'), "ab")


class EvalErrorTests(unittest.TestCase):
    def test_type_mismatch(self):
        with self.assertRaises(PylaRuntimeError):
            run('1 + "a"')

    def test_division_by_zero(self):
        with self.assertRaises(PylaRuntimeError):
            run("1 / 0")

    def test_unknown_identifier(self):
        with self.assertRaises(PylaRuntimeError):
            run("nope + 1")

    def test_assign_to_undeclared(self):
        with self.assertRaises(PylaRuntimeError):
            run("x = 5")

    def test_calling_non_function(self):
        with self.assertRaises(PylaRuntimeError):
            run("let x = 5; x(1)")

    def test_error_reports_line(self):
        try:
            run("let a = 1;\nlet b = 2;\nc + 1;")
        except PylaRuntimeError as e:
            self.assertEqual(e.line, 3)
        else:
            self.fail("expected PylaRuntimeError")


if __name__ == "__main__":
    unittest.main()
