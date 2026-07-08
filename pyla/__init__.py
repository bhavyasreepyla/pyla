"""Pyla: a small, dynamically-typed, pipeline-first programming language.

Public helpers:
    parse(source)      -> (Program, errors)
    run(source, env)   -> final value  (raises on parse/runtime error)

Pass slang=True to either for brainrot mode (the Gen Z dialect).
"""

from .parser import Parser
from .evaluator import evaluate
from .environment import Environment
from .errors import ParseError, PylaRuntimeError

__version__ = "0.4.1"


def parse(source, slang=False):
    p = Parser(source, slang)
    program = p.parse_program()
    return program, p.errors


def run(source, env=None, slang=False):
    """Parse and evaluate source. Raises ParseError (first) or PylaRuntimeError."""
    program, errors = parse(source, slang)
    if errors:
        raise errors[0]
    if env is None:
        env = Environment()
    return evaluate(program, env)
