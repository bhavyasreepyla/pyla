"""Command-line interface for Pyla.

Usage:
    pyla                        # interactive REPL
    pyla script.pyla            # run a program (bytecode VM, the default)
    pyla script.fr              # .fr files run in brainrot mode automatically
    pyla test dir/              # run every .pyla/.fr file in dir as a test
    pyla --walk script.pyla     # run on the tree-walking evaluator instead
    pyla --brainrot script.pyla # force the Gen Z dialect on any file
    pyla -c "print(1 + 2)"      # run a one-liner
    pyla --zen                  # the Way of the Pipe
    pyla --version

Exit codes: 0 = success, 1 = runtime/parse error or failed assert or failed
tests, 2 = usage error (unreadable file, bad arguments).
"""

import os
import sys

from . import __version__
from .errors import PylaError
from . import repl
from . import modules

ZEN = """\
The Way of the Pipe                        ~ pyla --zen

  Data flows downhill; let it.
  Read code the way water moves: left to right, never backwards.
  A pipeline you can say out loud is a pipeline you can trust.
  Small tools, joined well, beat one big tool joined badly.
  The collection goes first, so the next step can find it.
  Only nil and false are false; everything real is true.
  An error without a line number is an accusation without evidence.
  Two engines, one truth: if they disagree, that's a bug, not a feature.
  Finished and small beats ambitious and abandoned.
  fr fr, no cap.
"""


def run_source(source, filename="<input>", use_vm=True, slang=False):
    if use_vm:
        from .vm import vm_run
        runner = vm_run
    else:
        from . import run as runner
    try:
        runner(source, slang=slang)
    except PylaError as e:
        from .diagnostics import format_error
        sys.stderr.write(format_error(e, source, filename) + "\n")
        return 1
    return 0


def run_tests(dir_path, use_vm=True):
    """Run every .pyla/.fr file in dir_path as a test.

    A file passes when it runs to completion (asserts included) without
    error. Prints one `PASS name` / `FAIL name` line per file plus a summary;
    exits 0 only if everything passed.
    """
    import glob
    if not os.path.isdir(dir_path):
        sys.stderr.write(f"error: not a directory: {dir_path}\n")
        return 2
    files = sorted(glob.glob(os.path.join(dir_path, "*.pyla"))
                   + glob.glob(os.path.join(dir_path, "*.fr")))
    if not files:
        sys.stderr.write(f"error: no .pyla or .fr files in {dir_path}\n")
        return 2

    if use_vm:
        from .vm import vm_run
        runner = vm_run
    else:
        from . import run as runner

    failed = 0
    for path in files:
        name = os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                source = f.read()
        except OSError as e:
            print(f"FAIL {name}")
            sys.stderr.write(f"  cannot read {path}: {e}\n")
            failed += 1
            continue
        modules.set_base_dir(os.path.dirname(os.path.abspath(path)))
        try:
            runner(source, slang=path.endswith(".fr"))
            print(f"PASS {name}")
        except PylaError as e:
            print(f"FAIL {name}")
            from .diagnostics import format_error
            indented = "\n".join(
                "  " + l for l in format_error(e, source, name).splitlines())
            sys.stderr.write(indented + "\n")
            failed += 1

    total = len(files)
    print(f"{total - failed} passed, {failed} failed ({total} total)")
    return 1 if failed else 0


def main(argv=None):
    if argv is None:
        argv = sys.argv
    args = argv[1:]

    use_vm = "--walk" not in args
    slang = "--brainrot" in args
    args = [a for a in args if a not in ("--walk", "--vm", "--brainrot")]

    if not args:
        repl.start(__version__)
        return 0
    if args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args[0] in ("-v", "--version"):
        print(f"Pyla {__version__}")
        return 0
    if args[0] == "--zen":
        print(ZEN, end="")
        return 0
    if args[0] == "test":
        if len(args) < 2:
            sys.stderr.write("error: pyla test requires a directory\n")
            return 2
        return run_tests(args[1], use_vm)
    if args[0] == "-c":
        if len(args) < 2:
            sys.stderr.write("error: -c requires a program string\n")
            return 2
        from . import builtins
        builtins.SCRIPT_ARGS[:] = args[2:]
        return run_source(args[1], "<-c>", use_vm, slang)

    path = args[0]
    from . import builtins
    builtins.SCRIPT_ARGS[:] = args[1:]
    try:
        # utf-8-sig transparently strips a UTF-8 BOM (PowerShell writes one).
        with open(path, "r", encoding="utf-8-sig") as f:
            source = f.read()
    except OSError as e:
        sys.stderr.write(f"error: cannot read {path}: {e}\n")
        return 2
    if path.endswith(".fr"):
        slang = True  # fr fr
    # Imports in the script resolve relative to the script's own directory.
    modules.set_base_dir(os.path.dirname(os.path.abspath(path)))
    return run_source(source, path, use_vm, slang)


if __name__ == "__main__":
    sys.exit(main())
