"""
Purpose:
- Converts optimized IR into executable bytecode/instructions.
- Instruction mapping logic will be added in Prompt 9.
"""

import json
import re
from typing import List


class CodegenError(Exception):
    """Raised when an IR instruction cannot be mapped to bytecode."""


class BytecodeGenerator:
    """
    Convert 3-address IR lines into stack-machine friendly bytecode.

    Instruction mapping strategy:
    - Assignment with constant
      IR:  `x = 10`
      BC:  `LOAD_CONST 10`, `STORE x`
    - Assignment with variable
      IR:  `x = y`
      BC:  `LOAD_VAR y`, `STORE x`
    - Binary assignment
      IR:  `t1 = a + b`
      BC:  `LOAD_VAR a`, `LOAD_VAR b`, `ADD`, `STORE t1`
    - Control flow
      IR:  `IF_FALSE t1 GOTO L1` -> `LOAD_VAR t1`, `JUMP_IF_FALSE L1`
      IR:  `GOTO L2` -> `JUMP L2`
      IR:  `LABEL L2` -> `LABEL L2`
    """

    ASSIGN_PATTERN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$")
    BINARY_EXPR_PATTERN = re.compile(
        r"^([A-Za-z_][A-Za-z0-9_]*|-?\d+(?:\.\d+)?)\s*(\+|-|\*|/|==|!=|<=|>=|<|>)\s*([A-Za-z_][A-Za-z0-9_]*|-?\d+(?:\.\d+)?)$"
    )
    IF_FALSE_PATTERN = re.compile(r"^IF_FALSE\s+([A-Za-z_][A-Za-z0-9_]*)\s+GOTO\s+([A-Za-z_][A-Za-z0-9_]*)$")
    GOTO_PATTERN = re.compile(r"^(?:GOTO|JUMP)\s+([A-Za-z_][A-Za-z0-9_]*)$")
    LABEL_PATTERN = re.compile(r"^LABEL\s+([A-Za-z_][A-Za-z0-9_]*)$")
    CALL_PATTERN = re.compile(r"^CALL\s+([A-Za-z_][A-Za-z0-9_]*)$")
    PRINT_REF_PATTERN = re.compile(r"^PRINT\s+(.+)$")

    OPERATOR_TO_OPCODE = {
        "+": "ADD",
        "-": "SUB",
        "*": "MUL",
        "/": "DIV",
        "==": "CMP_EQ",
        "!=": "CMP_NE",
        "<": "CMP_LT",
        "<=": "CMP_LE",
        ">": "CMP_GT",
        ">=": "CMP_GE",
    }

    def generate(self, ir_instructions: List[str]) -> List[str]:
        """Generate bytecode list from IR instruction list."""
        bytecode: List[str] = []
        for line in ir_instructions:
            stripped = line.strip()
            if not stripped:
                continue
            bytecode.extend(self._map_line(stripped))
        return bytecode

    def _map_line(self, line: str) -> List[str]:
        stripped = line.strip()
        if stripped == "RETURN":
            return ["RETURN"]

        ret_match = re.compile(r"^RET\s+(.+)$").match(stripped)
        if ret_match:
            ref = ret_match.group(1).strip()
            return [self._load_operand(ref), "RETURN"]

        if stripped == "DROP":
            return ["DROP"]
        if stripped == "PRINT_STACK":
            return ["PRINT"]

        call_match = self.CALL_PATTERN.match(stripped)
        if call_match:
            return [f"CALL {call_match.group(1)}"]

        print_ref = self.PRINT_REF_PATTERN.match(stripped)
        if print_ref:
            ref = print_ref.group(1).strip()
            return [self._load_operand(ref), "PRINT"]

        if_match = self.IF_FALSE_PATTERN.match(line)
        if if_match:
            condition_var, label = if_match.groups()
            return [f"LOAD_VAR {condition_var}", f"JUMP_IF_FALSE {label}"]

        goto_match = self.GOTO_PATTERN.match(line)
        if goto_match:
            return [f"JUMP {goto_match.group(1)}"]

        label_match = self.LABEL_PATTERN.match(line)
        if label_match:
            return [f"LABEL {label_match.group(1)}"]

        assign_match = self.ASSIGN_PATTERN.match(line)
        if assign_match:
            target, expr = assign_match.groups()
            return self._map_assignment(target, expr.strip())

        raise CodegenError(f"Unsupported IR line for code generation: '{line}'")

    def _map_assignment(self, target: str, expr: str) -> List[str]:
        binary_match = self.BINARY_EXPR_PATTERN.match(expr)
        if binary_match:
            left, operator, right = binary_match.groups()
            opcode = self.OPERATOR_TO_OPCODE[operator]
            return [
                self._load_operand(left),
                self._load_operand(right),
                opcode,
                f"STORE {target}",
            ]

        # Simple assignment: x = y or x = 123
        return [self._load_operand(expr), f"STORE {target}"]

    def _load_operand(self, operand: str) -> str:
        op = operand.strip()
        if len(op) >= 2 and op[0] == '"' and op[-1] == '"':
            try:
                json.loads(op)
            except json.JSONDecodeError:
                pass
            else:
                return f"LOAD_CONST {op}"
        if self._is_number(op):
            return f"LOAD_CONST {op}"
        return f"LOAD_VAR {op}"

    def _is_number(self, text: str) -> bool:
        try:
            float(text)
            return True
        except ValueError:
            return False


def generate_bytecode(ir_instructions: List[str]) -> List[str]:
    """Convenience wrapper for IR -> bytecode conversion."""
    return BytecodeGenerator().generate(ir_instructions)
