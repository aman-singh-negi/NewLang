"""
Purpose:
- Stores AST node definitions used by parser and later compiler stages.
- Concrete node classes will be implemented in Prompt 5.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union


class ASTNode:
    """
    Base class for all AST nodes.

    Why this exists:
    A shared base class allows future compiler stages (semantic analysis, IR,
    optimization) to type-check and dispatch uniformly across node variants.
    """


@dataclass
class ProgramNode(ASTNode):
    """
    Root AST node representing a full program.

    Attributes:
        statements: Ordered top-level statements in the source program.
    """

    statements: List[ASTNode] = field(default_factory=list)


@dataclass
class VarDeclNode(ASTNode):
    """
    AST node for variable declaration statements.

    Attributes:
        name: Declared variable identifier.
        initializer: Expression assigned during declaration.
    """

    name: str
    initializer: ASTNode


@dataclass
class BinaryExprNode(ASTNode):
    """
    AST node for binary arithmetic or logical expressions.

    Attributes:
        left: Left expression operand.
        operator: Operator lexeme (e.g., '+', '*', '==').
        right: Right expression operand.
    """

    left: ASTNode
    operator: str
    right: ASTNode


@dataclass
class IfNode(ASTNode):
    """
    AST node for conditional branching.

    Attributes:
        condition: Condition expression evaluated as true/false.
        then_block: Statements executed when condition is true.
        else_block: Optional statements executed when condition is false.
    """

    condition: ASTNode
    then_block: List[ASTNode] = field(default_factory=list)
    else_block: Optional[List[ASTNode]] = None


@dataclass
class LoopNode(ASTNode):
    """
    AST node for loop constructs.

    Attributes:
        condition: Loop continuation condition.
        body: Statements repeated while condition holds.
    """

    condition: ASTNode
    body: List[ASTNode] = field(default_factory=list)


@dataclass
class NumberNode(ASTNode):
    """
    AST leaf node for numeric literals.

    Attributes:
        value: Parsed numeric value (int or float).
    """

    value: Union[int, float]


@dataclass
class IdentifierNode(ASTNode):
    """
    AST leaf node for variable references.

    Attributes:
        name: Referenced identifier name.
    """

    name: str
