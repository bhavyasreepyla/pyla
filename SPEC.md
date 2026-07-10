# The Pyla Language Specification

Pyla is a small, dynamically-typed scripting language. This document is the
complete reference: everything the language does is described here.

## Running programs

```
pyla program.pyla          # run a file
pyla -c "print(1 + 2)"     # run a string
pyla test dir/             # run every .pyla file in dir as a test
pyla --trace program.pyla  # also print the value leaving every |> stage
pyla --terse-errors x.pyla # one-line errors (no source line/caret/stack)
```

Exit codes: `0` = ran to completion; `1` = parse error, runtime error, or
failed `assert`; `2` = usage error. A statement is terminated by `;`
(optional for the last statement of a block). Comments run from `#` to end
of line.

## Types and truthiness

`int`, `float`, `string`, `bool` (`true` / `false`), `nil`, `array`, `hash`,
`function`. **Only `nil` and `false` are falsy** — `0`, `""`, and `[]` are
all truthy.

- Integer arithmetic stays integer, except `/`: `4 / 2` is int `2`, but
  `7 / 2` is float `3.5`. Any operation mixing int and float yields float.
- `/` or `%` by zero is a runtime error.
- Strings are immutable; `+` concatenates; comparisons are lexicographic.

## Variables

```
let x = 10;        # declare (let always creates/overwrites in current scope)
x = x + 1;         # reassign; ERROR if x was never declared
```

Assignment is an expression, evaluates to the assigned value, and is
right-associative (`a = b = 3`).

## Operators (loosest to tightest)

| level | operators |
|---|---|
| assignment | `=` |
| pipeline | `\|>` |
| logical | `or` then `and` (short-circuit; return the deciding operand: `nil or 7` is `7`, `1 and 2` is `2`) |
| equality | `==` `!=` |
| comparison | `<` `>` `<=` `>=` |
| additive | `+` `-` |
| multiplicative | `*` `/` `%` |
| prefix | `-x` `!x` (`!` returns a bool by truthiness) |
| call / index | `f(x)` `a[i]` `h.key` |

**Pipeline:** `x |> f(a, b)` means `f(x, a, b)`; `x |> f` means `f(x)`.
Left-associative: `x |> f |> g` is `g(f(x))`.

## Control flow

`if` is an expression: it produces the value of the branch taken (or `nil`
if no branch ran). The last expression of any block is the block's value.

```
let sign = if (n < 0) { -1 } else if (n == 0) { 0 } else { 1 };

while (cond) { ... }
for (let i = 0; i < 10; i = i + 1) { ... }   # all three clauses optional
break;      # exit the innermost loop
continue;   # next iteration (for-loops still run their post clause)
```

Loops are statements and produce `nil`.

## Functions

```
let add = fn(a, b) { a + b };        # implicit return of last expression
let f = fn(x) { return x * 2; };     # explicit return also works
```

Functions are first-class values. Closures capture their defining
environment **by reference** (mutating a captured variable is visible to
every closure sharing it). Recursion works via the name bound by `let`.
Calling with the wrong number of arguments is a runtime error.

## Arrays

```
let a = [1, 2, 3];
a[0]          # 1        (negative indices count from the end: a[-1] is 3)
a[99]         # nil      (out-of-range READS return nil)
a[99] = 5     # ERROR    (out-of-range WRITES are errors)
push(a, 4);   # arrays are mutable and passed by reference
```

## Hashes

```
let h = {"name": "Ada", 1: "one", true: "yes"};   # keys: string/int/float/bool
h["name"]     # "Ada";  missing keys read as nil
h.name        # sugar for h["name"] (write works too: h.name = "Lin")
```

Iteration order is insertion order. `keys(h)`, `values(h)`, `delete(h, k)`,
`contains(h, k)`.

## Modules

```
let list = import("std/list");    # returns the module's top-level lets as a hash
list.map([1,2], fn(x){ x * 2 })
```

