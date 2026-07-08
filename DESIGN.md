# Why Pyla looks the way it does

New languages mostly die. Before v0.3 we studied the post-mortems and built
against the documented failure modes.

## Lesson 1: Most languages are never finished
Christoffer Lernö (creator of C3): *"The obvious and most common way a
language can fail is by never being completed. It doesn't matter how good the
features are if the language can't be implemented."*

**Pyla's answer:** ship complete, small, and tested. Two full engines
(tree-walking interpreter and bytecode VM) held to identical semantics by a
parity suite; 70 tests; every feature that exists is finished — there is no
half-implemented syntax in the grammar.

## Lesson 2: "Build it and they will come" doesn't work
Lernö again: quality alone doesn't reach users. A language without an install
path, editor support, and docs never gets a second user.

**Pyla's answer:** `pip install pyla-lang` gives a `pyla` command on PATH; a
VS Code extension (`editor/vscode-pyla`) provides highlighting, bracket
matching and comment toggling; the README teaches the language in one page;
`examples/` are runnable and cover every feature.

## Lesson 3: Error messages ARE the implementation quality
Walter Bright (creator of D): a compiler that prints "bad syntax" has failed
its user. Diagnostics are the part of the language people actually see.

**Pyla's answer:** every error carries a line (and column for parse errors).
The CLI shows the offending source line with a caret, and runtime errors come
with a full Pyla call stack — from both engines, identically:

```
demo.pyla: Runtime error [line 2]: type mismatch: int + string
     2 |     return x + "oops";
  Pyla call stack (outermost first):
    in outer (called at line 6)
    in middle (called at line 5)
    in inner (called at line 2)
```

## Lesson 4: A language needs an identity
"Yet another toy interpreter" gives nobody a reason to type it. A language
needs one feature that shapes how programs are written.

**Pyla's answer: pipeline-first.** The `|>` operator threads a value as the
first argument of the next call, so data transformations read left-to-right
in execution order:

```
range(1, 21)
    |> list.filter(fn(x) { x % 2 == 0 })
    |> list.map(fn(x) { x * x })
    |> list.sum()
    |> print;
```

The stdlib is deliberately designed around it: every `std/list` function
takes the collection as its first parameter precisely so it pipes well.

## Lesson 5: A scripting language must script
A language that can't read a file, take arguments, or write output can't do
a single real job, and gets abandoned after the fibonacci demo.

**Pyla's answer:** `read_file` / `write_file` / `append_file` / `exists`,
`args()` for command-line arguments, `input()`, a string toolkit
(split/join/trim/replace/upper/lower/slice), and modules so scripts can be
organized. BOM-tolerant file reading, because real Windows tools write BOMs.

## Deliberate non-goals
- **No static types, no generics, no macros** — scope creep is failure mode #1.
- **No self-hosting ambitions** — Python is the substrate; the VM is for
  semantics and speed, not bootstrapping.
- **Breaking changes are allowed pre-1.0** but must update both engines, the
  parity tests, and the docs in the same commit.
