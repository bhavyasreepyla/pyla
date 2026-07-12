"""Built-in functions available in every Pyla program.

Each builtin receives (args, line): a list of already-evaluated argument
objects and the source line of the call site (for error messages).
"""

import sys

from . import objects as obj
from .objects import NIL, bool_obj
from .errors import PylaRuntimeError


def _err(msg, line):
    raise PylaRuntimeError(msg, line)


def _check_arity(name, args, line, *counts):
    if len(args) not in counts:
        expected = " or ".join(str(c) for c in counts)
        _err(f"{name}() expected {expected} argument(s), got {len(args)}", line)


def _b_print(args, line):
    sys.stdout.write(" ".join(a.inspect() for a in args) + "\n")
    return NIL


def _b_write(args, line):
    sys.stdout.write("".join(a.inspect() for a in args))
    return NIL


def _b_len(args, line):
    _check_arity("len", args, line, 1)
    a = args[0]
    if isinstance(a, obj.String):
        return obj.Integer(len(a.value))
    if isinstance(a, obj.Array):
        return obj.Integer(len(a.elements))
    if isinstance(a, obj.Hash):
        return obj.Integer(len(a.pairs))
    _err(f"len() not supported on {a.type_name()}", line)


def _b_type(args, line):
    _check_arity("type", args, line, 1)
    return obj.String(args[0].type_name())


def _b_push(args, line):
    _check_arity("push", args, line, 2)
    arr = args[0]
    if not isinstance(arr, obj.Array):
        _err(f"push() expects an array, got {arr.type_name()}", line)
    arr.elements.append(args[1])
    return arr


def _b_pop(args, line):
    _check_arity("pop", args, line, 1)
    arr = args[0]
    if not isinstance(arr, obj.Array):
        _err(f"pop() expects an array, got {arr.type_name()}", line)
    if not arr.elements:
        _err("pop() from empty array", line)
    return arr.elements.pop()


def _b_first(args, line):
    _check_arity("first", args, line, 1)
    arr = args[0]
    if not isinstance(arr, obj.Array):
        _err(f"first() expects an array, got {arr.type_name()}", line)
    return arr.elements[0] if arr.elements else NIL


def _b_last(args, line):
    _check_arity("last", args, line, 1)
    arr = args[0]
    if not isinstance(arr, obj.Array):
        _err(f"last() expects an array, got {arr.type_name()}", line)
    return arr.elements[-1] if arr.elements else NIL


def _b_rest(args, line):
    _check_arity("rest", args, line, 1)
    arr = args[0]
    if not isinstance(arr, obj.Array):
        _err(f"rest() expects an array, got {arr.type_name()}", line)
    if not arr.elements:
        return NIL
    return obj.Array(list(arr.elements[1:]))


def _b_keys(args, line):
    _check_arity("keys", args, line, 1)
    h = args[0]
    if not isinstance(h, obj.Hash):
        _err(f"keys() expects a hash, got {h.type_name()}", line)
    return obj.Array([k for k, _ in h.pairs.values()])


def _b_values(args, line):
    _check_arity("values", args, line, 1)
    h = args[0]
    if not isinstance(h, obj.Hash):
        _err(f"values() expects a hash, got {h.type_name()}", line)
    return obj.Array([v for _, v in h.pairs.values()])


def _b_contains(args, line):
    _check_arity("contains", args, line, 2)
    coll, item = args
    if isinstance(coll, obj.Hash):
        return bool_obj(coll.get(item) is not None)
    if isinstance(coll, obj.Array):
        from .evaluator import _objects_equal
        return bool_obj(any(_objects_equal(e, item) for e in coll.elements))
    if isinstance(coll, obj.String) and isinstance(item, obj.String):
        return bool_obj(item.value in coll.value)
    _err(f"contains() not supported on {coll.type_name()}", line)


def _b_delete(args, line):
    _check_arity("delete", args, line, 2)
    h, key = args
    if not isinstance(h, obj.Hash):
        _err(f"delete() expects a hash, got {h.type_name()}", line)
    h.pairs.pop(obj.Hash.hash_key(key), None)
    return h


def _b_str(args, line):
    _check_arity("str", args, line, 1)
    return obj.String(args[0].inspect())


def _b_int(args, line):
    _check_arity("int", args, line, 1)
    a = args[0]
    if isinstance(a, obj.Integer):
        return a
    if isinstance(a, obj.Float):
        return obj.Integer(int(a.value))
    if isinstance(a, obj.Boolean):
        return obj.Integer(1 if a.value else 0)
    if isinstance(a, obj.String):
        try:
            return obj.Integer(int(a.value.strip()))
        except ValueError:
            _err(f"cannot convert string {a.value!r} to int", line)
    _err(f"cannot convert {a.type_name()} to int", line)


