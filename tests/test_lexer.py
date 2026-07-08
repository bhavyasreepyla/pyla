import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyla.lexer import Lexer
from pyla import tokens as T


def types_and_literals(source):
    lex = Lexer(source)
    out = []
    for tok in lex.tokens():
        if tok.type == T.EOF:
            break
        out.append((tok.type, tok.literal))
    return out


class LexerTests(unittest.TestCase):
    def test_operators_and_delimiters(self):
        src = "= + - * / % ! == != < > <= >= ( ) { } [ ] , ; :"
        expected_types = [
            T.ASSIGN, T.PLUS, T.MINUS, T.ASTERISK, T.SLASH, T.PERCENT, T.BANG,
            T.EQ, T.NOT_EQ, T.LT, T.GT, T.LE, T.GE,
            T.LPAREN, T.RPAREN, T.LBRACE, T.RBRACE, T.LBRACKET, T.RBRACKET,
            T.COMMA, T.SEMICOLON, T.COLON,
        ]
        got = [t for t, _ in types_and_literals(src)]
        self.assertEqual(got, expected_types)

    def test_keywords_and_identifiers(self):
        src = "let fn if else while for break continue return true false nil and or foo _bar x1"
        got = types_and_literals(src)
        self.assertEqual(got[0], (T.LET, "let"))
        self.assertEqual(got[1], (T.FUNCTION, "fn"))
        self.assertEqual(got[-3], (T.IDENT, "foo"))
        self.assertEqual(got[-2], (T.IDENT, "_bar"))
        self.assertEqual(got[-1], (T.IDENT, "x1"))

    def test_numbers(self):
        got = types_and_literals("42 3.14 0 100")
        self.assertEqual(got, [
            (T.INT, "42"), (T.FLOAT, "3.14"), (T.INT, "0"), (T.INT, "100"),
        ])

    def test_string_with_escapes(self):
        got = types_and_literals(r'"hello\nworld" "a\tb" "quote:\""')
        self.assertEqual(got[0], (T.STRING, "hello\nworld"))
        self.assertEqual(got[1], (T.STRING, "a\tb"))
        self.assertEqual(got[2], (T.STRING, 'quote:"'))

    def test_comments_skipped(self):
        got = types_and_literals("let x = 1; # this is ignored\nlet y = 2;")
        types = [t for t, _ in got]
        self.assertNotIn(T.ILLEGAL, types)
        self.assertEqual(types.count(T.LET), 2)

    def test_line_and_column_tracking(self):
        lex = Lexer("let\n  x = 5;")
        toks = list(lex.tokens())
        # 'let' at line 1, 'x' at line 2 column 3
        self.assertEqual((toks[0].line, toks[0].col), (1, 1))
        x = next(t for t in toks if t.literal == "x")
        self.assertEqual((x.line, x.col), (2, 3))

    def test_unterminated_string_is_illegal(self):
        got = types_and_literals('"open ended')
        self.assertEqual(got[0][0], T.ILLEGAL)


if __name__ == "__main__":
    unittest.main()
