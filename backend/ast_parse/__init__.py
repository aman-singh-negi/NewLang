"""Recursive-descent parser for `language` (package renamed from `parser` to avoid stdlib name clash)."""

from .parser import Parser, ParserError, parse_tokens

__all__ = ["Parser", "ParserError", "parse_tokens"]
