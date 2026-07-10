"""A stack-based bytecode virtual machine for Pyla.

Executes the flat instruction stream produced by compiler.py. Compared to the
tree-walking evaluator it avoids a Python function call per AST node: one
dispatch loop, one shared operand stack, and explicit call frames. Semantics
(including error messages) intentionally match the tree-walker; the parity
tests in tests/test_vm.py hold both engines to identical behaviour.

Closures reuse the same Environment chain as the tree-walker, so captured
variables are shared by reference and remain mutable.
"""

from . import compiler as C
from . import diagnostics
from . import objects as obj
from .objects import NIL, TRUE, FALSE, bool_obj
from .environment import Environment
from .errors import PylaRuntimeError
from .evaluator import (is_truthy, eval_infix, eval_prefix, eval_index,
                        _assign_index)
from .builtins import BUILTINS


class Frame:
    __slots__ = ("fn", "ip", "envs", "call_line")

    def __init__(self, fn, env, call_line=0):
        self.fn = fn
        self.ip = 0
        self.envs = [env]
        self.call_line = call_line


def vm_run(source, env=None, slang=False):
    """Compile and execute source, returning the program's final value."""
    main = C.compile_source(source, slang)
    if env is None:
        env = Environment()
    return execute(main, env)


def call_closure(closure, args, line=0):
    """Invoke a compiled closure from outside the VM loop (used by the
    tree-walker when a VM function crosses the engine boundary)."""
    fn = closure.fn
    if len(args) != len(fn.params):
        name = fn.name or "<anonymous>"
        raise PylaRuntimeError(
            f"{name} expected {len(fn.params)} argument(s), got {len(args)}",
            line)
    env = Environment(outer=closure.env)
    for p, a in zip(fn.params, args):
        env.store[p] = a
    return execute(fn, env)


def execute(main, global_env):
    stack = []
    frames = [Frame(main, global_env)]
    try:
        return _dispatch(stack, frames)
    except PylaRuntimeError as e:
        if e.pyla_stack is None:
            e.pyla_stack = [(f.fn.name or "<anonymous>", f.call_line)
                            for f in frames[1:]]
        raise


