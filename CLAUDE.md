# CLAUDE.md — project context for the Ideas folder

This folder contains **Pyla**, a small dynamically-typed, pipeline-first
scripting language (`|>` is its signature feature) with two execution
engines, plus **tinylm**, a from-scratch neural language model trained on
Pyla source code. Everything is pure Python; the only third-party dependency
is numpy (used by tinylm only, never by Pyla). DESIGN.md records the design
rationale and the language-failure post-mortems v0.3 was built against.

## Build / run

Pyla is installed editable (`pip install -e .`), so the `pyla` command is on
PATH and reflects source changes immediately.

```sh
pyla                                # interactive REPL (:help, :env, :quit)
pyla examples/fib.pyla              # run a program (bytecode VM = default)
pyla --walk examples/fib.pyla       # run on the tree-walking evaluator
pyla -c 'print(2 + 3)'              # one-liner (quoting: see gotchas)
python bench.py                     # tree-walker vs VM benchmark
python tinylm.py train              # train the char-level LM on examples/*.pyla
python tinylm.py sample --temp 0.8  # generate Pyla-ish code from saved model
python tinylm.py check              # numerical gradient check (must PASS)
```

## Test

```sh
python -m unittest discover -s tests    # full suite; must stay green
```

Test files: `tests/test_lexer.py`, `tests/test_parser.py`,
`tests/test_evaluator.py`, `tests/test_vm.py`, `tests/test_modules.py`.

## Architecture

Pipeline: source → `pyla/lexer.py` (tokens, tracks line/col) →
`pyla/parser.py` (Pratt parser) → `pyla/ast_nodes.py` (AST dataclasses) →
one of two engines:

1. **Tree-walker**: `pyla/evaluator.py` — the reference semantics.
2. **Bytecode VM**: `pyla/compiler.py` (AST → flat `(opcode, arg, line)`
   tuples) + `pyla/vm.py` (stack machine with explicit call frames).

Shared runtime: `pyla/objects.py` (value types), `pyla/environment.py`
(scope chains — closures capture by reference), `pyla/builtins.py`
(37 builtins incl. file I/O and args()), `pyla/errors.py` (errors carry
line/col and a `pyla_stack` for tracebacks), `pyla/diagnostics.py`
(source-line + caret + call-stack formatting used by the CLI),
`pyla/modules.py` (import: cached by absolute path, resolves relative to
importing file then the bundled `pyla/std/`), `pyla/cli.py` (the `pyla`
entry point; packaging in `pyproject.toml`). The stdlib in `pyla/std/*.pyla`
is written in Pyla; its functions take the collection as FIRST parameter so
they compose with `|>` — keep that convention. `editor/vscode-pyla` is the
VS Code extension (also copied into ~/.vscode/extensions). `tinylm.py` is
standalone (Bengio-2003 MLP char model, manual backprop).

Parser-level sugar (works on both engines automatically): dot access
(`h.key` → `h["key"]`) and pipelines (`x |> f(a)` → `f(x, a)`).

Cross-engine calls: modules are evaluated by the tree-walker, so VM code can
receive tree-walker `Function`s and vice versa. The VM's CALL delegates
unknown function kinds to `evaluator.apply_function`, and the evaluator
delegates VM `Closure`s to `vm.call_closure`. Each `CompiledFunction` carries
its own constants pool precisely so its closures are callable from anywhere.
Dot access (`h.key`) is parser-level sugar for `h["key"]` — no engine code.

## Conventions & gotchas

- **The tree-walker is the source of truth for semantics.** The VM must match
  it exactly — values, types (int vs float), and error message strings.
  `tests/test_vm.py` enforces this parity, including byte-identical stdout on
  every program in `examples/`. Any language change must be made in BOTH
  engines and covered by a parity test.
- Language semantics to remember: only `nil` and `false` are falsy; `4/2` is
  int but `7/2` is float; the last expression of a block/function is its value
  (implicit return); `let` declares, bare `=` reassigns (error if undeclared);
  out-of-range array reads return `nil` but out-of-range writes are errors;
  negative indices count from the end; `and`/`or` short-circuit and return the
  deciding operand.
- The VM's deep-recursion test depends on VM frames being plain list entries —
  don't rewrite `vm.py`'s CALL/RET to use Python recursion.
- tinylm's backward() is hand-derived; if you touch the model, run
  `python tinylm.py check` (finite-difference gradient check) before training.
- PowerShell 5.1 mangles inner quotes in `pyla -c "..."` one-liners; run them
  from bash/Git Bash, or put the program in a file.
- No pip installs for the language itself — Pyla must stay stdlib-only.
- Module gotcha: `import` returns the SAME cached hash object for the same
  absolute path, and imports inside a script resolve relative to that
  script's directory (`modules.set_base_dir` is called by the CLI).

## State / ideas

- The language was renamed from Lume to **Pyla** (after its author, Bhavya
  Sree Pyla) because "lume" collides with existing projects. Author is
  credited in pyproject.toml, LICENSE and README (with a Claude credit).
- Done (v0.4.0): full language (closures, recursion, arrays, hashes, control
  flow, modules/import, dot access, **pipelines `|>`**, string toolkit, file
  I/O, args()), **brainrot mode** (Gen Z dialect: slang=True through
  lexer/parser/run/vm_run; `.fr` files auto-enable; `--brainrot` flag;
  `:brainrot` REPL toggle; strictly opt-in so slang words stay valid
  identifiers in normal mode), `pyla --zen` easter egg, ASCII REPL banner,
  stdlib in Pyla (std/list, std/math), caret + call-stack diagnostics,
  BOM-tolerant source loading, 79 tests, bytecode VM at ~2.5x (default
  engine), `pyla` console command (installed editable), VS Code extension
  for `.pyla`/`.fr` (installed locally), brainfuck-in-Pyla proof, trained
  tinylm model. PyPI name `pyla-lang` verified available (July 2026).
- Harness contract (for the pyla-bench experiment planned with the sibling
  project in `C:\Users\Pylab\desktop\ME\more`): exit codes 0/1/2 are the
  grading interface; `assert` exits 1 with a message; `pyla test dir/` runs
  every .pyla/.fr file and prints `PASS name`/`FAIL name` + summary;
  `SPEC.md` is the complete one-read language reference (its claims are
  executable via `tests/spec_conformance.pyla` — keep spec and
  implementation in lockstep). The bench plan: 5-10 buggy Pyla programs +
  hidden grading scripts, run through `agentic-bug-finder`, measured
  with/without SPEC.md in the repo (in-context language acquisition).
- To publish: `python -m twine upload dist/*` with the user's PyPI API token
  (NOT done — publishing under their account is their decision).
- Natural next steps: structs with methods, try/catch error handling, VM
  local-slot optimization (resolve names to indices at compile time), REPL
  syntax highlighting, publish VS Code extension to the marketplace.