Paths resolve relative to the importing file, then the interpreter's bundled
stdlib. Modules are cached: importing the same file twice returns the same
hash object.

**std/list:** `map(arr, f)` `filter(arr, pred)` `reduce(arr, init, f)`
`each(arr, f)` `sum` `product` `reverse` `index_of(arr, x)` `any(arr, pred)`
`all(arr, pred)` `sort(arr)` `sort_by(arr, less)` `zip(a, b)` — the
collection is always the first parameter so everything pipes.

**std/math:** `pi` `e` `floor` `ceil` `round` `pow(base, exp)` `sqrt` `gcd`
`lcm` `factorial` `clamp(x, lo, hi)` `is_prime`.

## Builtins

| builtin | behaviour |
|---|---|
| `print(...)` / `write(...)` | print with spaces + newline / raw, no newline |
| `len(x)` | length of string, array, or hash |
| `type(x)` | type name as a string, e.g. `"int"` |
| `push(a, v)` / `pop(a)` | append to array / remove+return last (error if empty) |
| `first(a)` / `last(a)` / `rest(a)` | element access; `rest` returns a new array |
| `keys(h)` / `values(h)` / `delete(h, k)` | hash utilities |
| `contains(coll, x)` | membership: hash key, array element, or substring |
| `str(x)` / `int(x)` / `float(x)` | conversions (bad conversions are errors) |
| `range(n)` / `range(a, b)` / `range(a, b, step)` | array of ints, end-exclusive |
| `abs` `min` `max` | numbers; `min`/`max` take varargs or one array |
| `chr(n)` / `ord(s)` | int <-> single-character string |
| `split(s, sep)` / `join(arr, sep)` | `split(s, "")` splits into chars |
| `upper` `lower` `trim` `replace(s, old, new)` | string tools |
| `slice(x, start)` / `slice(x, start, end)` | sub-array/substring, Python-style |
| `input()` / `input(prompt)` | read a line from stdin (`nil` on EOF) |
| `assert(cond)` / `assert(cond, msg)` | runtime error (exit 1) if cond is falsy |
| `args()` | command-line arguments as an array of strings |
| `read_file(p)` / `write_file(p, s)` / `append_file(p, s)` / `exists(p)` | file I/O |
| `import(path)` | load a module (see Modules) |

## Errors

Parse and runtime errors carry a line number; the CLI also shows the source
line with a caret and, for runtime errors, the call stack:

```
prog.pyla: Runtime error [line 2]: type mismatch: int + string
     2 |     return x + "oops";
  Pyla call stack (outermost first):
    in outer (called at line 6)
```

Common error messages: `identifier not found: NAME`, `type mismatch: T op T`,
`division by zero`, `NAME expected N argument(s), got M`,
`not a function: TYPE`, `array index out of range: N`,
`cannot assign to undefined variable: NAME (use 'let' to declare it)`.

## Grammar summary (EBNF-ish)

```
program    = { statement } ;
statement  = "let" IDENT "=" expr ";"? | "return" expr? ";"?
           | "while" "(" expr ")" block | "for" "(" init? ";" expr? ";" expr? ")" block
           | "break" ";"? | "continue" ";"? | expr ";"? ;
block      = "{" { statement } "}" ;
expr       = literal | IDENT | "(" expr ")" | prefix expr | expr infix expr
           | "if" "(" expr ")" block ( "else" ( block | if-expr ) )?
           | "fn" "(" params? ")" block | expr "(" args? ")" | expr "[" expr "]"
           | expr "." IDENT | expr "|>" expr | expr "=" expr ;
literal    = INT | FLOAT | STRING | "true" | "false" | "nil"
           | "[" args? "]" | "{" ( expr ":" expr ),* "}" ;
```

Trailing commas are allowed in array/hash literals and call arguments.
String escapes: `\n \t \r \" \\ \0`.
