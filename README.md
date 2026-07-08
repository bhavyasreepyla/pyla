# Pyla

A small, dynamically-typed, **pipeline-first** scripting language, implemented
in pure Python (standard library only, no dependencies). Data flows left to
right through the `|>` operator, so programs read in the order they execute:

```
range(1, 21)
    |> list.filter(fn(x) { x % 2 == 0 })
    |> list.map(fn(x) { x * x })
    |> list.sum()
    |> print;                              # 1540
```

Under the hood it is a complete language implementation with **two execution
engines** that are held to identical behaviour by parity tests:

```
source text -> Lexer -> Pratt Parser -> AST -> Tree-walking Evaluator
                                            \-> Bytecode Compiler -> Stack VM
```

The bytecode VM runs 2–3x faster than the tree-walker and, because it manages
its own call frames, supports recursion far deeper than Python's own limit.

This repo also contains **tinylm** (`tinylm.py`): a character-level neural
language model built from scratch in numpy with hand-derived backpropagation
(verified by numerical gradient check), trained on the Pyla programs in
`examples/` so it generates Pyla-looking code.

It supports first-class functions, closures, recursion, arrays, hashes,
`if`/`else if`/`else`, `while`, C-style `for`, `break`/`continue`, a numeric
tower (int promotes to float), short-circuit `and`/`or`, and error messages that
point at a line number.

## Install

```sh
pip install pyla-lang     # the language is Pyla; the command is pyla
```

(From a clone of this repo, `pip install .` does the same.)

```sh
pyla                          # interactive REPL
pyla examples/fib.pyla        # run a program (bytecode VM, the default)
pyla test mytests/            # run every .pyla file in a dir; exit 1 if any fail
pyla --walk examples/fib.pyla # run on the tree-walking evaluator
pyla -c 'print(2 + 3)'        # run a one-liner
pyla --version
```

Exit codes are a contract: `0` success, `1` parse/runtime error or failed
`assert` or failed tests, `2` usage error — so Pyla plugs directly into any
CI or grading harness. The full language fits in one document:
[SPEC.md](SPEC.md), whose claims are themselves executable
(`pyla tests/spec_conformance.pyla`).

Without installing, `python pyla.py ...` from this directory does the same.
Benchmark the two engines with `python bench.py`.

Run the test suite (79 tests, standard-library `unittest`):

```sh
python -m unittest discover -s tests
```

Train and sample the tiny language model (requires numpy):

```sh
python tinylm.py check    # verify hand-written gradients numerically
python tinylm.py train    # ~30s; saves tinylm_model.npz, prints a sample
python tinylm.py sample --temp 0.8 -n 400 --prompt "let fib = "
```

## A taste of the language

```
# variables and functions are declared with `let`
let greet = fn(name) { "Hello, " + name + "!" };
print(greet("world"));

# recursion
let fib = fn(n) { if (n < 2) { n } else { fib(n-1) + fib(n-2) } };
print(fib(20));                 # 6765

# closures keep private state
let counter = fn() { let n = 0; fn() { n = n + 1; n } };
let next = counter();
print(next(), next(), next());  # 1 2 3

# arrays, hashes, loops
let squares = [];
for (let i = 1; i <= 5; i = i + 1) { push(squares, i * i); }
print(squares);                 # [1, 4, 9, 16, 25]

let ages = {"ada": 36, "alan": 41};
print(ages["ada"]);             # 36
print(ages.alan);               # 41 -- h.key is sugar for h["key"]

# modules: import() returns a module's top-level bindings as a hash
let math = import("std/math");
let list = import("std/list");
print(math.sqrt(2));                          # 1.414...
print(list.sort_by([3, 1, 2], fn(a, b) { a > b }));  # [3, 2, 1]
```

The last expression in a function body (or block) is its value, so `return` is
optional. `if`/`else` is an expression and produces a value.

## Language reference

### Types
`int`, `float`, `string`, `bool` (`true`/`false`), `nil`, `array`, `hash`,
`function`. Only `nil` and `false` are falsy; everything else (including `0` and
`""`) is truthy.

### Operators
- Arithmetic: `+ - * / %` (`+` also concatenates strings). Integer `/` stays an
  integer when it divides evenly, otherwise becomes a float.
- Comparison: `== != < > <= >=` (work on numbers and strings).
- Logical: `and`, `or` (short-circuit), `!` (negation).
- Pipeline: `x |> f(a, b)` is `f(x, a, b)`; `x |> f` is `f(x)`. Left
  associative, binds looser than everything except `=`, so `x + 1 |> f`
  pipes the sum. The stdlib takes collections as first parameters so
  everything pipes naturally.
- Assignment: `x = v`, `arr[i] = v`, `hash[k] = v` (right-associative). Use
  `let` to declare; plain `=` reassigns an existing binding.
- Indexing: `arr[i]`, `str[i]` (negative indices count from the end;
  out-of-range reads return `nil`), `hash[key]`, and `hash.key` sugar.

