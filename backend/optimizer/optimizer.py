"""
Purpose:
- Applies IR optimization passes to improve generated code.
- Constant folding and dead code logic will be added in Prompt 8.
"""

import re
from typing import List, Set


class IROptimizer:
    """
    Optimizes 3-address IR with simple, explainable passes.

    Implemented passes:
    1) Constant folding
       - Example: `t1 = 2 + 3` becomes `t1 = 5`
       - Why: removes runtime arithmetic when result is known at compile time.

    2) Dead code removal
       - Example: if `t9 = a + b` is never used later, remove it.
       - Why: cuts unnecessary instructions, reducing VM work.
    """

    ASSIGN_PATTERN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$")
    BINARY_CONST_PATTERN = re.compile(
        r"^(-?\d+(?:\.\d+)?)\s*(\+|-|\*|/|==|!=|<=|>=|<|>)\s*(-?\d+(?:\.\d+)?)$"
    )
    IDENTIFIER_PATTERN = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")

    def optimize(self, instructions: List[str]) -> List[str]:
        """
        Run optimization pipeline in stable order.
        """
        folded = self._constant_fold(instructions)
        cleaned = self._remove_dead_code(folded)
        return cleaned

    def _constant_fold(self, instructions: List[str]) -> List[str]:
        folded: List[str] = []
        for line in instructions:
            match = self.ASSIGN_PATTERN.match(line.strip())
            if not match:
                folded.append(line)
                continue

            target, expr = match.group(1), match.group(2).strip()
            bin_match = self.BINARY_CONST_PATTERN.match(expr)
            if not bin_match:
                folded.append(line)
                continue

            left_raw, operator, right_raw = bin_match.groups()
            left = float(left_raw) if "." in left_raw else int(left_raw)
            right = float(right_raw) if "." in right_raw else int(right_raw)
            result = self._evaluate_const_binary(left, operator, right)

            folded_value = self._format_number(result)
            folded.append(f"{target} = {folded_value}")
        return folded

    def _remove_dead_code(self, instructions: List[str]) -> List[str]:
        """
        Remove assignments whose targets are never read afterward.

        We keep:
        - non-assignment control-flow lines (`IF_FALSE`, `GOTO`, `LABEL`)
        - assignments to non-temp names (program variables)
        - temp assignments that are later used
        """
        live: Set[str] = set()
        output_reversed: List[str] = []

        for line in reversed(instructions):
            stripped = line.strip()
            match = self.ASSIGN_PATTERN.match(stripped)
            if not match:
                live.update(self._extract_identifiers(stripped))
                output_reversed.append(line)
                continue

            target, expr = match.group(1), match.group(2).strip()
            used_names = self._extract_identifiers(expr)
            is_temp = target.startswith("t")

            if (not is_temp) or (target in live):
                output_reversed.append(line)
                live.discard(target)
                live.update(used_names)
            else:
                # Dead temporary assignment removed.
                continue

        return list(reversed(output_reversed))

    def _extract_identifiers(self, text: str) -> Set[str]:
        names = set(self.IDENTIFIER_PATTERN.findall(text))
        # Control-flow keywords are not variables.
        return {
            n
            for n in names
            if n not in {
                "IF_FALSE",
                "GOTO",
                "LABEL",
                "JUMP",
                "CALL",
                "RETURN",
                "RET",
                "DROP",
                "PRINT_STACK",
            }
        }

    def _evaluate_const_binary(self, left: float, operator: str, right: float) -> float:
        if operator == "+":
            return left + right
        if operator == "-":
            return left - right
        if operator == "*":
            return left * right
        if operator == "/":
            return left / right
        if operator == "==":
            return float(left == right)
        if operator == "!=":
            return float(left != right)
        if operator == "<":
            return float(left < right)
        if operator == "<=":
            return float(left <= right)
        if operator == ">":
            return float(left > right)
        if operator == ">=":
            return float(left >= right)
        raise ValueError(f"Unsupported operator for constant folding: {operator}")

    def _format_number(self, value: float) -> str:
        # Keep IR tidy: represent integer-valued results without `.0`.
        if float(value).is_integer():
            return str(int(value))
        return str(value)


def optimize_ir(instructions: List[str]) -> List[str]:
    """Convenience wrapper to optimize IR instruction list."""
    return IROptimizer().optimize(instructions)
