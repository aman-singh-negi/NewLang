"""
Purpose:
- Implements lexical analysis (source code -> tokens).
- Detailed regex/tokenization logic will be added in Prompt 3.
"""

import re
from typing import List

from lexer.tokens import (
    KEYWORDS,
    TOKEN_EOF,
    TOKEN_IDENTIFIER,
    TOKEN_KEYWORD,
    TOKEN_NUMBER,
    TOKEN_OPERATOR,
    TOKEN_STRING,
    TOKEN_SYMBOL,
    Token,
)


class LexerError(Exception):
    """Raised when the lexer finds an invalid character sequence."""


# Token specification order matters:
# - NUMBER first to capture float/int lexemes as a whole.
# - IDENTIFIER next, then we remap reserved words to KEYWORD tokens.
# - OPERATOR and SYMBOL provide grammar punctuation and arithmetic/logic marks.
TOKEN_SPECIFICATION = [
    (TOKEN_STRING, r'"([^"\\]|\\.)*"'),
    (TOKEN_NUMBER, r"\d+\.\d+|\d+"),
    (TOKEN_IDENTIFIER, r"[A-Za-z_][A-Za-z0-9_]*"),
    (TOKEN_OPERATOR, r"==|!=|<=|>=|\+\+|\+|-|\*|/|=|<|>"),
    (TOKEN_SYMBOL, r"[(){};,]"),
    ("NEWLINE", r"\n"),
    ("WHITESPACE", r"[ \t\r]+"),
    ("MISMATCH", r"."),
]


# The combined regex uses named groups so each match reports which token rule
# won. This makes the tokenization loop simple and explicit.
MASTER_PATTERN = re.compile(
    "|".join(f"(?P<{token_type}>{pattern})" for token_type, pattern in TOKEN_SPECIFICATION)
)


def _unescape_string(quoted: str) -> str:
    """Decode escape sequences inside a double-quoted string literal."""
    if len(quoted) < 2 or quoted[0] != '"' or quoted[-1] != '"':
        return quoted
    inner = quoted[1:-1]
    out: List[str] = []
    i = 0
    while i < len(inner):
        if inner[i] == "\\" and i + 1 < len(inner):
            n = inner[i + 1]
            if n == "n":
                out.append("\n")
            elif n == "t":
                out.append("\t")
            elif n == "\\":
                out.append("\\")
            elif n == '"':
                out.append('"')
            else:
                out.append(n)
            i += 2
            continue
        out.append(inner[i])
        i += 1
    return "".join(out)


def tokenize(source_code: str) -> List[Token]:
    """
    Convert source code into a list of Token objects.

    Token flow:
    1. Scan left-to-right using the compiled master regex.
    2. Skip layout-only lexemes (whitespace/newlines) while tracking location.
    3. Build Token objects for language-significant lexemes.
    4. Promote identifiers that match reserved words to KEYWORD type.
    5. Raise LexerError immediately for invalid characters.
    6. Append EOF token so parser has a deterministic stream terminator.
    """

    tokens: List[Token] = []
    line = 1
    line_start_index = 0

    for match in MASTER_PATTERN.finditer(source_code):
        token_type = match.lastgroup
        value = match.group()
        position = (match.start() - line_start_index) + 1

        if token_type == "NEWLINE":
            line += 1
            line_start_index = match.end()
            continue

        if token_type == "WHITESPACE":
            continue

        if token_type == "MISMATCH":
            raise LexerError(
                f"Invalid character '{value}' at line {line}, position {position}."
            )

        if token_type == TOKEN_IDENTIFIER and value in KEYWORDS:
            token_type = TOKEN_KEYWORD

        lexeme_value = _unescape_string(value) if token_type == TOKEN_STRING else value

        tokens.append(
            Token(
                token_type=token_type,
                value=lexeme_value,
                line=line,
                position=position,
            )
        )

    # EOF is useful for parser loops because it avoids repeated end checks.
    tokens.append(Token(token_type=TOKEN_EOF, value="", line=line, position=1))
    return tokens
