"""Tree-walking evaluator for Pyla.

`eval_node` recursively walks the AST, producing runtime Objects. Control flow
that unwinds the Python call stack (return / break / continue) is implemented
with dedicated exceptions caught at function and loop boundaries.
"""

from . import ast_nodes as ast
from . import objects as obj
from .objects import NIL, TRUE, FALSE, bool_obj
from .environment import Environment
from .errors import PylaRuntimeError


# Pyla-level call stack, kept for runtime error stack traces.
_call_stack = []


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


def is_truthy(value) -> bool:
    return value is not NIL and value is not FALSE


def evaluate(program, env):
    """Entry point: evaluate a whole program, returning the last value."""
    result = NIL
    try:
        for stmt in program.statements:
            result = eval_node(stmt, env)
    except ReturnSignal as r:
        return r.value
    return result


def eval_node(node, env):
    t = type(node)

    # Statements ------------------------------------------------------------
    if t is ast.ExpressionStatement:
        return eval_node(node.expression, env)
    if t is ast.LetStatement:
        value = eval_node(node.value, env)
        env.define(node.name.value, value)
        return NIL
    if t is ast.ReturnStatement:
        value = NIL if node.value is None else eval_node(node.value, env)
        raise ReturnSignal(value)
    if t is ast.BlockStatement:
        return eval_block(node, env)
    if t is ast.WhileStatement:
        return eval_while(node, env)
    if t is ast.ForStatement:
        return eval_for(node, env)
    if t is ast.BreakStatement:
        raise BreakSignal()
    if t is ast.ContinueStatement:
        raise ContinueSignal()

    # Literals --------------------------------------------------------------
    if t is ast.IntegerLiteral:
        return obj.Integer(node.value)
    if t is ast.FloatLiteral:
        return obj.Float(node.value)
    if t is ast.StringLiteral:
        return obj.String(node.value)
    if t is ast.BooleanLiteral:
        return bool_obj(node.value)
    if t is ast.NilLiteral:
        return NIL
    if t is ast.ArrayLiteral:
        return obj.Array([eval_node(e, env) for e in node.elements])
    if t is ast.HashLiteral:
        return eval_hash_literal(node, env)
    if t is ast.FunctionLiteral:
        return obj.Function(node.parameters, node.body, env, node.name)

    # Expressions -----------------------------------------------------------
    if t is ast.Identifier:
        return eval_identifier(node, env)
    if t is ast.PrefixExpression:
        right = eval_node(node.right, env)
        return eval_prefix(node.operator, right, node.line)
    if t is ast.InfixExpression:
        return eval_infix_expression(node, env)
    if t is ast.IfExpression:
        return eval_if_expression(node, env)
    if t is ast.CallExpression:
        return eval_call(node, env)
    if t is ast.IndexExpression:
        left = eval_node(node.left, env)
        index = eval_node(node.index, env)
        return eval_index(left, index, node.line)
    if t is ast.AssignExpression:
        return eval_assign(node, env)

    raise PylaRuntimeError(f"cannot evaluate node of type {t.__name__}",
                           getattr(node, "line", 0))


def eval_block(block, env):
    result = NIL
    for stmt in block.statements:
        result = eval_node(stmt, env)
    return result


def eval_while(node, env):
    while is_truthy(eval_node(node.condition, env)):
        try:
            eval_node(node.body, env)
        except BreakSignal:
            break
        except ContinueSignal:
            continue
    return NIL


def eval_for(node, env):
    loop_env = env.child()
    if node.init is not None:
        eval_node(node.init, loop_env)
    while node.condition is None or is_truthy(eval_node(node.condition, loop_env)):
        try:
            eval_node(node.body, loop_env)
        except BreakSignal:
            break
        except ContinueSignal:
            pass
        if node.post is not None:
            eval_node(node.post, loop_env)
    return NIL


def eval_identifier(node, env):
    value, found = env.get(node.value)
    if found:
        return value
    from .builtins import BUILTINS
    if node.value in BUILTINS:
        return BUILTINS[node.value]
    raise PylaRuntimeError(f"identifier not found: {node.value}", node.line)


