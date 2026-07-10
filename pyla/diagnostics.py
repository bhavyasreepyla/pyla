"""Human-friendly error reporting and the pipeline flight recorder.

Walter Bright's rule: error messages are the quality of implementation.
Instead of a bare message, the CLI shows the offending source line, a caret
at the column (when known), and the Pyla call stack for runtime errors.

The flight recorder (`pyla --trace`) prints the value leaving every |>
pipeline stage of an UNMODIFIED program to stderr. Both engines honour it.
"""

import sys

# Toggled by the CLI's --trace flag.
TRACE_PIPES = False


def trace_pipe(line, stage, value):
    """Report one pipeline stage: the value that just flowed out of it."""
    text = value.inspect()
    if len(text) > 72:
        text = text[:69] + "..."
    sys.stderr.write(f"|> line {line:>3}: {stage}  =>  {text}\n")


def format_error(e, source, filename="<input>"):
    parts = [f"{filename}: {e}"]
    lines = source.splitlines()
    line_no = getattr(e, "line", 0)
    if 1 <= line_no <= len(lines):
        text = lines[line_no - 1]
        # Trim very long lines around the error column.
        col = getattr(e, "col", 0) or 0
        prefix = f"  {line_no:>4} | "
        parts.append(prefix + text)
        if 1 <= col <= len(text) + 1:
            parts.append(" " * (len(prefix) + col - 1) + "^")
    stack = getattr(e, "pyla_stack", None)
    if stack:
        parts.append("  Pyla call stack (outermost first):")
        for name, call_line in stack:
            where = f" (called at line {call_line})" if call_line else ""
            parts.append(f"    in {name}{where}")
    return "\n".join(parts)
