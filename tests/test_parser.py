import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyla.parser import Parser
from pyla import ast_nodes as ast


def parse(source):
    p = Parser(source)
    program = p.parse_program()
    if p.errors:
        raise AssertionError("unexpected parse errors: " +
                             "; ".join(str(e) for e in p.errors))
    return program


def parse_with_errors(source):
    p = Parser(source)
    p.parse_program()
    return p.errors


class ParserTests(unittest.TestCase):
    def test_let_and_return(self):
        prog = parse("let x = 5; return x;")
        self.assertIsInstance(prog.statements[0], ast.LetStatement)
        self.assertEqual(prog.statements[0].name.value, "x")
        self.assertIsInstance(prog.statements[1], ast.ReturnStatement)

    def test_operator_precedence(self):
        cases = {
            "1 + 2 * 3": "(1 + (2 * 3))",
            "-a * b": "((-a) * b)",
            "1 + 2 + 3": "((1 + 2) + 3)",
            "2 * 3 + 4 == 10": "(((2 * 3) + 4) == 10)",
            "a < b == c > d": "((a < b) == (c > d))",
            "!(true == false)": "(!(true == false))",
            "a + b * c % d": "(a + ((b * c) % d))",
            "a and b or c": "((a and b) or c)",
            "(1 + 2) * 3": "((1 + 2) * 3)",
        }
        for src, expected in cases.items():
            prog = parse(src)
            self.assertEqual(str(prog.statements[0].expression), expected,
                             msg=f"for source {src!r}")

    def test_assignment_is_right_associative(self):
        prog = parse("a = b = 3")
        expr = prog.statements[0].expression
        self.assertIsInstance(expr, ast.AssignExpression)
        self.assertEqual(str(expr), "(a = (b = 3))")

    def test_if_else_and_else_if(self):
        prog = parse("if (x < 0) { -1 } else if (x == 0) { 0 } else { 1 }")
        expr = prog.statements[0].expression
        self.assertIsInstance(expr, ast.IfExpression)
        self.assertIsInstance(expr.alternative, ast.IfExpression)

    def test_function_literal_and_call(self):
        prog = parse("let add = fn(a, b) { a + b }; add(2, 3);")
        fn = prog.statements[0].value
        self.assertIsInstance(fn, ast.FunctionLiteral)
        self.assertEqual([p.value for p in fn.parameters], ["a", "b"])
        self.assertEqual(fn.name, "add")  # inferred from let binding
        call = prog.statements[1].expression
        self.assertIsInstance(call, ast.CallExpression)
        self.assertEqual(len(call.arguments), 2)

    def test_array_hash_index(self):
        prog = parse('let a = [1, 2, 3]; let h = {"k": 1,}; a[0]; h["k"];')
        self.assertIsInstance(prog.statements[0].value, ast.ArrayLiteral)
        self.assertIsInstance(prog.statements[1].value, ast.HashLiteral)
        self.assertIsInstance(prog.statements[2].expression, ast.IndexExpression)

    def test_while_and_for(self):
        prog = parse("while (x) { x = x - 1; } "
                     "for (let i = 0; i < 3; i = i + 1) { print(i); }")
        self.assertIsInstance(prog.statements[0], ast.WhileStatement)
        forstmt = prog.statements[1]
        self.assertIsInstance(forstmt, ast.ForStatement)
        self.assertIsInstance(forstmt.init, ast.LetStatement)
        self.assertIsNotNone(forstmt.condition)
        self.assertIsNotNone(forstmt.post)

    def test_trailing_comma_allowed(self):
        parse("[1, 2, 3,]")
        parse("f(1, 2,)")

    def test_error_on_missing_paren(self):
        errors = parse_with_errors("let x = (1 + 2;")
        self.assertTrue(errors)

    def test_error_on_bad_assignment_target(self):
        errors = parse_with_errors("1 + 2 = 3;")
        self.assertTrue(any("assignment target" in str(e) for e in errors))


if __name__ == "__main__":
    unittest.main()