def eval_prefix(operator, right, line):
    if operator == "!":
        return bool_obj(not is_truthy(right))
    if operator == "-":
        if isinstance(right, obj.Integer):
            return obj.Integer(-right.value)
        if isinstance(right, obj.Float):
            return obj.Float(-right.value)
        raise PylaRuntimeError(
            f"unknown operator: -{right.type_name()}", line)
    raise PylaRuntimeError(f"unknown operator: {operator}", line)


def eval_infix_expression(node, env):
    op = node.operator
    # Short-circuiting logical operators must not evaluate the right side eagerly.
    if op == "and":
        left = eval_node(node.left, env)
        if not is_truthy(left):
            return left
        return eval_node(node.right, env)
    if op == "or":
        left = eval_node(node.left, env)
        if is_truthy(left):
            return left
        return eval_node(node.right, env)

    left = eval_node(node.left, env)
    right = eval_node(node.right, env)
    return eval_infix(op, left, right, node.line)


def eval_infix(op, left, right, line):
    # Numeric tower: int op int stays int; anything with a float becomes float.
    if isinstance(left, (obj.Integer, obj.Float)) and isinstance(right, (obj.Integer, obj.Float)):
        return eval_numeric_infix(op, left, right, line)
    if isinstance(left, obj.String) and isinstance(right, obj.String):
        return eval_string_infix(op, left, right, line)
    if op == "==":
        return bool_obj(_objects_equal(left, right))
    if op == "!=":
        return bool_obj(not _objects_equal(left, right))
    if type(left) is not type(right):
        raise PylaRuntimeError(
            f"type mismatch: {left.type_name()} {op} {right.type_name()}", line)
    raise PylaRuntimeError(
        f"unknown operator: {left.type_name()} {op} {right.type_name()}", line)


