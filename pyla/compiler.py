"""Bytecode compiler for Pyla.

Walks the AST once and emits flat bytecode for the stack VM in vm.py.
Instructions are (opcode, arg, line) tuples. Control flow becomes jumps with
back-patched targets; `break`/`continue` are collected per enclosing loop and
patched when the loop's extent is known. Function literals compile to
CompiledFunction constants wrapped in a Closure at runtime, which captures the
current environment (same closure semantics as the tree-walker).
"""

from dataclasses import dataclass, field
from typing import List

from . import ast_nodes as ast
from . import objects as obj
from .errors import ParseError

# Opcodes ---------------------------------------------------------------------
CONST = 1        # arg: constant-pool index
NIL = 2
TRUE = 3
FALSE = 4
POP = 5
BINARY = 6       # arg: operator string ("+", "<", "==", ...)
NEG = 7
NOT = 8
JUMP = 9         # arg: absolute instruction index
JF = 10          # jump if falsy (pops the value)
JF_KEEP = 11     # jump if falsy, keeping the value (for `and`)
JT_KEEP = 12     # jump if truthy, keeping the value (for `or`)
GET = 13         # arg: name
DEFINE = 14      # arg: name (let: bind in current scope, pops)
ASSIGN = 15      # arg: name (rebind existing, peeks)
ARRAY = 16       # arg: element count
HASH = 17        # arg: pair count
INDEX = 18
SET_INDEX = 19
CALL = 20        # arg: argument count
RET = 21
CLOSURE = 22     # arg: constant-pool index of a CompiledFunction
PUSH_ENV = 23    # enter a child scope (for-loop header)
POP_ENV = 24     # leave it


@dataclass
class CompiledFunction(obj.Object):
    params: List[str]
    code: list
    constants: list = field(default_factory=list)
    name: str = ""

    def type_name(self):
        return "function"

    def inspect(self):
        label = f" {self.name}" if self.name else ""
        return f"fn{label}({', '.join(self.params)}) {{ ... }}"


@dataclass
class Closure(obj.Object):
    fn: CompiledFunction
    env: object

    def type_name(self):
        return "function"

    def inspect(self):
        return self.fn.inspect()


@dataclass
class _LoopCtx:
    cont_target: int = -1        # -1 means "patch later" (for-loop post clause)
    breaks: list = field(default_factory=list)
    continues: list = field(default_factory=list)


class CompileError(ParseError):
    pass