def _b_float(args, line):
    _check_arity("float", args, line, 1)
    a = args[0]
    if isinstance(a, obj.Float):
        return a
    if isinstance(a, obj.Integer):
        return obj.Float(float(a.value))
    if isinstance(a, obj.String):
        try:
            return obj.Float(float(a.value.strip()))
        except ValueError:
            _err(f"cannot convert string {a.value!r} to float", line)
    _err(f"cannot convert {a.type_name()} to float", line)


def _b_range(args, line):
    _check_arity("range", args, line, 1, 2, 3)
    for a in args:
        if not isinstance(a, obj.Integer):
            _err("range() arguments must be integers", line)
    vals = [a.value for a in args]
    if len(vals) == 1:
        rng = range(vals[0])
    elif len(vals) == 2:
        rng = range(vals[0], vals[1])
    else:
        if vals[2] == 0:
            _err("range() step must not be zero", line)
        rng = range(vals[0], vals[1], vals[2])
    return obj.Array([obj.Integer(i) for i in rng])


def _numeric_value(a, name, line):
    if isinstance(a, (obj.Integer, obj.Float)):
        return a.value
    _err(f"{name}() expects numbers, got {a.type_name()}", line)


# Script arguments, set by the CLI before execution.
SCRIPT_ARGS = []


def _b_args(args, line):
    _check_arity("args", args, line, 0)
    return obj.Array([obj.String(a) for a in SCRIPT_ARGS])


def _b_read_file(args, line):
    _check_arity("read_file", args, line, 1)
    a = args[0]
    if not isinstance(a, obj.String):
        _err(f"read_file() expects a path string, got {a.type_name()}", line)
    try:
        with open(a.value, "r", encoding="utf-8-sig") as f:
            return obj.String(f.read())
    except OSError as e:
        _err(f"cannot read file {a.value!r}: {e.strerror or e}", line)


def _write(path_obj, content_obj, mode, name, line):
    if not isinstance(path_obj, obj.String) or not isinstance(content_obj, obj.String):
        _err(f"{name}() expects (path string, content string)", line)
    try:
        with open(path_obj.value, mode, encoding="utf-8", newline="") as f:
            f.write(content_obj.value)
    except OSError as e:
        _err(f"cannot write file {path_obj.value!r}: {e.strerror or e}", line)
    return NIL


def _b_write_file(args, line):
    _check_arity("write_file", args, line, 2)
    return _write(args[0], args[1], "w", "write_file", line)


def _b_append_file(args, line):
    _check_arity("append_file", args, line, 2)
    return _write(args[0], args[1], "a", "append_file", line)


def _b_exists(args, line):
    _check_arity("exists", args, line, 1)
    a = args[0]
    if not isinstance(a, obj.String):
        _err(f"exists() expects a path string, got {a.type_name()}", line)
    import os
    return bool_obj(os.path.exists(a.value))


def _b_import(args, line):
    _check_arity("import", args, line, 1)
    a = args[0]
    if not isinstance(a, obj.String):
        _err(f"import() expects a path string, got {a.type_name()}", line)
    from .modules import load_module
    return load_module(a.value, line)


def _b_split(args, line):
    _check_arity("split", args, line, 2)
    s, sep = args
    if not isinstance(s, obj.String) or not isinstance(sep, obj.String):
        _err("split() expects (string, string)", line)
    if sep.value == "":
        parts = list(s.value)
    else:
        parts = s.value.split(sep.value)
    return obj.Array([obj.String(p) for p in parts])


def _b_join(args, line):
    _check_arity("join", args, line, 2)
    arr, sep = args
    if not isinstance(arr, obj.Array) or not isinstance(sep, obj.String):
        _err("join() expects (array, string)", line)
    parts = []
    for e in arr.elements:
        if not isinstance(e, obj.String):
            _err(f"join() array must contain only strings, "
                 f"found {e.type_name()}", line)
        parts.append(e.value)
    return obj.String(sep.value.join(parts))


def _b_upper(args, line):
    _check_arity("upper", args, line, 1)
    a = args[0]
    if not isinstance(a, obj.String):
        _err(f"upper() expects a string, got {a.type_name()}", line)
    return obj.String(a.value.upper())


def _b_lower(args, line):
    _check_arity("lower", args, line, 1)
    a = args[0]
    if not isinstance(a, obj.String):
        _err(f"lower() expects a string, got {a.type_name()}", line)
    return obj.String(a.value.lower())


def _b_trim(args, line):
    _check_arity("trim", args, line, 1)
    a = args[0]
    if not isinstance(a, obj.String):
        _err(f"trim() expects a string, got {a.type_name()}", line)
    return obj.String(a.value.strip())


def _b_replace(args, line):
    _check_arity("replace", args, line, 3)
    s, old, new = args
    if not (isinstance(s, obj.String) and isinstance(old, obj.String)
            and isinstance(new, obj.String)):
        _err("replace() expects (string, string, string)", line)
    return obj.String(s.value.replace(old.value, new.value))


