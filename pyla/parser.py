"""A Pratt (top-down operator precedence) parser for Pyla.

The parser keeps a current token and a peek token. Prefix-parse functions
handle tokens that appear at the start of an expression (literals, identifiers,
prefix operators, grouping, etc). Infix-parse functions handle operators that
sit between two expressions and are chosen by the peek token's precedence.
"""

from . import tokens as T
from . import ast_nodes as ast
from .lexer import Lexer
from .errors import ParseError

# Precedence levels, from loosest to tightest binding.
LOWEST = 1
ASSIGN = 2       # =
PIPELINE = 3     # |>
OR = 4           # or
AND = 5          # and
EQUALS = 6       # == !=
LESSGREATER = 7  # < > <= >=
SUM = 8          # + -
PRODUCT = 9      # * / %
PREFIX = 10      # -x !x
CALL = 11        # fn(...)
INDEX = 12       # arr[...]

PRECEDENCES = {
    T.ASSIGN: ASSIGN,
    T.PIPE: PIPELINE,
    T.OR: OR,
    T.AND: AND,
    T.EQ: EQUALS,
    T.NOT_EQ: EQUALS,
    T.LT: LESSGREATER,
    T.GT: LESSGREATER,
    T.LE: LESSGREATER,
    T.GE: LESSGREATER,
    T.PLUS: SUM,
    T.MINUS: SUM,
    T.SLASH: PRODUCT,
    T.ASTERISK: PRODUCT,
    T.PERCENT: PRODUCT,
    T.LPAREN: CALL,
    T.LBRACKET: INDEX,
    T.DOT: INDEX,
}