### Modules
`import("path/to/module")` loads a `.pyla` file once (cached by absolute
path), evaluates it, and returns its top-level bindings as a hash. Paths
resolve relative to the importing file, falling back to the interpreter's
bundled library. The standard library ships with `std/list` (map, filter,
reduce, sort_by, zip, ...) and `std/math` (sqrt, pow, gcd, factorial,
is_prime, ...) — both written in Pyla itself.

### Control flow
```
if (cond) { ... } else if (cond) { ... } else { ... }
while (cond) { ... }
for (init; cond; post) { ... }
break;   continue;
```

### Builtins
`print` `write` `len` `type` `push` `pop` `first` `last` `rest` `keys` `values`
`contains` `delete` `str` `int` `float` `range` `abs` `min` `max` `chr` `ord`
`input` `assert` `import` `split` `join` `upper` `lower` `trim` `replace`
`slice` `args` `read_file` `write_file` `append_file` `exists`.

### Diagnostics
Errors show the offending source line with a caret (parse errors) and a full
Pyla call stack (runtime errors) — from both engines, identically. See
[DESIGN.md](DESIGN.md) for the design rationale and the language post-mortems
Pyla was built against.

### Brainrot mode (the Gen Z dialect)
Pyla ships with an optional slang dialect. Files ending in `.fr` enable it
automatically; `--brainrot` forces it anywhere; `:brainrot` toggles it in the
REPL. Same grammar, same semantics, different drip:

| standard | brainrot | | standard | brainrot |
|---|---|---|---|---|
| `let` | `fr` | | `true` | `nocap` |
| `fn` | `cook` | | `false` | `cap` |
| `return` | `yeet` | | `nil` | `ghosted` |
| `if` / `else` | `vibecheck` / `nah` | | `print` | `yap` |
| `while` / `for` | `grind` / `farm` | | `input` | `spill` |
| `break` / `continue` | `dip` / `skip` | | `assert` | `sheesh` |

```
fr fib = cook(n) {
    vibecheck (n < 2) { yeet n; }
    yeet fib(n - 1) + fib(n - 2);
};
yap("fib(15) is lowkey", fib(15));
sheesh(fib(10) == 55, "math is capping");
```

The dialect is strictly opt-in: in normal mode every slang word is just an
ordinary identifier. Run `pyla --zen` for the language's guiding principles.

### Editor support
`editor/vscode-pyla` is a VS Code extension with syntax highlighting, bracket
matching, auto-indent and comment toggling for `.pyla` and `.fr` files.

## Project layout

| File | Responsibility |
|------|----------------|
| `pyla/tokens.py`      | Token types and the `Token` record |
| `pyla/lexer.py`       | Source text -> tokens (tracks line/column) |
| `pyla/ast_nodes.py`   | AST node dataclasses |
| `pyla/parser.py`      | Pratt parser: tokens -> AST |
| `pyla/objects.py`     | Runtime value types |
| `pyla/environment.py` | Lexical scopes / closures |
| `pyla/evaluator.py`   | Tree-walking evaluator (reference semantics) |
| `pyla/compiler.py`    | AST -> bytecode compiler |
| `pyla/vm.py`          | Stack-based bytecode virtual machine |
| `pyla/builtins.py`    | Built-in functions |
| `pyla/modules.py`     | Module loader (`import`), caching + circular-import detection |
| `pyla/std/`           | Standard library, written in Pyla (`std/list`, `std/math`) |
| `pyla/repl.py`        | Interactive REPL |
| `pyla/cli.py`         | The `pyla` command (VM by default, `--walk` for the tree-walker) |
| `pyla.py`             | Repo-local wrapper around the CLI |
| `pyproject.toml`      | Packaging; `pip install .` provides the `pyla` command |
| `bench.py`            | Tree-walker vs VM benchmark |
| `tinylm.py`           | From-scratch neural language model trained on Pyla code |
| `examples/`           | Sample programs (incl. a Brainfuck interpreter written in Pyla) |
| `tests/`              | `unittest` suite: lexer, parser, evaluator, VM parity |

## Examples

- `examples/fib.pyla` — recursion and iteration
- `examples/closures.pyla` — closures and partial application
- `examples/higher_order.pyla` — `map`/`filter`/`reduce` written in Pyla
- `examples/fizzbuzz.pyla` — control flow, `break`/`continue`
- `examples/data_structures.pyla` — arrays, hashes, nesting, negative indexing
- `examples/modules_demo.pyla` — imports, dot access, stdlib, struct-like objects
- `examples/pipelines.pyla` — the `|>` operator doing what it does best
- `examples/brainrot.fr` — the Gen Z dialect, in its natural habitat
- `examples/brainfuck.pyla` — a Brainfuck interpreter written *in Pyla*

## Credits

Pyla was created by **Bhavya Sree Pyla**, designed and implemented in
collaboration with **Claude** (Anthropic's Fable 5 model) via Claude Code.
The language-design post-mortems it was built against are documented in
[DESIGN.md](DESIGN.md). MIT licensed.