def _b_slice(args, line):
    _check_arity("slice", args, line, 2, 3)
    target = args[0]
    for a in args[1:]:
        if not isinstance(a, obj.Integer):
            _err("slice() indices must be integers", line)
    start = args[1].value
    end = args[2].value if len(args) == 3 else None
    if isinstance(target, obj.Array):
        return obj.Array(list(target.elements[start:end]))
    if isinstance(target, obj.String):
        return obj.String(target.value[start:end])
    _err(f"slice() expects an array or string, got {target.type_name()}", line)


def _b_chr(args, line):
    _check_arity("chr", args, line, 1)
    a = args[0]
    if not isinstance(a, obj.Integer):
        _err(f"chr() expects an int, got {a.type_name()}", line)
    if not (0 <= a.value <= 0x10FFFF):
        _err(f"chr() argument out of range: {a.value}", line)
    return obj.String(chr(a.value))


def _b_ord(args, line):
    _check_arity("ord", args, line, 1)
    a = args[0]
    if not isinstance(a, obj.String) or len(a.value) != 1:
        _err("ord() expects a single-character string", line)
    return obj.Integer(ord(a.value))


def _b_abs(args, line):
    _check_arity("abs", args, line, 1)
    a = args[0]
    if isinstance(a, obj.Integer):
        return obj.Integer(abs(a.value))
    if isinstance(a, obj.Float):
        return obj.Float(abs(a.value))
    _err(f"abs() expects a number, got {a.type_name()}", line)


def _min_max(name, fn, args, line):
    if len(args) == 1 and isinstance(args[0], obj.Array):
        items = args[0].elements
    else:
        items = args
    if not items:
        _err(f"{name}() of empty sequence", line)
    values = [_numeric_value(x, name, line) for x in items]
    best_idx = values.index(fn(values))
    return items[best_idx]


def _b_min(args, line):
    return _min_max("min", min, args, line)


def _b_max(args, line):
    return _min_max("max", max, args, line)


def _b_input(args, line):
    _check_arity("input", args, line, 0, 1)
    if args:
        sys.stdout.write(args[0].inspect())
        sys.stdout.flush()
    try:
        return obj.String(input())
    except EOFError:
        return NIL


def _b_assert(args, line):
    _check_arity("assert", args, line, 1, 2)
    from .evaluator import is_truthy
    if not is_truthy(args[0]):
        msg = args[1].inspect() if len(args) == 2 else "assertion failed"
        _err(msg, line)
    return NIL


def _b_attempt(args, line):
    """Call a zero-argument function, catching any runtime error.

    Returns {"ok": bool, "value": result-or-nil, "error": message-or-nil},
    turning errors into ordinary values you can inspect and pipe."""
    _check_arity("attempt", args, line, 1)
    from .evaluator import apply_function
    h = obj.Hash()
    try:
        value = apply_function(args[0], [], line)
        h.set(obj.String("ok"), bool_obj(True))
        h.set(obj.String("value"), value)
        h.set(obj.String("error"), NIL)
    except PylaRuntimeError as e:
        h.set(obj.String("ok"), bool_obj(False))
        h.set(obj.String("value"), NIL)
        h.set(obj.String("error"), obj.String(e.message))
    return h


def _make(name, fn):
    return obj.Builtin(fn=fn, name=name)


BUILTINS = {
    "print": _make("print", _b_print),
    "write": _make("write", _b_write),
    "len": _make("len", _b_len),
    "type": _make("type", _b_type),
    "push": _make("push", _b_push),
    "pop": _make("pop", _b_pop),
    "first": _make("first", _b_first),
    "last": _make("last", _b_last),
    "rest": _make("rest", _b_rest),
    "keys": _make("keys", _b_keys),
    "values": _make("values", _b_values),
    "contains": _make("contains", _b_contains),
    "delete": _make("delete", _b_delete),
    "str": _make("str", _b_str),
    "int": _make("int", _b_int),
    "float": _make("float", _b_float),
    "range": _make("range", _b_range),
    "args": _make("args", _b_args),
    "read_file": _make("read_file", _b_read_file),
    "write_file": _make("write_file", _b_write_file),
    "append_file": _make("append_file", _b_append_file),
    "exists": _make("exists", _b_exists),
    "import": _make("import", _b_import),
    "split": _make("split", _b_split),
    "join": _make("join", _b_join),
    "upper": _make("upper", _b_upper),
    "lower": _make("lower", _b_lower),
    "trim": _make("trim", _b_trim),
    "replace": _make("replace", _b_replace),
    "slice": _make("slice", _b_slice),
    "chr": _make("chr", _b_chr),
    "ord": _make("ord", _b_ord),
    "abs": _make("abs", _b_abs),
    "min": _make("min", _b_min),
    "max": _make("max", _b_max),
    "input": _make("input", _b_input),
    "assert": _make("assert", _b_assert),
    "attempt": _make("attempt", _b_attempt),
}
