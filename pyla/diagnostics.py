"""Human-friendly error reporting.

Walter Bright's rule: error messages are the quality of implementation.
Instead of a bare message, the CLI shows the offending source line, a caret
at the column (when known), and the Pyla call stack for runtime errors.
"""


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
