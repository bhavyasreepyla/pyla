"""Exception types used across the Pyla pipeline."""


class PylaError(Exception):
    """Base class for all Pyla errors."""


class ParseError(PylaError):
    def __init__(self, message: str, line: int = 0, col: int = 0):
        self.message = message
        self.line = line
        self.col = col
        super().__init__(message)

    def __str__(self):
        where = f" [line {self.line}]" if self.line else ""
        return f"Parse error{where}: {self.message}"


class PylaRuntimeError(PylaError):
    def __init__(self, message: str, line: int = 0):
        self.message = message
        self.line = line
        self.pyla_stack = None  # [(function name, call line), ...] outermost first
        super().__init__(message)

    def __str__(self):
        where = f" [line {self.line}]" if self.line else ""
        return f"Runtime error{where}: {self.message}"