def eval_numeric_infix(op, left, right, line):
    a, b = left.value, right.value
    both_int = isinstance(left, obj.Integer) and isinstance(right, obj.Integer)

    if op == "+":
        result = a + b
    elif op == "-":
        result = a - b
    elif op == "*":
        result = a * b
    elif op == "/":
        if b == 0:
            raise PylaRuntimeError("division by zero", line)
        if both_int and a % b == 0:
            return obj.Integer(a // b)
        return obj.Float(a / b)
    elif op == "%":
        if b == 0:
            raise PylaRuntimeError("modulo by zero", line)
        result = a % b
    elif op == "<":
        return bool_obj(a < b)
    elif op == ">":
        return bool_obj(a > b)
    elif op == "<=":
        return bool_obj(a <= b)
    elif op == ">=":
        return bool_obj(a >= b)
    elif op == "==":
        return bool_obj(a == b)
    elif op == "!=":
        return bool_obj(a != b)
    else:
        raise PylaRuntimeError(f"unknown operator: {op}", line)

    return obj.Integer(result) if both_int else obj.Float(result)


def eval_string_infix(op, left, right, line):
    a, b = left.value, right.value
    if op == "+":
        return obj.String(a + b)
    if op == "==":
        return bool_obj(a == b)
    if op == "!=":
        return bool_obj(a != b)
    if op == "<":
        return bool_obj(a < b)
    if op == ">":
        return bool_obj(a > b)
    if op == "<=":
        return bool_obj(a <= b)
    if op == ">=":
        return bool_obj(a >= b)
    raise PylaRuntimeError(f"unknown operator: string {op} string", line)


def _objects_equal(left, right):
    if isinstance(left, (obj.Integer, obj.Float)) and isinstance(right, (obj.Integer, obj.Float)):
        return left.value == right.value
    if type(left) is not type(right):
        return False
    if isinstance(left, (obj.String, obj.Boolean)):
        return left.value == right.value
    if left is NIL and right is NIL:
        return True
    return left is right


def eval_if_expression(node, env):
    condition = eval_node(node.condition, env)
    if is_truthy(condition):
        return eval_node(node.consequence, env)
    if node.alternative is not None:
        return eval_node(node.alternative, env)
    return NIL


def eval_hash_literal(node, env):
    result = obj.Hash()
    for key_node, value_node in node.pairs:
        key = eval_node(key_node, env)
        if obj.Hash.hash_key(key) is None:
            raise PylaRuntimeError(
                f"unusable as hash key: {key.type_name()}", node.line)
        result.set(key, eval_node(value_node, env))
    return result


def eval_index(left, index, line):
    if isinstance(left, obj.Array):
        if not isinstance(index, obj.Integer):
            raise PylaRuntimeError(
                f"array index must be int, got {index.type_name()}", line)
        return _array_get(left, index.value)
    if isinstance(left, obj.String):
        if not isinstance(index, obj.Integer):
            raise PylaRuntimeError(
                f"string index must be int, got {index.type_name()}", line)
        return _string_get(left, index.value)
    if isinstance(left, obj.Hash):
        if obj.Hash.hash_key(index) is None:
            raise PylaRuntimeError(
                f"unusable as hash key: {index.type_name()}", line)
        found = left.get(index)
        return found if found is not None else NIL
    raise PylaRuntimeError(
        f"index operator not supported on {left.type_name()}", line)


def _array_get(arr, i):
    n = len(arr.elements)
    if i < 0:
        i += n
    if 0 <= i < n:
        return arr.elements[i]
    return NIL


def _string_get(s, i):
    n = len(s.value)
    if i < 0:
        i += n
    if 0 <= i < n:
        return obj.String(s.value[i])
    return NIL


def eval_assign(node, env):
    value = eval_node(node.value, env)
    target = node.target
    if isinstance(target, ast.Identifier):
        if not env.assign(target.value, value):
            raise PylaRuntimeError(
                f"cannot assign to undefined variable: {target.value} "
                f"(use 'let' to declare it)", node.line)
        return value
    if isinstance(target, ast.IndexExpression):
        container = eval_node(target.left, env)
        index = eval_node(target.index, env)
        _assign_index(container, index, value, node.line)
        return value
    raise PylaRuntimeError("invalid assignment target", node.line)


def _assign_index(container, index, value, line):
    if isinstance(container, obj.Array):
        if not isinstance(index, obj.Integer):
            raise PylaRuntimeError(
                f"array index must be int, got {index.type_name()}", line)
        i, n = index.value, len(container.elements)
        if i < 0:
            i += n
        if not (0 <= i < n):
            raise PylaRuntimeError(
                f"array index out of range: {index.value}", line)
        container.elements[i] = value
        return
    if isinstance(container, obj.Hash):
        if obj.Hash.hash_key(index) is None:
            raise PylaRuntimeError(
                f"unusable as hash key: {index.type_name()}", line)
        container.set(index, value)
        return
    raise PylaRuntimeError(
        f"cannot index-assign into {container.type_name()}", line)


def eval_call(node, env):
    function = eval_node(node.function, env)
    args = [eval_node(a, env) for a in node.arguments]
    result = apply_function(function, args, node.line)
    if node.pipe_text:
        from . import diagnostics
        if diagnostics.TRACE_PIPES:
            diagnostics.trace_pipe(node.line, node.pipe_text, result)
    return result


def apply_function(function, args, line):
    if isinstance(function, obj.Function):
        if len(args) != len(function.parameters):
            name = function.name or "<anonymous>"
            raise PylaRuntimeError(
                f"{name} expected {len(function.parameters)} argument(s), "
                f"got {len(args)}", line)
        call_env = Environment(outer=function.env)
        for param, arg in zip(function.parameters, args):
            call_env.define(param.value, arg)
        _call_stack.append((function.name or "<anonymous>", line))
        try:
            result = eval_node(function.body, call_env)
        except ReturnSignal as r:
            return r.value
        except PylaRuntimeError as e:
            if e.pyla_stack is None:
                e.pyla_stack = list(_call_stack)
            raise
        finally:
            _call_stack.pop()
        return result
    if isinstance(function, obj.Builtin):
        return function.fn(args, line)
    from .compiler import Closure
    if isinstance(function, Closure):
        # A VM closure crossing the engine boundary: run it on the VM.
        from .vm import call_closure
        return call_closure(function, args, line)
    raise PylaRuntimeError(f"not a function: {function.type_name()}", line)