def _dispatch(stack, frames):
    frame = frames[0]
    code = frame.fn.code
    consts = frame.fn.constants
    ip = 0

    while True:
        op, arg, line = code[ip]
        ip += 1

        if op == C.CONST:
            stack.append(consts[arg])
        elif op == C.GET:
            e = frame.envs[-1]
            while e is not None:
                if arg in e.store:
                    stack.append(e.store[arg])
                    break
                e = e.outer
            else:
                b = BUILTINS.get(arg)
                if b is None:
                    raise PylaRuntimeError(f"identifier not found: {arg}", line)
                stack.append(b)
        elif op == C.BINARY:
            b = stack.pop()
            a = stack.pop()
            # Fast path for the overwhelmingly common int-int case.
            if type(a) is obj.Integer and type(b) is obj.Integer:
                x, y = a.value, b.value
                if arg == "+":
                    stack.append(obj.Integer(x + y))
                elif arg == "-":
                    stack.append(obj.Integer(x - y))
                elif arg == "*":
                    stack.append(obj.Integer(x * y))
                elif arg == "<":
                    stack.append(TRUE if x < y else FALSE)
                elif arg == ">":
                    stack.append(TRUE if x > y else FALSE)
                elif arg == "<=":
                    stack.append(TRUE if x <= y else FALSE)
                elif arg == ">=":
                    stack.append(TRUE if x >= y else FALSE)
                elif arg == "==":
                    stack.append(TRUE if x == y else FALSE)
                elif arg == "!=":
                    stack.append(TRUE if x != y else FALSE)
                else:
                    stack.append(eval_infix(arg, a, b, line))
            else:
                stack.append(eval_infix(arg, a, b, line))
        elif op == C.JUMP:
            ip = arg
        elif op == C.JF:
            if not is_truthy(stack.pop()):
                ip = arg
        elif op == C.POP:
            stack.pop()
        elif op == C.CALL:
            if arg:
                args = stack[-arg:]
                del stack[-arg:]
            else:
                args = []
            callee = stack.pop()
            if isinstance(callee, C.Closure):
                fn = callee.fn
                if len(args) != len(fn.params):
                    name = fn.name or "<anonymous>"
                    raise PylaRuntimeError(
                        f"{name} expected {len(fn.params)} argument(s), "
                        f"got {len(args)}", line)
                call_env = Environment(outer=callee.env)
                for p, a in zip(fn.params, args):
                    call_env.store[p] = a
                frame.ip = ip
                frame = Frame(fn, call_env, line)
                frames.append(frame)
                code = fn.code
                consts = fn.constants
                ip = 0
            elif isinstance(callee, obj.Builtin):
                stack.append(callee.fn(args, line))
            elif isinstance(callee, obj.Function):
                # A tree-walker closure (e.g. exported by a module): let the
                # tree-walking evaluator apply it.
                from .evaluator import apply_function
                stack.append(apply_function(callee, args, line))
            else:
                raise PylaRuntimeError(
                    f"not a function: {callee.type_name()}", line)
        elif op == C.RET:
            value = stack.pop()
            frames.pop()
            if not frames:
                return value
            frame = frames[-1]
            code = frame.fn.code
            consts = frame.fn.constants
            ip = frame.ip
            stack.append(value)
        elif op == C.NIL:
            stack.append(NIL)
        elif op == C.TRUE:
            stack.append(TRUE)
        elif op == C.FALSE:
            stack.append(FALSE)
        elif op == C.DEFINE:
            frame.envs[-1].store[arg] = stack.pop()
        elif op == C.ASSIGN:
            value = stack[-1]
            e = frame.envs[-1]
            while e is not None:
                if arg in e.store:
                    e.store[arg] = value
                    break
                e = e.outer
            else:
                raise PylaRuntimeError(
                    f"cannot assign to undefined variable: {arg} "
                    f"(use 'let' to declare it)", line)
        elif op == C.CLOSURE:
            stack.append(C.Closure(consts[arg], frame.envs[-1]))
        elif op == C.INDEX:
            index = stack.pop()
            left = stack.pop()
            stack.append(eval_index(left, index, line))
        elif op == C.SET_INDEX:
            value = stack.pop()
            index = stack.pop()
            container = stack.pop()
            _assign_index(container, index, value, line)
            stack.append(value)
        elif op == C.ARRAY:
            if arg:
                elements = stack[-arg:]
                del stack[-arg:]
            else:
                elements = []
            stack.append(obj.Array(elements))
        elif op == C.HASH:
            h = obj.Hash()
            if arg:
                items = stack[-2 * arg:]
                del stack[-2 * arg:]
                for i in range(0, len(items), 2):
                    key = items[i]
                    if obj.Hash.hash_key(key) is None:
                        raise PylaRuntimeError(
                            f"unusable as hash key: {key.type_name()}", line)
                    h.set(key, items[i + 1])
            stack.append(h)
        elif op == C.NEG:
            stack.append(eval_prefix("-", stack.pop(), line))
        elif op == C.NOT:
            stack.append(bool_obj(not is_truthy(stack.pop())))
        elif op == C.JF_KEEP:
            if not is_truthy(stack[-1]):
                ip = arg
        elif op == C.JT_KEEP:
            if is_truthy(stack[-1]):
                ip = arg
        elif op == C.PUSH_ENV:
            frame.envs.append(Environment(outer=frame.envs[-1]))
        elif op == C.POP_ENV:
            frame.envs.pop()
        elif op == C.TRACE_PIPE:
            if diagnostics.TRACE_PIPES:
                diagnostics.trace_pipe(line, arg, stack[-1])
        else:
            raise PylaRuntimeError(f"unknown opcode: {op}", line)
