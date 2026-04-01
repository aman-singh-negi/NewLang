"""
Purpose:
- Defines token data structures and token type declarations.
- Token model details will be implemented in Prompt 3.
"""

from dataclasses import dataclass


# Token type constants are grouped here so every compiler stage uses one
# canonical vocabulary and avoids scattered string literals.
TOKEN_KEYWORD = "KEYWORD"
TOKEN_IDENTIFIER = "IDENTIFIER"
TOKEN_NUMBER = "NUMBER"
TOKEN_STRING = "STRING"
TOKEN_OPERATOR = "OPERATOR"
TOKEN_SYMBOL = "SYMBOL"
TOKEN_EOF = "EOF"


# Reserved words are recognized as KEYWORD tokens instead of generic
# identifiers because grammar rules treat them as language control words.
KEYWORDS = {
    "var",
    "when",
    "otherwise",
    "loop",
    "func",
    "show",
    "return",
}


@dataclass(frozen=True)
class Token:
    """
    Represents one lexical unit produced by the lexer.

    Attributes:
        token_type: Category of token (e.g., IDENTIFIER, NUMBER).
        value: Raw lexeme text as found in source.
        line: 1-based line number to support readable diagnostics.
        position: 1-based column position on the line for precise error pointers.
    """

    token_type: str
    value: str
    line: int
    position: int
