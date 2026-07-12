"""The Lexer turns Pyla source text into a stream of tokens.

It tracks line and column for every token so the parser and evaluator can
produce error messages that point at the offending location.
"""

from . import tokens as T
from .tokens import Token


class Lexer:
    def __init__(self, source: str, slang: bool = False):
        self.source = source
        self.slang = slang    # brainrot mode: Gen Z keyword aliases
        self.pos = 0          # index of self.ch
        self.read_pos = 0     # next index to read
        self.ch = ""          # current char ("" means EOF)
        self.line = 1
        self.col = 0
        self._read_char()

    def _read_char(self) -> None:
        # Advance position. line/col always describe the new self.ch.
        if self.ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        if self.read_pos >= len(self.source):
            self.ch = ""
        else:
            self.ch = self.source[self.read_pos]
        self.pos = self.read_pos
        self.read_pos += 1

    def _peek_char(self) -> str:
        if self.read_pos >= len(self.source):
            return ""
        return self.source[self.read_pos]

    def _skip_whitespace_and_comments(self) -> None:
        while True:
            if self.ch in (" ", "\t", "\r", "\n"):
                self._read_char()
            elif self.ch == "#":
                while self.ch not in ("\n", ""):
                    self._read_char()
            else:
                break

    def next_token(self) -> Token:
        self._skip_whitespace_and_comments()
        line, col = self.line, self.col
        ch = self.ch

        def tok(ttype, literal):
            return Token(ttype, literal, line, col)

        if ch == "":
            return tok(T.EOF, "")

        # Two-character operators
        if ch == "=":
            if self._peek_char() == "=":
                self._read_char()
                self._read_char()
                return tok(T.EQ, "==")
            self._read_char()
            return tok(T.ASSIGN, "=")
        if ch == "!":
            if self._peek_char() == "=":
                self._read_char()
                self._read_char()
                return tok(T.NOT_EQ, "!=")
            self._read_char()
            return tok(T.BANG, "!")
        if ch == "<":
            if self._peek_char() == "=":
                self._read_char()
                self._read_char()
                return tok(T.LE, "<=")
            self._read_char()
            return tok(T.LT, "<")
        if ch == ">":
            if self._peek_char() == "=":
                self._read_char()
                self._read_char()
                return tok(T.GE, ">=")
            self._read_char()
            return tok(T.GT, ">")
        if ch == "|":
            if self._peek_char() == ">":
                self._read_char()
                self._read_char()
                return tok(T.PIPE, "|>")
            self._read_char()
            return tok(T.ILLEGAL, "|")

        # Single-character tokens
        singles = {
            "+": T.PLUS,
            "-": T.MINUS,
            "*": T.ASTERISK,
            "/": T.SLASH,
            "%": T.PERCENT,
            ",": T.COMMA,
            ";": T.SEMICOLON,
            ":": T.COLON,
            ".": T.DOT,
            "(": T.LPAREN,
            ")": T.RPAREN,
            "{": T.LBRACE,
            "}": T.RBRACE,
            "[": T.LBRACKET,
            "]": T.RBRACKET,
        }
        if ch in singles:
            self._read_char()
            return tok(singles[ch], ch)

        if ch == '"':
            return self._read_string(line, col)

        if ch.isalpha() or ch == "_":
            ident = self._read_identifier()
            if self.slang:
                if ident in T.SLANG_KEYWORDS:
                    return Token(T.SLANG_KEYWORDS[ident], ident, line, col)
                ident = T.SLANG_IDENTS.get(ident, ident)
            return Token(T.lookup_ident(ident), ident, line, col)

        if ch.isdigit():
            return self._read_number(line, col)

        # Unknown character
        self._read_char()
        return tok(T.ILLEGAL, ch)

    def _read_identifier(self) -> str:
        start = self.pos
        while self.ch.isalnum() or self.ch == "_":
            self._read_char()
        return self.source[start:self.pos]

    def _read_number(self, line: int, col: int) -> Token:
        start = self.pos
        is_float = False
        while self.ch.isdigit():
            self._read_char()
        if self.ch == "." and self._peek_char().isdigit():
            is_float = True
            self._read_char()  # consume '.'
            while self.ch.isdigit():
                self._read_char()
        literal = self.source[start:self.pos]
        return Token(T.FLOAT if is_float else T.INT, literal, line, col)

    def _read_string(self, line: int, col: int) -> Token:
        # self.ch is the opening quote. Strings may contain ${expr}
        # interpolations; those produce an INTERP token carrying the
        # literal/expression segments for the parser to desugar.
        self._read_char()
        chars = []
        segments = []
        while self.ch != '"':
            if self.ch == "":
                return Token(T.ILLEGAL, "unterminated string", line, col)
            if self.ch == "\\":
                self._read_char()
                escapes = {"n": "\n", "t": "\t", "r": "\r",
                           '"': '"', "\\": "\\", "0": "\0", "$": "$"}
                chars.append(escapes.get(self.ch, self.ch))
            elif self.ch == "$" and self._peek_char() == "{":
                if chars:
                    segments.append(("str", "".join(chars)))
                    chars = []
                self._read_char()  # on '{'
                self._read_char()  # first char of the expression
                expr_chars = []
                depth = 1
                in_str = False
                escaped = False
                while True:
                    if self.ch == "":
                        return Token(T.ILLEGAL,
                                     "unterminated interpolation", line, col)
                    if in_str:
                        if escaped:
                            escaped = False
                        elif self.ch == "\\":
                            escaped = True
                        elif self.ch == '"':
                            in_str = False
                    else:
                        if self.ch == '"':
                            in_str = True
                        elif self.ch == "{":
                            depth += 1
                        elif self.ch == "}":
                            depth -= 1
                            if depth == 0:
                                break
                    expr_chars.append(self.ch)
                    self._read_char()
                # self.ch is the closing '}'; the loop-bottom advance eats it.
                segments.append(("expr", "".join(expr_chars)))
            else:
                chars.append(self.ch)
            self._read_char()
        self._read_char()  # consume closing quote
        if not segments:
            return Token(T.STRING, "".join(chars), line, col)
        if chars:
            segments.append(("str", "".join(chars)))
        tok = Token(T.INTERP, "<interpolated string>", line, col)
        tok.segments = segments
        return tok

    def tokens(self):
        """Yield all tokens including the final EOF (useful for tests)."""
        while True:
            t = self.next_token()
            yield t
            if t.type == T.EOF:
                break