class Compiler:
    def __init__(self):
        self.constants = []
        self.code = []
        self.loops = []

    # -- emit helpers --------------------------------------------------------

    def emit(self, op, arg=None, line=0):
        self.code.append((op, arg, line))
        return len(self.code) - 1

    def patch(self, pos, target):
        op, _, line = self.code[pos]
        self.code[pos] = (op, target, line)

    def add_constant(self, value):
        self.constants.append(value)
        return len(self.constants) - 1

    # -- entry point ----------------------------------------------------------

    def compile_program(self, program):
        self.compile_block_value(program.statements)
        self.emit(RET)
        return CompiledFunction(params=[], code=self.code,
                                constants=self.constants, name="<main>")

    # -- statements -----------------------------------------------------------

    def compile_block_value(self, statements):
        """Compile statements so the block leaves its value on the stack
        (the value of a trailing expression, else nil)."""
        if not statements:
            self.emit(NIL)
            return
        for stmt in statements[:-1]:
            self.compile_statement(stmt)
        last = statements[-1]
        if isinstance(last, ast.ExpressionStatement):
            self.compile_expression(last.expression)
        else:
            self.compile_statement(last)
            self.emit(NIL, line=getattr(last, "line", 0))

    def compile_statement(self, stmt):
        t = type(stmt)
        if t is ast.ExpressionStatement:
            self.compile_expression(stmt.expression)
            self.emit(POP, line=stmt.line)
        elif t is ast.LetStatement:
            self.compile_expression(stmt.value)
            self.emit(DEFINE, stmt.name.value, stmt.line)
        elif t is ast.ReturnStatement:
            if stmt.value is None:
                self.emit(NIL, line=stmt.line)
            else:
                self.compile_expression(stmt.value)
            self.emit(RET, line=stmt.line)
        elif t is ast.WhileStatement:
            self.compile_while(stmt)
        elif t is ast.ForStatement:
            self.compile_for(stmt)
        elif t is ast.BreakStatement:
            if not self.loops:
                raise CompileError("'break' outside of a loop", stmt.line)
            pos = self.emit(JUMP, None, stmt.line)
            self.loops[-1].breaks.append(pos)
        elif t is ast.ContinueStatement:
            if not self.loops:
                raise CompileError("'continue' outside of a loop", stmt.line)
            ctx = self.loops[-1]
            if ctx.cont_target >= 0:
                self.emit(JUMP, ctx.cont_target, stmt.line)
            else:
                ctx.continues.append(self.emit(JUMP, None, stmt.line))
        else:
            raise CompileError(f"cannot compile statement {t.__name__}",
                               getattr(stmt, "line", 0))

    def compile_while(self, stmt):
        cond_start = len(self.code)
        self.compile_expression(stmt.condition)
        jf = self.emit(JF, None, stmt.line)
        self.loops.append(_LoopCtx(cont_target=cond_start))
        for s in stmt.body.statements:
            self.compile_statement(s)
        self.emit(JUMP, cond_start, stmt.line)
        end = len(self.code)
        ctx = self.loops.pop()
        self.patch(jf, end)
        for pos in ctx.breaks:
            self.patch(pos, end)

    def compile_for(self, stmt):
        self.emit(PUSH_ENV, line=stmt.line)
        if stmt.init is not None:
            self.compile_statement(stmt.init)
        cond_start = len(self.code)
        if stmt.condition is not None:
            self.compile_expression(stmt.condition)
        else:
            self.emit(TRUE, line=stmt.line)
        jf = self.emit(JF, None, stmt.line)
        self.loops.append(_LoopCtx(cont_target=-1))
        for s in stmt.body.statements:
            self.compile_statement(s)
        post_start = len(self.code)
        if stmt.post is not None:
            self.compile_expression(stmt.post)
            self.emit(POP, line=stmt.line)
        self.emit(JUMP, cond_start, stmt.line)
        end = len(self.code)          # the POP_ENV below
        ctx = self.loops.pop()
        self.patch(jf, end)
        for pos in ctx.breaks:
            self.patch(pos, end)
        for pos in ctx.continues:
            self.patch(pos, post_start)
        self.emit(POP_ENV, line=stmt.line)

    # -- expressions ----------------------------------------------------------

    def compile_expression(self, node):
        t = type(node)
        line = getattr(node, "line", 0)

        if t is ast.IntegerLiteral:
            self.emit(CONST, self.add_constant(obj.Integer(node.value)), line)
        elif t is ast.FloatLiteral:
            self.emit(CONST, self.add_constant(obj.Float(node.value)), line)
        elif t is ast.StringLiteral:
            self.emit(CONST, self.add_constant(obj.String(node.value)), line)
        elif t is ast.BooleanLiteral:
            self.emit(TRUE if node.value else FALSE, line=line)
        elif t is ast.NilLiteral:
            self.emit(NIL, line=line)
        elif t is ast.Identifier:
            self.emit(GET, node.value, line)
        elif t is ast.PrefixExpression:
            self.compile_expression(node.right)
            self.emit(NEG if node.operator == "-" else NOT, line=line)
        elif t is ast.InfixExpression:
            self.compile_infix(node)
        elif t is ast.AssignExpression:
            self.compile_assign(node)
        elif t is ast.IfExpression:
            self.compile_if(node)
        elif t is ast.FunctionLiteral:
            self.compile_function(node)
        elif t is ast.CallExpression:
            self.compile_expression(node.function)
            for arg in node.arguments:
                self.compile_expression(arg)
            self.emit(CALL, len(node.arguments), line)
        elif t is ast.ArrayLiteral:
            for e in node.elements:
                self.compile_expression(e)
            self.emit(ARRAY, len(node.elements), line)
        elif t is ast.HashLiteral:
            for k, v in node.pairs:
                self.compile_expression(k)
                self.compile_expression(v)
            self.emit(HASH, len(node.pairs), line)
        elif t is ast.IndexExpression:
            self.compile_expression(node.left)
            self.compile_expression(node.index)
            self.emit(INDEX, line=line)
        else:
            raise CompileError(f"cannot compile expression {t.__name__}", line)

    def compile_infix(self, node):
        if node.operator == "and":
            self.compile_expression(node.left)
            jf = self.emit(JF_KEEP, None, node.line)
            self.emit(POP, line=node.line)
            self.compile_expression(node.right)
            self.patch(jf, len(self.code))
            return
        if node.operator == "or":
            self.compile_expression(node.left)
            jt = self.emit(JT_KEEP, None, node.line)
            self.emit(POP, line=node.line)
            self.compile_expression(node.right)
            self.patch(jt, len(self.code))
            return
        self.compile_expression(node.left)
        self.compile_expression(node.right)
        self.emit(BINARY, node.operator, node.line)

    def compile_assign(self, node):
        target = node.target
        if isinstance(target, ast.Identifier):
            self.compile_expression(node.value)
            self.emit(ASSIGN, target.value, node.line)
        elif isinstance(target, ast.IndexExpression):
            self.compile_expression(target.left)
            self.compile_expression(target.index)
            self.compile_expression(node.value)
            self.emit(SET_INDEX, line=node.line)
        else:
            raise CompileError("invalid assignment target", node.line)

    def compile_if(self, node):
        self.compile_expression(node.condition)
        jf = self.emit(JF, None, node.line)
        self.compile_block_value(node.consequence.statements)
        jend = self.emit(JUMP, None, node.line)
        self.patch(jf, len(self.code))
        if node.alternative is None:
            self.emit(NIL, line=node.line)
        elif isinstance(node.alternative, ast.BlockStatement):
            self.compile_block_value(node.alternative.statements)
        else:  # else-if chain
            self.compile_expression(node.alternative)
        self.patch(jend, len(self.code))

    def compile_function(self, node):
        outer = (self.code, self.loops, self.constants)
        self.code, self.loops, self.constants = [], [], []
        self.compile_block_value(node.body.statements)
        self.emit(RET, line=node.line)
        fn = CompiledFunction(params=[p.value for p in node.parameters],
                              code=self.code, constants=self.constants,
                              name=node.name)
        self.code, self.loops, self.constants = outer
        self.emit(CLOSURE, self.add_constant(fn), node.line)


def compile_source(source, slang=False):
    """Parse and compile. Returns the main CompiledFunction (constants are
    carried on each function, so closures are callable from anywhere)."""
    from .parser import Parser
    p = Parser(source, slang)
    program = p.parse_program()
    if p.errors:
        raise p.errors[0]
    return Compiler().compile_program(program)
