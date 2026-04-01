"""
Purpose:
- Converts AST into an intermediate representation (IR).
- 3-address code generation will be added in Prompt 7.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class IRGenerator:
    """
    Generates 3-address-code style IR from parser AST dictionaries.

    Program layout:
      JUMP main_N
      LABEL func_foo ... RETURN
      LABEL main_N
      ... top-level statements ...
    """

    instructions: List[str] = field(default_factory=list)
    temp_counter: int = 0
    label_counter: int = 0

    def generate(self, ast: Dict[str, Any]) -> List[str]:
        """Generate IR instruction list from Program AST."""
        if ast.get("node_type") != "Program":
            raise ValueError("IR generation expects a Program root node.")

        statements = ast.get("statements", [])
        funcs = [s for s in statements if s.get("node_type") == "FuncDecl"]
        main_stmts = [s for s in statements if s.get("node_type") != "FuncDecl"]

        entry = self._new_label("main")
        self.instructions.append(f"JUMP {entry}")

        for fn in funcs:
            self._emit_func_decl(fn)

        self.instructions.append(f"LABEL {entry}")
        for statement in main_stmts:
            self._emit_statement(statement)

        return self.instructions

    def _emit_func_decl(self, node: Dict[str, Any]) -> None:
        name = node.get("name")
        lbl = f"func_{name}"
        self.instructions.append(f"LABEL {lbl}")
        body = node.get("body", [])
        for statement in body:
            self._emit_statement(statement)
        if not body or body[-1].get("node_type") != "Return":
            self.instructions.append("RETURN")

    def _emit_statement(self, node: Dict[str, Any]) -> None:
        node_type = node.get("node_type")
        if node_type == "VarDecl":
            rhs_value = self._emit_expression(node.get("initializer"))
            self.instructions.append(f"{node.get('name')} = {rhs_value}")
            return
        if node_type == "Assign":
            rhs_value = self._emit_expression(node.get("expr"))
            self.instructions.append(f"{node.get('name')} = {rhs_value}")
            return
        if node_type == "If":
            self._emit_if(node)
            return
        if node_type == "Loop":
            self._emit_loop(node)
            return
        if node_type == "Show":
            self._emit_show(node)
            return
        if node_type == "Return":
            ref = self._emit_expression(node.get("expr", {}))
            self.instructions.append(f"RET {ref}")
            return
        if node_type == "PostIncrement":
            name = node.get("name")
            temp = self._new_temp()
            self.instructions.append(f"{temp} = {name} + 1")
            self.instructions.append(f"{name} = {temp}")
            return
        if node_type == "ExprStmt":
            self._emit_expr_stmt(node)
            return
        if node_type == "FuncDecl":
            raise ValueError("Nested function declarations are not supported.")
        raise ValueError(f"Unsupported statement node in IR generation: {node_type}")

    def _emit_loop(self, node: Dict[str, Any]) -> None:
        start_l = self._new_label("loop")
        end_l = self._new_label("loop")
        self.instructions.append(f"LABEL {start_l}")
        condition_ref = self._emit_condition(node.get("condition", {}))
        self.instructions.append(f"IF_FALSE {condition_ref} GOTO {end_l}")
        for statement in node.get("body", []):
            self._emit_statement(statement)
        self.instructions.append(f"GOTO {start_l}")
        self.instructions.append(f"LABEL {end_l}")

    def _emit_show(self, node: Dict[str, Any]) -> None:
        expr = node.get("expr", {})
        if expr.get("node_type") == "Call":
            self.instructions.append(f"CALL func_{expr.get('name')}")
            self.instructions.append("PRINT_STACK")
            return
        ref = self._emit_expression(expr)
        self.instructions.append(f"PRINT {ref}")

    def _emit_expr_stmt(self, node: Dict[str, Any]) -> None:
        expr = node.get("expr", {})
        if expr.get("node_type") == "Call":
            self.instructions.append(f"CALL func_{expr.get('name')}")
            self.instructions.append("DROP")
            return
        raise ValueError("ExprStmt must be a call.")

    def _emit_if(self, node: Dict[str, Any]) -> None:
        condition_ref = self._emit_condition(node.get("condition", {}))
        else_label = self._new_label("L_else")
        end_label = self._new_label("L_end")

        self.instructions.append(f"IF_FALSE {condition_ref} GOTO {else_label}")
        for statement in node.get("then_block", []):
            self._emit_statement(statement)
        self.instructions.append(f"GOTO {end_label}")
        self.instructions.append(f"LABEL {else_label}")

        else_block = node.get("else_block")
        if else_block:
            for statement in else_block:
                self._emit_statement(statement)

        self.instructions.append(f"LABEL {end_label}")

    def _emit_condition(self, node: Dict[str, Any]) -> str:
        if node.get("node_type") != "Condition":
            raise ValueError("Expected Condition node for control-flow emission.")
        left = self._emit_expression(node.get("left"))
        right = self._emit_expression(node.get("right"))
        temp = self._new_temp()
        operator = node.get("operator")
        self.instructions.append(f"{temp} = {left} {operator} {right}")
        return temp

    def _emit_expression(self, node: Dict[str, Any]) -> str:
        node_type = node.get("node_type")

        if node_type == "Number":
            return str(node.get("value"))
        if node_type == "StringLiteral":
            return json.dumps(node.get("value"))
        if node_type == "Identifier":
            return str(node.get("name"))
        if node_type == "Call":
            raise ValueError("Nested calls in expressions are not supported in IR.")
        if node_type == "BinaryExpr":
            left = self._emit_expression(node.get("left"))
            right = self._emit_expression(node.get("right"))
            temp = self._new_temp()
            operator = node.get("operator")
            self.instructions.append(f"{temp} = {left} {operator} {right}")
            return temp

        raise ValueError(f"Unsupported expression node in IR generation: {node_type}")

    def _new_temp(self) -> str:
        self.temp_counter += 1
        return f"t{self.temp_counter}"

    def _new_label(self, prefix: str) -> str:
        self.label_counter += 1
        return f"{prefix}_{self.label_counter}"


def generate_ir(ast: Dict[str, Any]) -> List[str]:
    """Convenience wrapper to generate IR from an AST."""
    return IRGenerator().generate(ast)
