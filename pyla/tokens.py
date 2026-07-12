"""Token types and the Token record for the Pyla language."""

from dataclasses import dataclass

# Special
ILLEGAL = "ILLEGAL"
EOF = "EOF"

# Identifiers + literals
IDENT = "IDENT"
INT = "INT"
FLOAT = "FLOAT"
STRING = "STRING"
INTERP = "INTERP"   # a string containing ${...} interpolations

# Operators
ASSIGN = "="
PLUS = "+"
MINUS = "-"
BANG = "!"
ASTERISK = "*"
SLASH = "/"
PERCENT = "%"

LT = "<"
GT = ">"
LE = "<="
GE = ">="
EQ = "=="
NOT_EQ = "!="
PIPE = "|>"

# Delimiters
COMMA = ","
SEMICOLON = ";"
COLON = ":"
DOT = "."

LPAREN = "("
RPAREN = ")"
LBRACE = "{"
RBRACE = "}"
LBRACKET = "["
RBRACKET = "]"

# Keywords
FUNCTION = "FUNCTION"
LET = "LET"
TRUE = "TRUE"
FALSE = "FALSE"
IF = "IF"
ELSE = "ELSE"
RETURN = "RETURN"
WHILE = "WHILE"
FOR = "FOR"
BREAK = "BREAK"
CONTINUE = "CONTINUE"
NIL = "NIL"
AND = "AND"
OR = "OR"

KEYWORDS = {
    "fn": FUNCTION,
    "let": LET,
    "true": TRUE,
    "false": FALSE,
    "if": IF,
    "else": ELSE,
    "return": RETURN,
    "while": WHILE,
    "for": FOR,
    "break": BREAK,
    "continue": CONTINUE,
    "nil": NIL,
    "and": AND,
    "or": OR,
}


def lookup_ident(ident: str) -> str:
    """Return the keyword token type for an identifier, or IDENT."""
    return KEYWORDS.get(ident, IDENT)


# Brainrot mode: the Gen Z dialect of Pyla. Same language, different drip.
# Only active when the lexer is created with slang=True (--brainrot, .fr files),
# so regular programs can still use these words as identifiers.
SLANG_KEYWORDS = {
    "fr": LET,            # fr x = 5;              (for real, x is 5)
    "cook": FUNCTION,     # fr f = cook(x) {...}   (let him cook)
    "yeet": RETURN,       # yeet x;
    "vibecheck": IF,      # vibecheck (x > 0) {...}
    "nah": ELSE,          # ... nah {...}
    "grind": WHILE,       # grind (nocap) {...}
    "farm": FOR,          # farm (fr i = 0; ...) {...}
    "dip": BREAK,         # dip;                   (leave the loop)
    "skip": CONTINUE,     # skip;
    "nocap": TRUE,        # no cap = the truth
    "cap": FALSE,         # cap = a lie
    "ghosted": NIL,       # ghosted = nothing there
}

# Identifier aliases: rewritten to the canonical builtin name while lexing.
SLANG_IDENTS = {
    "yap": "print",       # yap("hello")
    "spill": "input",     # spill the tea
    "sheesh": "assert",   # sheesh(x > 0, "down bad")
}


@dataclass
class Token:
    type: str
    literal: str
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.type!r}, {self.literal!r}, {self.line}:{self.col})"
