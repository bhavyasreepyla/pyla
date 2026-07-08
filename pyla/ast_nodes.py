"""AST node definitions for Pyla.

Every node stores the token that introduced it so the evaluator can report the
line number when something goes wrong at runtime. Each node's __str__ renders
back to a source-like form, which makes parser tests easy to read.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


class Node:
    line: int = 0


# ---------------------------------------------------------------------------
# Program / statements
# ---------------------------------------------------------------------------

@dataclass
class Program(Node):
    statements: List["Node"] = field(default_factory=list)

    def __str__(self):
        return "".join(str(s) for s in self.statements)


@dataclass
class LetStatement(Node):
    name: "Identifier"
    value: "Node"
    line: int = 0

    def __str__(self):
        return f"let {self.name} = {self.value};"


@dataclass
class ReturnStatement(Node):
    value: Optional["Node"]
    line: int = 0

    def __str__(self):
        v = "" if self.value is None else str(self.value)
        return f"return {v};"


@dataclass
class ExpressionStatement(Node):
    expression: "Node"
    line: int = 0

    def __str__(self):
        return str(self.expression)


@dataclass
class BlockStatement(Node):
    statements: List["Node"] = field(default_factory=list)
    line: int = 0

    def __str__(self):
        return "{ " + " ".join(str(s) for s in self.statements) + " }"


@dataclass
class WhileStatement(Node):
    condition: "Node"
    body: "BlockStatement"
    line: int = 0

    def __str__(self):
        return f"while ({self.condition}) {self.body}"


@dataclass
class ForStatement(Node):
    init: Optional["Node"]
    condition: Optional["Node"]
    post: Optional["Node"]
    body: "BlockStatement"
    line: int = 0

    def __str__(self):
        i = "" if self.init is None else str(self.init)
        c = "" if self.condition is None else str(self.condition)
        p = "" if self.post is None else str(self.post)
        return f"for ({i} {c}; {p}) {self.body}"


@dataclass
class BreakStatement(Node):
    line: int = 0

    def __str__(self):
        return "break;"


@dataclass
class ContinueStatement(Node):
    line: int = 0

    def __str__(self):
        return "continue;"


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

@dataclass
class Identifier(Node):
    value: str
    line: int = 0

    def __str__(self):
        return self.value


@dataclass
class IntegerLiteral(Node):
    value: int
    line: int = 0

    def __str__(self):
        return str(self.value)


@dataclass
class FloatLiteral(Node):
    value: float
    line: int = 0

    def __str__(self):
        return repr(self.value)


@dataclass
class StringLiteral(Node):
    value: str
    line: int = 0

    def __str__(self):
        return f'"{self.value}"'


@dataclass
class BooleanLiteral(Node):
    value: bool
    line: int = 0

    def __str__(self):
        return "true" if self.value else "false"


@dataclass
class NilLiteral(Node):
    line: int = 0

    def __str__(self):
        return "nil"


@dataclass
class PrefixExpression(Node):
    operator: str
    right: "Node"
    line: int = 0

    def __str__(self):
        return f"({self.operator}{self.right})"


@dataclass
class InfixExpression(Node):
    left: "Node"
    operator: str
    right: "Node"
    line: int = 0

    def __str__(self):
        return f"({self.left} {self.operator} {self.right})"


@dataclass
class IfExpression(Node):
    condition: "Node"
    consequence: "BlockStatement"
    alternative: Optional["Node"]  # BlockStatement or IfExpression (else-if)
    line: int = 0

    def __str__(self):
        s = f"if ({self.condition}) {self.consequence}"
        if self.alternative is not None:
            s += f" else {self.alternative}"
        return s


@dataclass
class FunctionLiteral(Node):
    parameters: List["Identifier"]
    body: "BlockStatement"
    line: int = 0
    name: str = ""  # optional, for nicer stack traces / printing

    def __str__(self):
        params = ", ".join(str(p) for p in self.parameters)
        return f"fn({params}) {self.body}"


@dataclass
class CallExpression(Node):
    function: "Node"
    arguments: List["Node"]
    line: int = 0

    def __str__(self):
        args = ", ".join(str(a) for a in self.arguments)
        return f"{self.function}({args})"


@dataclass
class ArrayLiteral(Node):
    elements: List["Node"]
    line: int = 0

    def __str__(self):
        return "[" + ", ".join(str(e) for e in self.elements) + "]"


@dataclass
class IndexExpression(Node):
    left: "Node"
    index: "Node"
    line: int = 0

    def __str__(self):
        return f"({self.left}[{self.index}])"


@dataclass
class HashLiteral(Node):
    pairs: List[Tuple["Node", "Node"]]
    line: int = 0

    def __str__(self):
        inner = ", ".join(f"{k}: {v}" for k, v in self.pairs)
        return "{" + inner + "}"


@dataclass
class AssignExpression(Node):
    target: "Node"       # Identifier or IndexExpression
    value: "Node"
    line: int = 0

    def __str__(self):
        return f"({self.target} = {self.value})"
