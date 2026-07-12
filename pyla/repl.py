"""An interactive Read-Eval-Print Loop for Pyla.

Handles multi-line input by counting unbalanced brackets, keeps a single
environment across lines so definitions persist, and echoes the value of the
last expression (unless it is nil)."""

import sys

from .parser import Parser
from .evaluator import evaluate
from .environment import Environment
from . import objects as obj
from .errors import PylaRuntimeError

BANNER = r"""
     _       .
  __|_)     _|_    everything flows
 |__| \__|--|      Pyla {version}
     |>  |> |>
""" + """\
Commands: :help  :env  :zen  :brainrot  :quit
"""

HELP = """\
Pyla quick reference:
  let x = 10;                 declare a variable
  "hi ${x}"                   string interpolation (any expression)
  fn(a, b) { a + b }          a function literal (closures supported)
  attempt(fn() { risky() })   catch errors as {ok, value, error}
  if (c) { .. } else { .. }   conditional (an expression)
  while (c) { .. }            loop; also for (i=0; i<n; i=i+1) { .. }
  [1, 2, 3]     {"a": 1}      arrays and hashes (h.key sugar for h["key"])
  x |> f(a) |> g              pipelines: f(x, a) then g(...)
  let m = import("std/math")  modules; stdlib: std/list, std/math
  builtins: print write len push pop first last rest keys values range
            str int float type abs min max chr ord contains delete input
            assert import split join upper lower trim replace slice
            args read_file write_file append_file exists
  :brainrot toggles the Gen Z dialect (fr/cook/yeet/vibecheck/nocap/yap...)
"""


def _brackets_balanced(text):
    depth = 0
    in_string = False
    escape = False
    for ch in text:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
    return depth <= 0 and not in_string


def start(version="0.1.0"):
    print(BANNER.format(version=version), end="")
    env = Environment()
    slang = False
    while True:
        try:
            line = input("fr> " if slang else ">> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        stripped = line.strip()
        if stripped in (":quit", ":q", "exit", "quit"):
            return
        if stripped == ":help":
            print(HELP, end="")
            continue
        if stripped == ":zen":
            from .cli import ZEN
            print(ZEN, end="")
            continue
        if stripped == ":brainrot":
            slang = not slang
            print("brainrot mode: ON (fr fr)" if slang
                  else "brainrot mode: off (back to professional)")
            continue
        if stripped == ":env":
            if not env.store:
                print("(no variables defined)")
            for k, v in env.store.items():
                print(f"  {k} = {v.inspect()}")
            continue
        if not stripped:
            continue

        # Accumulate continuation lines until brackets balance.
        source = line
        while not _brackets_balanced(source):
            try:
                cont = input(".. ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            source += "\n" + cont

        parser = Parser(source, slang)
        program = parser.parse_program()
        if parser.errors:
            for e in parser.errors:
                print(f"  {e}")
            continue
        try:
            result = evaluate(program, env)
        except PylaRuntimeError as e:
            print(f"  {e}")
            continue
        if result is not None and result is not obj.NIL:
            print(result.inspect())
