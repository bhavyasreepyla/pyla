"""Runtime value types for Pyla.

Values are wrapped in small classes so we can attach behaviour (type names,
display formatting, hashability) and support a `type()` builtin. Return,
break and continue are modelled as Python exceptions that the evaluator
catches at the right boundaries.
"""

from dataclasses import dataclass, field
from typing import List, Callable, Dict, Tuple


class Object:
    def type_name(self) -> str:
        raise NotImplementedError

    def inspect(self) -> str:
        """Developer-facing representation (used by the REPL and str())."""
        raise NotImplementedError


@dataclass
class Integer(Object):
    value: int

    def type_name(self):
        return "int"

    def inspect(self):
        return str(self.value)


@dataclass
class Float(Object):
    value: float

    def type_name(self):
        return "float"

    def inspect(self):
        return repr(self.value)


@dataclass
class String(Object):
    value: str

    def type_name(self):
        return "string"

    def inspect(self):
        return self.value


@dataclass
class Boolean(Object):
    value: bool

    def type_name(self):
        return "bool"

    def inspect(self):
        return "true" if self.value else "false"


class Nil(Object):
    def type_name(self):
        return "nil"

    def inspect(self):
        return "nil"


@dataclass
class Array(Object):
    elements: List[Object] = field(default_factory=list)

    def type_name(self):
        return "array"

    def inspect(self):
        return "[" + ", ".join(_repr(e) for e in self.elements) + "]"


class Hash(Object):
    """A hash map keyed on immutable Pyla values (int, float, string, bool)."""

    def __init__(self):
        # maps a python hash-key -> (key_object, value_object)
        self.pairs: Dict[Tuple, Tuple[Object, Object]] = {}

    def type_name(self):
        return "hash"

    @staticmethod
    def hash_key(obj: Object):
        if isinstance(obj, (Integer, Float)):
            return ("num", obj.value)
        if isinstance(obj, String):
            return ("str", obj.value)
        if isinstance(obj, Boolean):
            return ("bool", obj.value)
        return None  # not hashable

    def set(self, key: Object, value: Object):
        self.pairs[self.hash_key(key)] = (key, value)

    def get(self, key: Object):
        entry = self.pairs.get(self.hash_key(key))
        return entry[1] if entry is not None else None

    def inspect(self):
        inner = ", ".join(f"{_repr(k)}: {_repr(v)}"
                          for k, v in self.pairs.values())
        return "{" + inner + "}"


@dataclass
class Function(Object):
    parameters: list
    body: object
    env: object
    name: str = ""

    def type_name(self):
        return "function"

    def inspect(self):
        params = ", ".join(p.value for p in self.parameters)
        label = f" {self.name}" if self.name else ""
        return f"fn{label}({params}) {{ ... }}"


@dataclass
class Builtin(Object):
    fn: Callable
    name: str = ""

    def type_name(self):
        return "builtin"

    def inspect(self):
        return f"builtin fn {self.name}"


def _repr(obj: Object) -> str:
    """Like inspect(), but strings are quoted so nested structures read well."""
    if isinstance(obj, String):
        return '"' + obj.value + '"'
    return obj.inspect()


# Singletons -----------------------------------------------------------------
NIL = Nil()
TRUE = Boolean(True)
FALSE = Boolean(False)


def bool_obj(value: bool) -> Boolean:
    return TRUE if value else FALSE
