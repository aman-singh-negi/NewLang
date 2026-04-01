"""
Purpose:
- Maintains scoped symbol information for semantic analysis.
- Scope and type metadata logic will be added in Prompt 6.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class SymbolInfo:
    """
    Metadata associated with one declared symbol.

    Attributes:
        name: Symbol identifier text.
        symbol_type: Static type inferred/declared for this symbol.
    """

    name: str
    symbol_type: str


class SymbolTable:
    """
    Scoped symbol table with lexical scope stack.

    Why this design:
    A stack of dictionaries mirrors nested blocks. Entering a block pushes
    a new scope, leaving a block pops it, and lookups walk outward so inner
    scopes can shadow outer declarations safely.
    """

    def __init__(self) -> None:
        self._scopes: List[Dict[str, SymbolInfo]] = [{}]

    def enter_scope(self) -> None:
        """Start a new nested scope."""
        self._scopes.append({})

    def exit_scope(self) -> None:
        """End current scope; global scope is never removed."""
        if len(self._scopes) == 1:
            return
        self._scopes.pop()

    def declare(self, name: str, symbol_type: str) -> bool:
        """
        Declare symbol in current scope.

        Returns:
            True if declaration succeeds, False if name already exists in the
            current scope (redeclaration error scenario).
        """
        current_scope = self._scopes[-1]
        if name in current_scope:
            return False
        current_scope[name] = SymbolInfo(name=name, symbol_type=symbol_type)
        return True

    def resolve(self, name: str) -> Optional[SymbolInfo]:
        """
        Resolve symbol by searching from innermost to outermost scope.
        """
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None