class Parser:
    def __init__(self, source: str, slang: bool = False):
        self.lexer = Lexer(source, slang)
        self.errors = []
        self.cur_token = None
        self.peek_token = None

        self.prefix_fns = {
            T.IDENT: self.parse_identifier,
            T.INT: self.parse_integer_literal,
            T.FLOAT: self.parse_float_literal,
            T.STRING: self.parse_string_literal,
            T.TRUE: self.parse_boolean,
            T.FALSE: self.parse_boolean,
            T.NIL: self.parse_nil,
            T.BANG: self.parse_prefix_expression,
            T.MINUS: self.parse_prefix_expression,
            T.LPAREN: self.parse_grouped_expression,
            T.IF: self.parse_if_expression,
            T.FUNCTION: self.parse_function_literal,
            T.LBRACKET: self.parse_array_literal,
            T.LBRACE: self.parse_hash_literal,
        }
        self.infix_fns = {
            T.PLUS: self.parse_infix_expression,
            T.MINUS: self.parse_infix_expression,
            T.SLASH: self.parse_infix_expression,
            T.ASTERISK: self.parse_infix_expression,
            T.PERCENT: self.parse_infix_expression,
            T.EQ: self.parse_infix_expression,
            T.NOT_EQ: self.parse_infix_expression,
            T.LT: self.parse_infix_expression,
            T.GT: self.parse_infix_expression,
            T.LE: self.parse_infix_expression,
            T.GE: self.parse_infix_expression,
            T.AND: self.parse_infix_expression,
            T.OR: self.parse_infix_expression,
            T.LPAREN: self.parse_call_expression,
            T.LBRACKET: self.parse_index_expression,
            T.DOT: self.parse_dot_expression,
            T.ASSIGN: self.parse_assign_expression,
            T.PIPE: self.parse_pipeline_expression,
        }

        self._next_token()
        self._next_token()

    # -- token helpers ------------------------------------------------------

    def _next_token(self):
        self.cur_token = self.peek_token
        self.peek_token = self.lexer.next_token()

    def _cur_is(self, ttype):
        return self.cur_token.type == ttype

    def _peek_is(self, ttype):
        return self.peek_token.type == ttype

    def _expect_peek(self, ttype):
        if self._peek_is(ttype):
            self._next_token()
            return True
        self._peek_error(ttype)
        return False

    def _peek_error(self, ttype):
        self.errors.append(ParseError(
            f"expected next token to be {ttype!r}, got {self.peek_token.type!r}",
            self.peek_token.line, self.peek_token.col))

    def _peek_precedence(self):
        return PRECEDENCES.get(self.peek_token.type, LOWEST)

    def _cur_precedence(self):
        return PRECEDENCES.get(self.cur_token.type, LOWEST)

    def _error(self, message, token=None):
        token = token or self.cur_token
        self.errors.append(ParseError(message, token.line, token.col))

    # -- top level ----------------------------------------------------------

    def parse_program(self):
        program = ast.Program(statements=[])
        while not self._cur_is(T.EOF):
            stmt = self.parse_statement()
            if stmt is not None:
                program.statements.append(stmt)
            self._next_token()
        return program

    def parse_statement(self):
        if self._cur_is(T.LET):
            return self.parse_let_statement()
        if self._cur_is(T.RETURN):
            return self.parse_return_statement()
        if self._cur_is(T.WHILE):
            return self.parse_while_statement()
        if self._cur_is(T.FOR):
            return self.parse_for_statement()
        if self._cur_is(T.BREAK):
            return self.parse_break_statement()
        if self._cur_is(T.CONTINUE):
            return self.parse_continue_statement()
        return self.parse_expression_statement()

    # -- statements ---------------------------------------------------------

    def parse_let_statement(self):
        line = self.cur_token.line
        if not self._expect_peek(T.IDENT):
            return None
        name = ast.Identifier(self.cur_token.literal, self.cur_token.line)
        if not self._expect_peek(T.ASSIGN):
            return None
        self._next_token()
        value = self.parse_expression(LOWEST)
        # Give anonymous function literals the name they're bound to.
        if isinstance(value, ast.FunctionLiteral) and not value.name:
            value.name = name.value
        if self._peek_is(T.SEMICOLON):
            self._next_token()
        return ast.LetStatement(name=name, value=value, line=line)

    def parse_return_statement(self):
        line = self.cur_token.line
        if self._peek_is(T.SEMICOLON):
            self._next_token()
            return ast.ReturnStatement(value=None, line=line)
        self._next_token()
        value = self.parse_expression(LOWEST)
        if self._peek_is(T.SEMICOLON):
            self._next_token()
        return ast.ReturnStatement(value=value, line=line)

    def parse_expression_statement(self):
        line = self.cur_token.line
        expr = self.parse_expression(LOWEST)
        if self._peek_is(T.SEMICOLON):
            self._next_token()
        return ast.ExpressionStatement(expression=expr, line=line)

    def parse_block_statement(self):
        line = self.cur_token.line
        block = ast.BlockStatement(statements=[], line=line)
        self._next_token()  # consume '{'
        while not self._cur_is(T.RBRACE) and not self._cur_is(T.EOF):
            stmt = self.parse_statement()
            if stmt is not None:
                block.statements.append(stmt)
            self._next_token()
        if not self._cur_is(T.RBRACE):
            self._error("expected '}' to close block")
        return block

    def parse_while_statement(self):
        line = self.cur_token.line
        if not self._expect_peek(T.LPAREN):
            return None
        self._next_token()
        condition = self.parse_expression(LOWEST)
        if not self._expect_peek(T.RPAREN):
            return None
        if not self._expect_peek(T.LBRACE):
            return None
        body = self.parse_block_statement()
        return ast.WhileStatement(condition=condition, body=body, line=line)

    def parse_for_statement(self):
        line = self.cur_token.line
        if not self._expect_peek(T.LPAREN):
            return None
        self._next_token()  # move to first token of the init clause (or ';')

        # init clause
        if self._cur_is(T.SEMICOLON):
            init = None
        elif self._cur_is(T.LET):
            init = self.parse_let_statement()
        else:
            init = self.parse_expression_statement()
        if not self._cur_is(T.SEMICOLON):
            self._error("expected ';' after for-loop initializer")
            return None
        self._next_token()  # move past ';' to condition (or ';')

        # condition clause
        if self._cur_is(T.SEMICOLON):
            condition = None
        else:
            condition = self.parse_expression(LOWEST)
            if not self._expect_peek(T.SEMICOLON):
                return None
        self._next_token()  # move past ';' to post (or ')')

        # post clause
        if self._cur_is(T.RPAREN):
            post = None
        else:
            post = self.parse_expression(LOWEST)
            if not self._expect_peek(T.RPAREN):
                return None

        if not self._expect_peek(T.LBRACE):
            return None
        body = self.parse_block_statement()
        return ast.ForStatement(init=init, condition=condition,
                                post=post, body=body, line=line)

    def parse_break_statement(self):
        line = self.cur_token.line
        if self._peek_is(T.SEMICOLON):
            self._next_token()
        return ast.BreakStatement(line=line)

    def parse_continue_statement(self):
        line = self.cur_token.line
        if self._peek_is(T.SEMICOLON):
            self._next_token()
        return ast.ContinueStatement(line=line)

    # -- expressions --------------------------------------------------------

    def parse_expression(self, precedence):
        prefix = self.prefix_fns.get(self.cur_token.type)
        if prefix is None:
            self._error(f"no parse rule for {self.cur_token.type!r} "
                        f"({self.cur_token.literal!r})")
            return None
        left = prefix()

        while not self._peek_is(T.SEMICOLON) and precedence < self._peek_precedence():
            infix = self.infix_fns.get(self.peek_token.type)
            if infix is None:
                return left
            self._next_token()
            left = infix(left)
        return left

    def parse_identifier(self):
        return ast.Identifier(self.cur_token.literal, self.cur_token.line)

    def parse_integer_literal(self):
        try:
            value = int(self.cur_token.literal)
        except ValueError:
            self._error(f"could not parse {self.cur_token.literal!r} as integer")
            return None
        return ast.IntegerLiteral(value, self.cur_token.line)

    def parse_float_literal(self):
        try:
            value = float(self.cur_token.literal)
        except ValueError:
            self._error(f"could not parse {self.cur_token.literal!r} as float")
            return None
        return ast.FloatLiteral(value, self.cur_token.line)

    def parse_string_literal(self):
        return ast.StringLiteral(self.cur_token.literal, self.cur_token.line)

    def parse_boolean(self):
        return ast.BooleanLiteral(self._cur_is(T.TRUE), self.cur_token.line)

    def parse_nil(self):
        return ast.NilLiteral(self.cur_token.line)

    def parse_prefix_expression(self):
        line = self.cur_token.line
        operator = self.cur_token.literal
        self._next_token()
        right = self.parse_expression(PREFIX)
        return ast.PrefixExpression(operator=operator, right=right, line=line)

    def parse_infix_expression(self, left):
        line = self.cur_token.line
        operator = self.cur_token.literal
        precedence = self._cur_precedence()
        self._next_token()
        right = self.parse_expression(precedence)
        return ast.InfixExpression(left=left, operator=operator,
                                   right=right, line=line)

    def parse_assign_expression(self, left):
        line = self.cur_token.line
        if not isinstance(left, (ast.Identifier, ast.IndexExpression)):
            self._error("invalid assignment target")
        self._next_token()
        value = self.parse_expression(LOWEST)  # right-associative
        return ast.AssignExpression(target=left, value=value, line=line)

    def parse_grouped_expression(self):
        self._next_token()
        expr = self.parse_expression(LOWEST)
        if not self._expect_peek(T.RPAREN):
            return None
        return expr

    def parse_if_expression(self):
        line = self.cur_token.line
        if not self._expect_peek(T.LPAREN):
            return None
        self._next_token()
        condition = self.parse_expression(LOWEST)
        if not self._expect_peek(T.RPAREN):
            return None
        if not self._expect_peek(T.LBRACE):
            return None
        consequence = self.parse_block_statement()

        alternative = None
        if self._peek_is(T.ELSE):
            self._next_token()
            if self._peek_is(T.IF):
                self._next_token()
                alternative = self.parse_if_expression()  # else-if chain
            elif self._expect_peek(T.LBRACE):
                alternative = self.parse_block_statement()
            else:
                return None
        return ast.IfExpression(condition=condition, consequence=consequence,
                                alternative=alternative, line=line)

    def parse_function_literal(self):
        line = self.cur_token.line
        if not self._expect_peek(T.LPAREN):
            return None
        parameters = self.parse_function_parameters()
        if not self._expect_peek(T.LBRACE):
            return None
        body = self.parse_block_statement()
        return ast.FunctionLiteral(parameters=parameters, body=body, line=line)

    def parse_function_parameters(self):
        params = []
        if self._peek_is(T.RPAREN):
            self._next_token()
            return params
        self._next_token()
        params.append(ast.Identifier(self.cur_token.literal, self.cur_token.line))
        while self._peek_is(T.COMMA):
            self._next_token()
            self._next_token()
            params.append(ast.Identifier(self.cur_token.literal, self.cur_token.line))
        if not self._expect_peek(T.RPAREN):
            return []
        return params

    def parse_call_expression(self, function):
        line = self.cur_token.line
        arguments = self.parse_expression_list(T.RPAREN)
        return ast.CallExpression(function=function, arguments=arguments, line=line)

    def parse_index_expression(self, left):
        line = self.cur_token.line
        self._next_token()
        index = self.parse_expression(LOWEST)
        if not self._expect_peek(T.RBRACKET):
            return None
        return ast.IndexExpression(left=left, index=index, line=line)

    def parse_pipeline_expression(self, left):
        # `x |> f(a, b)` desugars to `f(x, a, b)`; `x |> f` to `f(x)`.
        # Pure parser sugar, so both engines support it identically.
        line = self.cur_token.line
        self._next_token()
        right = self.parse_expression(PIPELINE)
        if isinstance(right, ast.CallExpression):
            right.arguments.insert(0, left)
            right.pipe_text = getattr(right.function, "dot_text",
                                      None) or str(right.function)
            return right
        return ast.CallExpression(function=right, arguments=[left], line=line,
                                  pipe_text=getattr(right, "dot_text",
                                                    None) or str(right))

    def parse_dot_expression(self, left):
        # `a.b` is sugar for `a["b"]`, so both engines support it for free.
        line = self.cur_token.line
        if not self._expect_peek(T.IDENT):
            return None
        name = ast.StringLiteral(self.cur_token.literal, self.cur_token.line)
        expr = ast.IndexExpression(left=left, index=name, line=line)
        # Remember the dotted spelling so --trace can label pipe stages nicely.
        expr.dot_text = f"{left}.{name.value}"
        return expr

    def parse_array_literal(self):
        line = self.cur_token.line
        elements = self.parse_expression_list(T.RBRACKET)
        return ast.ArrayLiteral(elements=elements, line=line)

    def parse_expression_list(self, end):
        items = []
        if self._peek_is(end):
            self._next_token()
            return items
        self._next_token()
        items.append(self.parse_expression(LOWEST))
        while self._peek_is(T.COMMA):
            self._next_token()          # consume ','
            if self._peek_is(end):      # allow a trailing comma
                break
            self._next_token()
            items.append(self.parse_expression(LOWEST))
        if not self._expect_peek(end):
            return []
        return items

    def parse_hash_literal(self):
        line = self.cur_token.line
        pairs = []
        while not self._peek_is(T.RBRACE):
            self._next_token()
            key = self.parse_expression(LOWEST)
            if not self._expect_peek(T.COLON):
                return None
            self._next_token()
            value = self.parse_expression(LOWEST)
            pairs.append((key, value))
            if not self._peek_is(T.RBRACE) and not self._expect_peek(T.COMMA):
                return None
        if not self._expect_peek(T.RBRACE):
            return None
        return ast.HashLiteral(pairs=pairs, line=line)
