"""
Purpose:
- Parses token streams into an abstract syntax tree (AST).
- Recursive-descent parser rules will be added in Prompt 4.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from lexer.tokens import (
    TOKEN_EOF,
    TOKEN_IDENTIFIER,
    TOKEN_KEYWORD,
    TOKEN_NUMBER,
    TOKEN_OPERATOR,
    TOKEN_STRING,
    TOKEN_SYMBOL,
    Token,
)


class ParserError(Exception):
    """Raised when token stream does not satisfy the grammar."""


@dataclass
class Parser:
    """
    Recursive descent parser for a small language subset.

    Grammar:
      program        -> statement* EOF
      statement      -> var_declaration | when_statement | loop_statement
                      | func_declaration | show_statement | call_statement
      var_declaration-> 'var' IDENTIFIER '=' expression
      when_statement -> 'when' condition block ('otherwise' block)?
      loop_statement -> 'loop' condition block
      func_declaration -> 'func' IDENTIFIER '(' ')' block
      show_statement -> 'show' expression
      call_statement -> IDENTIFIER '(' ')'   // must be a function call
      block          -> '{' statement* '}'
      condition      -> expression comparator expression
      expression     -> term (('+'|'-') term)*
      term           -> factor (('*'|'/') factor)*
      factor         -> NUMBER | STRING | call_or_identifier | '(' expression ')'
      call_or_identifier -> IDENTIFIER '(' ')' | IDENTIFIER  // lookahead
      return_statement -> 'return' expression
      post_increment   -> IDENTIFIER '++'
    """

    tokens: List[Token]
    current: int = 0

    def parse(self) -> Dict[str, Any]:
        """Parse full token list and return a Program AST node."""
        statements: List[Dict[str, Any]] = []
        while not self._is_at_end():
            statements.append(self._parse_statement(allow_func=True))
            while self._match_symbol(";"):
                pass
        return {"node_type": "Program", "statements": statements}

    def _parse_statement(self, allow_func: bool = True) -> Dict[str, Any]:
        """
        Parse one statement by trying grammar entry points in priority order.
        """
        if self._match_keyword("var"):
            return self._parse_var_declaration()
        if self._match_keyword("when"):
            return self._parse_when_statement()
        if self._match_keyword("loop"):
            return self._parse_loop_statement()
        if self._match_keyword("func"):
            if not allow_func:
                raise self._error(
                    self._peek(), "Nested 'func' declarations are not allowed."
                )
            return self._parse_func_declaration()
        if self._match_keyword("show"):
            return self._parse_show_statement()
        if self._match_keyword("return"):
            return self._parse_return_statement()
        if self._check(TOKEN_IDENTIFIER) and self._peek_next_is_postincrement():
            return self._parse_post_increment_statement()
        if self._check(TOKEN_IDENTIFIER) and self._peek_next_is_assignment():
            return self._parse_assign_statement()
        if self._check(TOKEN_IDENTIFIER) and self._call_statement_follows():
            return self._parse_call_statement()
        raise self._error(
            self._peek(),
            "Expected statement (var, when, loop, func, show, return, assign, ++, or name()).",
        )

    def _call_statement_follows(self) -> bool:
        """True if current IDENTIFIER is followed by '(' — call statement."""
        if self.current + 1 >= len(self.tokens):
            return False
        nxt = self.tokens[self.current + 1]
        return nxt.token_type == TOKEN_SYMBOL and nxt.value == "("

    def _parse_loop_statement(self) -> Dict[str, Any]:
        """Rule: loop_statement -> 'loop' condition block"""
        condition = self._parse_condition()
        body = self._parse_block()
        return {"node_type": "Loop", "condition": condition, "body": body}

    def _parse_func_declaration(self) -> Dict[str, Any]:
        """Rule: func_declaration -> 'func' IDENTIFIER '(' ')' block"""
        name_tok = self._consume(TOKEN_IDENTIFIER, "Expected function name after 'func'.")
        self._consume_symbol("(", "Expected '(' after function name.")
        self._consume_symbol(")", "Expected ')' (use func name() for zero parameters).")
        body = self._parse_block()
        return {"node_type": "FuncDecl", "name": name_tok.value, "body": body}

    def _parse_return_statement(self) -> Dict[str, Any]:
        """Rule: return_statement -> 'return' expression"""
        expr = self._parse_expression()
        return {"node_type": "Return", "expr": expr}

    def _peek_next_is_postincrement(self) -> bool:
        if self.current + 1 >= len(self.tokens):
            return False
        nxt = self.tokens[self.current + 1]
        return nxt.token_type == TOKEN_OPERATOR and nxt.value == "++"

    def _peek_next_is_assignment(self) -> bool:
        if self.current + 1 >= len(self.tokens):
            return False
        nxt = self.tokens[self.current + 1]
        return nxt.token_type == TOKEN_OPERATOR and nxt.value == "="

    def _parse_assign_statement(self) -> Dict[str, Any]:
        """Rule: assign_statement -> IDENTIFIER '=' expression"""
        name_tok = self._consume(TOKEN_IDENTIFIER, "Expected variable name.")
        self._consume_operator("=", "Expected '=' in assignment.")
        expr = self._parse_expression()
        return {"node_type": "Assign", "name": name_tok.value, "expr": expr}

    def _parse_post_increment_statement(self) -> Dict[str, Any]:
        """Rule: post_increment -> IDENTIFIER '++'"""
        name_tok = self._consume(TOKEN_IDENTIFIER, "Expected variable name before '++'.")
        self._consume_operator("++", "Expected '++' after identifier.")
        return {"node_type": "PostIncrement", "name": name_tok.value}

    def _parse_show_statement(self) -> Dict[str, Any]:
        """Rule: show_statement -> 'show' expression"""
        expr = self._parse_expression()
        return {"node_type": "Show", "expr": expr}

    def _parse_call_statement(self) -> Dict[str, Any]:
        """Rule: call_statement -> IDENTIFIER '(' ')'"""
        name_tok = self._consume(TOKEN_IDENTIFIER, "Expected function name.")
        self._consume_symbol("(", "Expected '(' to call function.")
        self._consume_symbol(")", "Expected ')' after call.")
        return {
            "node_type": "ExprStmt",
            "expr": {"node_type": "Call", "name": name_tok.value},
        }

    def _parse_var_declaration(self) -> Dict[str, Any]:
        """
        Rule: var_declaration -> 'var' IDENTIFIER '=' expression
        """
        identifier = self._consume(
            TOKEN_IDENTIFIER, "Expected variable name after 'var'."
        )
        self._consume_operator("=", "Expected '=' after variable name.")
        initializer = self._parse_expression()
        return {
            "node_type": "VarDecl",
            "name": identifier.value,
            "initializer": initializer,
        }

    def _parse_when_statement(self) -> Dict[str, Any]:
        """
        Rule: when_statement -> 'when' condition block ('otherwise' block)?
        """
        condition = self._parse_condition()
        then_block = self._parse_block()
        else_block = None
        if self._match_keyword("otherwise"):
            else_block = self._parse_block()
        return {
            "node_type": "If",
            "condition": condition,
            "then_block": then_block,
            "else_block": else_block,
        }

    def _parse_block(self) -> List[Dict[str, Any]]:
        """Rule: block -> '{' statement* '}'"""
        self._consume_symbol("{", "Expected '{' to start block.")
        statements: List[Dict[str, Any]] = []
        while not self._check_symbol("}") and not self._is_at_end():
            statements.append(self._parse_statement(allow_func=False))
            while self._match_symbol(";"):
                pass
        self._consume_symbol("}", "Expected '}' after block.")
        return statements

    def _parse_condition(self) -> Dict[str, Any]:
        """
        Rule: condition -> expression comparator expression

        Comparator set:
        ==, !=, <, <=, >, >=
        """
        left = self._parse_expression()
        comparator = self._consume(
            TOKEN_OPERATOR, "Expected comparator operator in condition."
        )
        if comparator.value not in {"==", "!=", "<", "<=", ">", ">="}:
            raise self._error(comparator, "Expected a valid comparison operator.")
        right = self._parse_expression()
        return {
            "node_type": "Condition",
            "operator": comparator.value,
            "left": left,
            "right": right,
        }

    def _parse_expression(self) -> Dict[str, Any]:
        """Rule: expression -> term (('+'|'-') term)*"""
        expr = self._parse_term()
        while self._match_operator("+", "-"):
            operator = self._previous().value
            right = self._parse_term()
            expr = {
                "node_type": "BinaryExpr",
                "operator": operator,
                "left": expr,
                "right": right,
            }
        return expr

    def _parse_term(self) -> Dict[str, Any]:
        """Rule: term -> factor (('*'|'/') factor)*"""
        expr = self._parse_factor()
        while self._match_operator("*", "/"):
            operator = self._previous().value
            right = self._parse_factor()
            expr = {
                "node_type": "BinaryExpr",
                "operator": operator,
                "left": expr,
                "right": right,
            }
        return expr

    def _parse_factor(self) -> Dict[str, Any]:
        """Rule: factor -> NUMBER | STRING | call | IDENTIFIER | '(' expression ')'"""
        if self._match_type(TOKEN_NUMBER):
            raw = self._previous().value
            value: Any = float(raw) if "." in raw else int(raw)
            return {"node_type": "Number", "value": value}

        if self._match_type(TOKEN_STRING):
            return {"node_type": "StringLiteral", "value": self._previous().value}

        if self._check(TOKEN_IDENTIFIER) and self._call_statement_follows():
            name_tok = self._consume(TOKEN_IDENTIFIER, "Expected name.")
            self._consume_symbol("(", "Expected '(' in call.")
            self._consume_symbol(")", "Expected ')'.")
            return {"node_type": "Call", "name": name_tok.value}

        if self._match_type(TOKEN_IDENTIFIER):
            return {"node_type": "Identifier", "name": self._previous().value}

        if self._match_symbol("("):
            expr = self._parse_expression()
            self._consume_symbol(")", "Expected ')' after expression.")
            return expr

        raise self._error(self._peek(), "Expected number, string, identifier, call, or '('.")

    def _match_keyword(self, keyword: str) -> bool:
        if self._check(TOKEN_KEYWORD) and self._peek().value == keyword:
            self._advance()
            return True
        return False

    def _match_operator(self, *operators: str) -> bool:
        if self._check(TOKEN_OPERATOR) and self._peek().value in operators:
            self._advance()
            return True
        return False

    def _match_symbol(self, symbol: str) -> bool:
        if self._check(TOKEN_SYMBOL) and self._peek().value == symbol:
            self._advance()
            return True
        return False

    def _match_type(self, token_type: str) -> bool:
        if self._check(token_type):
            self._advance()
            return True
        return False

    def _consume(self, token_type: str, message: str) -> Token:
        if self._check(token_type):
            return self._advance()
        raise self._error(self._peek(), message)

    def _consume_operator(self, operator: str, message: str) -> Token:
        if self._check(TOKEN_OPERATOR) and self._peek().value == operator:
            return self._advance()
        raise self._error(self._peek(), message)

    def _consume_symbol(self, symbol: str, message: str) -> Token:
        if self._check(TOKEN_SYMBOL) and self._peek().value == symbol:
            return self._advance()
        raise self._error(self._peek(), message)

    def _check_symbol(self, symbol: str) -> bool:
        return self._check(TOKEN_SYMBOL) and self._peek().value == symbol

    def _check(self, token_type: str) -> bool:
        if self._is_at_end():
            return token_type == TOKEN_EOF
        return self._peek().token_type == token_type

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.current += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        return self._peek().token_type == TOKEN_EOF

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _previous(self) -> Token:
        return self.tokens[self.current - 1]

    def _error(self, token: Token, message: str) -> ParserError:
        location = f"line {token.line}, position {token.position}"
        found = token.value if token.value else "EOF"
        return ParserError(f"{message} Found '{found}' at {location}.")


def parse_tokens(tokens: List[Token]) -> Dict[str, Any]:
    """Convenience wrapper around Parser(tokens).parse()."""
    return Parser(tokens=tokens).parse()
