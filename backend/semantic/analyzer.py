"""
Purpose:
- Performs semantic checks over the AST.
- Type checks and validation rules will be added in Prompt 6.
"""

from typing import Any, Dict, List

from semantic.symbol_table import SymbolTable


class SemanticError(Exception):
    """Raised for semantic violations discovered after parsing."""


class SemanticAnalyzer:
    """
    Semantic analyzer for parser-produced AST dictionaries.

    Responsibilities:
    - Track declarations/usages through nested scopes.
    - Enforce basic type consistency for expressions and conditions.
    - Collect human-readable errors to help users debug source code quickly.
    """

    def __init__(self) -> None:
        self.symbol_table = SymbolTable()
        self.errors: List[str] = []

    def analyze(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze AST and return structured semantic result.
        """
        if ast.get("node_type") != "Program":
            self.errors.append("Root node must be 'Program'.")
            return self._result()

        statements = ast.get("statements", [])

        # Pass 1: register every function name in global scope (for forward calls).
        for statement in statements:
            if statement.get("node_type") == "FuncDecl":
                name = statement.get("name")
                if not self.symbol_table.declare(name, "func"):
                    self.errors.append(
                        f"Semantic error: Function '{name}' is already declared."
                    )

        # Pass 2: analyze bodies and other statements.
        for statement in statements:
            self._analyze_statement(statement)

        return self._result()

    def _analyze_statement(self, node: Dict[str, Any]) -> None:
        node_type = node.get("node_type")
        if node_type == "VarDecl":
            self._analyze_var_decl(node)
            return
        if node_type == "Assign":
            self._analyze_assign(node)
            return
        if node_type == "If":
            self._analyze_if(node)
            return
        if node_type == "Loop":
            self._analyze_loop(node)
            return
        if node_type == "FuncDecl":
            self._analyze_func_decl(node)
            return
        if node_type == "Show":
            self._analyze_show(node)
            return
        if node_type == "Return":
            self._analyze_return(node)
            return
        if node_type == "PostIncrement":
            self._analyze_post_increment(node)
            return
        if node_type == "ExprStmt":
            self._analyze_expr_stmt(node)
            return
        self.errors.append(f"Unsupported statement node type: {node_type}.")

    def _analyze_loop(self, node: Dict[str, Any]) -> None:
        self._analyze_condition(node.get("condition", {}))
        self.symbol_table.enter_scope()
        for statement in node.get("body", []):
            self._analyze_statement(statement)
        self.symbol_table.exit_scope()

    def _analyze_func_decl(self, node: Dict[str, Any]) -> None:
        # Name registered in pass 1; analyze body in its own scope.
        self.symbol_table.enter_scope()
        for statement in node.get("body", []):
            self._analyze_statement(statement)
        self.symbol_table.exit_scope()

    def _analyze_show(self, node: Dict[str, Any]) -> None:
        self._infer_expression_type(node.get("expr"))

    def _analyze_return(self, node: Dict[str, Any]) -> None:
        self._infer_expression_type(node.get("expr"))

    def _analyze_post_increment(self, node: Dict[str, Any]) -> None:
        name = node.get("name")
        sym = self.symbol_table.resolve(name)
        if sym is None:
            self.errors.append(
                f"Semantic error: Variable '{name}' is used before declaration."
            )
            return
        if sym.symbol_type == "func":
            self.errors.append(f"Semantic error: Cannot increment function '{name}'.")
            return
        if sym.symbol_type == "str":
            self.errors.append("Semantic error: Cannot apply ++ to a string variable.")

    def _analyze_expr_stmt(self, node: Dict[str, Any]) -> None:
        expr = node.get("expr", {})
        if expr.get("node_type") != "Call":
            self.errors.append("Expression statement must be a function call.")
            return
        self._check_call_target(expr.get("name"))

    def _check_call_target(self, name: str) -> None:
        sym = self.symbol_table.resolve(name)
        if sym is None:
            self.errors.append(f"Semantic error: Call to unknown function '{name}'.")
            return
        if sym.symbol_type != "func":
            self.errors.append(f"Semantic error: '{name}' is not a function.")

    def _analyze_assign(self, node: Dict[str, Any]) -> None:
        name = node.get("name")
        sym = self.symbol_table.resolve(name)
        if sym is None:
            self.errors.append(
                f"Semantic error: Unknown variable '{name}' in assignment."
            )
            return
        if sym.symbol_type == "func":
            self.errors.append(f"Semantic error: Cannot assign to function '{name}'.")
            return
        rhs_type = self._infer_expression_type(node.get("expr"))
        if rhs_type == "unknown" or rhs_type == "void":
            self.errors.append(f"Invalid right-hand side in assignment to '{name}'.")
            return
        if rhs_type != sym.symbol_type:
            self.errors.append(
                f"Type mismatch in assignment to '{name}': "
                f"expected '{sym.symbol_type}', got '{rhs_type}'."
            )

    def _analyze_var_decl(self, node: Dict[str, Any]) -> None:
        name = node.get("name")
        initializer = node.get("initializer")
        initializer_type = self._infer_expression_type(initializer)

        if initializer_type == "unknown":
            self.errors.append(f"Cannot infer type for initializer of '{name}'.")
            return

        if initializer_type == "void":
            self.errors.append(f"Cannot assign from void call to '{name}'.")
            return

        if not self.symbol_table.declare(name, initializer_type):
            self.errors.append(
                f"Semantic error: Variable '{name}' is already declared in this scope."
            )

    def _analyze_if(self, node: Dict[str, Any]) -> None:
        condition = node.get("condition", {})
        self._analyze_condition(condition)

        # Scope management for control flow blocks ensures variables declared
        # inside blocks do not leak into outer scopes.
        self.symbol_table.enter_scope()
        for statement in node.get("then_block", []):
            self._analyze_statement(statement)
        self.symbol_table.exit_scope()

        else_block = node.get("else_block")
        if else_block is not None:
            self.symbol_table.enter_scope()
            for statement in else_block:
                self._analyze_statement(statement)
            self.symbol_table.exit_scope()

    def _analyze_condition(self, node: Dict[str, Any]) -> None:
        if node.get("node_type") != "Condition":
            self.errors.append("If/loop requires a Condition node.")
            return

        left_type = self._infer_expression_type(node.get("left"))
        right_type = self._infer_expression_type(node.get("right"))
        operator = node.get("operator")

        if left_type == "unknown" or right_type == "unknown":
            self.errors.append(
                f"Condition uses unresolved expression(s) with operator '{operator}'."
            )
            return

        if left_type == "void" or right_type == "void":
            self.errors.append("Condition cannot use void call results.")
            return

        if left_type == "str" or right_type == "str":
            self.errors.append("Condition cannot compare string values.")
            return

        if left_type != right_type:
            self.errors.append(
                "Type mismatch in condition: "
                f"left is '{left_type}', right is '{right_type}'."
            )

    def _infer_expression_type(self, node: Dict[str, Any]) -> str:
        node_type = node.get("node_type")

        if node_type == "Number":
            value = node.get("value")
            if isinstance(value, int):
                return "int"
            if isinstance(value, float):
                return "float"
            return "unknown"

        if node_type == "StringLiteral":
            return "str"

        if node_type == "Identifier":
            name = node.get("name")
            symbol = self.symbol_table.resolve(name)
            if symbol is None:
                self.errors.append(
                    f"Semantic error: Variable '{name}' is used before declaration."
                )
                return "unknown"
            if symbol.symbol_type == "func":
                self.errors.append(
                    f"Semantic error: '{name}' is a function; use {name}() to call."
                )
                return "unknown"
            return symbol.symbol_type

        if node_type == "Call":
            self._check_call_target(node.get("name"))
            return "void"

        if node_type == "BinaryExpr":
            left_type = self._infer_expression_type(node.get("left"))
            right_type = self._infer_expression_type(node.get("right"))
            operator = node.get("operator")

            if left_type == "void" or right_type == "void":
                self.errors.append(
                    f"Cannot use void call result in arithmetic ('{operator}')."
                )
                return "unknown"

            if left_type == "str" or right_type == "str":
                self.errors.append(
                    f"Cannot use strings in arithmetic ('{operator}')."
                )
                return "unknown"

            if left_type == "unknown" or right_type == "unknown":
                return "unknown"

            if left_type != right_type:
                self.errors.append(
                    "Type mismatch in expression: "
                    f"left is '{left_type}', right is '{right_type}' for '{operator}'."
                )
                return "unknown"

            return left_type

        self.errors.append(f"Unsupported expression node type: {node_type}.")
        return "unknown"

    def _result(self) -> Dict[str, Any]:
        return {
            "success": len(self.errors) == 0,
            "errors": self.errors,
        }


def analyze_ast(ast: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for semantic analysis execution."""
    return SemanticAnalyzer().analyze(ast)
