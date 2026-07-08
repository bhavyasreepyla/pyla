"""The Pyla module system.

`import("path")` loads a .pyla file, evaluates it once in a fresh
environment, and returns its top-level bindings as a hash. Paths resolve
relative to the importing file first, then against the interpreter's bundled
library (so `import("std/list")` always works). Modules are cached by
absolute path, so importing the same file twice returns the same hash object.
"""

import os

from . import objects as obj
from .errors import PylaError, PylaRuntimeError

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))

_cache = {}
_loading = set()
_dir_stack = [os.getcwd()]


def set_base_dir(path):
    """Called by the CLI so imports resolve relative to the main script."""
    _dir_stack[0] = os.path.abspath(path)


def _resolve(path_str):
    names = [path_str] if path_str.endswith(".pyla") else [path_str + ".pyla"]
    for base in (_dir_stack[-1], _PKG_DIR):
        for name in names:
            full = os.path.abspath(os.path.join(base, name))
            if os.path.isfile(full):
                return full
    return None


def load_module(path_str, line=0):
    full = _resolve(path_str)
    if full is None:
        raise PylaRuntimeError(f"module not found: {path_str}", line)
    if full in _cache:
        return _cache[full]
    if full in _loading:
        raise PylaRuntimeError(f"circular import: {path_str}", line)

    with open(full, "r", encoding="utf-8-sig") as f:
        source = f.read()

    from .parser import Parser
    from .evaluator import evaluate
    from .environment import Environment

    parser = Parser(source)
    program = parser.parse_program()
    if parser.errors:
        e = parser.errors[0]
        raise PylaRuntimeError(
            f"in module {path_str}: {e.message} [line {e.line}]", line)

    env = Environment()
    _loading.add(full)
    _dir_stack.append(os.path.dirname(full))
    try:
        evaluate(program, env)
    except PylaError as e:
        raise PylaRuntimeError(f"in module {path_str}: {e}", line)
    finally:
        _dir_stack.pop()
        _loading.discard(full)

    exports = obj.Hash()
    for name, value in env.store.items():
        exports.set(obj.String(name), value)
    _cache[full] = exports
    return exports
