"""
Safe boolean expression parser and evaluator for MedDSL-Lite.
Implements a Pratt parser for boolean expressions with field references.
"""

import re
from typing import Any, Dict, List, Union
from enum import Enum


class TokenType(Enum):
    # Literals
    TRUE = "true"
    FALSE = "false"
    NULL = "null"
    NUMBER = "number"
    IDENTIFIER = "identifier"
    
    # Operators
    AND = "and"
    OR = "or"
    NOT = "not"
    EQ = "=="
    NE = "!="
    GE = ">="
    GT = ">"
    LE = "<="
    LT = "<"
    
    # Delimiters
    LPAREN = "("
    RPAREN = ")"
    DOT = "."
    
    # Special
    EOF = "eof"


class Token:
    def __init__(self, type_: TokenType, value: Any = None, position: int = 0):
        self.type = type_
        self.value = value
        self.position = position
    
    def __repr__(self):
        return f"Token({self.type.value}, {self.value})"


class ParseError(Exception):
    """Raised when parsing fails."""
    def __init__(self, message: str, position: int = 0):
        super().__init__(message)
        self.position = position


class Parser:
    """Pratt parser for boolean expressions."""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.current = tokens[0] if tokens else Token(TokenType.EOF)
    
    def advance(self):
        """Move to next token."""
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
            self.current = self.tokens[self.pos]
    
    def peek(self) -> Token:
        """Look at next token without advancing."""
        if self.pos < len(self.tokens) - 1:
            return self.tokens[self.pos + 1]
        return Token(TokenType.EOF)
    
    def expect(self, token_type: TokenType) -> Token:
        """Expect and consume a token of given type."""
        if self.current.type == token_type:
            token = self.current
            self.advance()
            return token
        raise ParseError(f"Expected {token_type.value}, got {self.current.type.value}", self.current.position)
    
    def parse_expression(self, precedence: int = 0) -> 'ASTNode':
        """Parse expression with given precedence."""
        left = self.parse_prefix()
        
        while precedence < self.get_precedence(self.current.type):
            left = self.parse_infix(left, self.current.type)
        
        return left
    
    def parse_prefix(self) -> 'ASTNode':
        """Parse prefix expressions."""
        token = self.current
        
        if token.type == TokenType.TRUE:
            self.advance()
            return BooleanNode(True)
        elif token.type == TokenType.FALSE:
            self.advance()
            return BooleanNode(False)
        elif token.type == TokenType.NULL:
            self.advance()
            return NullNode()
        elif token.type == TokenType.NUMBER:
            self.advance()
            return NumberNode(token.value)
        elif token.type == TokenType.IDENTIFIER:
            self.advance()
            return FieldNode(token.value)
        elif token.type == TokenType.NOT:
            self.advance()
            expr = self.parse_expression(self.get_precedence(TokenType.NOT))
            return NotNode(expr)
        elif token.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expression(0)
            self.expect(TokenType.RPAREN)
            return expr
        else:
            raise ParseError(f"Unexpected token: {token.type.value}", token.position)
    
    def parse_infix(self, left: 'ASTNode', token_type: TokenType) -> 'ASTNode':
        """Parse infix expressions."""
        if token_type in [TokenType.EQ, TokenType.NE, TokenType.GE, TokenType.GT, TokenType.LE, TokenType.LT]:
            self.advance()
            right = self.parse_expression(self.get_precedence(token_type))
            return ComparisonNode(left, token_type, right)
        elif token_type == TokenType.AND:
            self.advance()
            right = self.parse_expression(self.get_precedence(TokenType.AND))
            return AndNode(left, right)
        elif token_type == TokenType.OR:
            self.advance()
            right = self.parse_expression(self.get_precedence(TokenType.OR))
            return OrNode(left, right)
        else:
            raise ParseError(f"Unexpected infix operator: {token_type.value}", self.current.position)
    
    @staticmethod
    def get_precedence(token_type: TokenType) -> int:
        """Get operator precedence."""
        precedences = {
            TokenType.OR: 1,
            TokenType.AND: 2,
            TokenType.EQ: 3,
            TokenType.NE: 3,
            TokenType.GE: 3,
            TokenType.GT: 3,
            TokenType.LE: 3,
            TokenType.LT: 3,
            TokenType.NOT: 4,
        }
        return precedences.get(token_type, 0)


class ASTNode:
    """Base AST node."""
    def eval(self, case: Dict[str, Any]) -> Any:
        raise NotImplementedError


class BooleanNode(ASTNode):
    def __init__(self, value: bool):
        self.value = value
    
    def eval(self, case: Dict[str, Any]) -> bool:
        return self.value


class NullNode(ASTNode):
    def eval(self, case: Dict[str, Any]) -> None:
        return None


class NumberNode(ASTNode):
    def __init__(self, value: Union[int, float]):
        self.value = value
    
    def eval(self, case: Dict[str, Any]) -> Union[int, float]:
        return self.value


class FieldNode(ASTNode):
    def __init__(self, path: str):
        self.path = path
    
    def eval(self, case: Dict[str, Any]) -> Any:
        return get_field_value(case, self.path)


class NotNode(ASTNode):
    def __init__(self, expr: ASTNode):
        self.expr = expr
    
    def eval(self, case: Dict[str, Any]) -> bool:
        return not bool(self.expr.eval(case))


class AndNode(ASTNode):
    def __init__(self, left: ASTNode, right: ASTNode):
        self.left = left
        self.right = right
    
    def eval(self, case: Dict[str, Any]) -> bool:
        return bool(self.left.eval(case)) and bool(self.right.eval(case))


class OrNode(ASTNode):
    def __init__(self, left: ASTNode, right: ASTNode):
        self.left = left
        self.right = right
    
    def eval(self, case: Dict[str, Any]) -> bool:
        return bool(self.left.eval(case)) or bool(self.right.eval(case))


class ComparisonNode(ASTNode):
    def __init__(self, left: ASTNode, operator: TokenType, right: ASTNode):
        self.left = left
        self.operator = operator
        self.right = right
    
    def eval(self, case: Dict[str, Any]) -> bool:
        left_val = self.left.eval(case)
        right_val = self.right.eval(case)
        
        # Handle null comparisons
        if left_val is None or right_val is None:
            if self.operator == TokenType.EQ:
                return left_val is None and right_val is None
            elif self.operator == TokenType.NE:
                return left_val is not None or right_val is not None
            else:
                return False
        
        # Numeric comparisons
        if self.operator == TokenType.EQ:
            return left_val == right_val
        elif self.operator == TokenType.NE:
            return left_val != right_val
        elif self.operator == TokenType.GE:
            return left_val >= right_val
        elif self.operator == TokenType.GT:
            return left_val > right_val
        elif self.operator == TokenType.LE:
            return left_val <= right_val
        elif self.operator == TokenType.LT:
            return left_val < right_val
        else:
            raise ParseError(f"Unknown comparison operator: {self.operator.value}")


class Tokenizer:
    """Tokenizes boolean expressions."""
    
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
    
    def tokenize(self) -> List[Token]:
        """Tokenize the input text."""
        tokens = []
        
        while self.pos < len(self.text):
            self.skip_whitespace()
            if self.pos >= len(self.text):
                break
            
            token = self.next_token()
            if token:
                tokens.append(token)
        
        tokens.append(Token(TokenType.EOF, position=self.pos))
        return tokens
    
    def skip_whitespace(self):
        """Skip whitespace characters."""
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            self.pos += 1
    
    def next_token(self) -> Token:
        """Get next token."""
        char = self.text[self.pos]
        
        # Single character tokens
        if char == '(':
            self.pos += 1
            return Token(TokenType.LPAREN, position=self.pos - 1)
        elif char == ')':
            self.pos += 1
            return Token(TokenType.RPAREN, position=self.pos - 1)
        elif char == '.':
            self.pos += 1
            return Token(TokenType.DOT, position=self.pos - 1)
        
        # Multi-character tokens
        elif char in ['=', '!', '>', '<']:
            return self.parse_comparison()
        elif char.isalpha():
            return self.parse_identifier()
        elif char.isdigit():
            return self.parse_number()
        else:
            raise ParseError(f"Unexpected character: {char}", self.pos)
    
    def parse_comparison(self) -> Token:
        """Parse comparison operators."""
        start_pos = self.pos
        
        if self.text[self.pos:self.pos+2] == '==':
            self.pos += 2
            return Token(TokenType.EQ, position=start_pos)
        elif self.text[self.pos:self.pos+2] == '!=':
            self.pos += 2
            return Token(TokenType.NE, position=start_pos)
        elif self.text[self.pos:self.pos+2] == '>=':
            self.pos += 2
            return Token(TokenType.GE, position=start_pos)
        elif self.text[self.pos:self.pos+2] == '<=':
            self.pos += 2
            return Token(TokenType.LE, position=start_pos)
        elif self.text[self.pos] == '>':
            self.pos += 1
            return Token(TokenType.GT, position=start_pos)
        elif self.text[self.pos] == '<':
            self.pos += 1
            return Token(TokenType.LT, position=start_pos)
        else:
            raise ParseError(f"Invalid operator starting with {self.text[self.pos]}", self.pos)
    
    def parse_identifier(self) -> Token:
        """Parse identifiers and keywords."""
        start_pos = self.pos
        value = ""
        
        while self.pos < len(self.text) and (self.text[self.pos].isalnum() or self.text[self.pos] == '_'):
            value += self.text[self.pos]
            self.pos += 1
        
        # Check for keywords
        if value == 'true':
            return Token(TokenType.TRUE, True, start_pos)
        elif value == 'false':
            return Token(TokenType.FALSE, False, start_pos)
        elif value == 'null':
            return Token(TokenType.NULL, None, start_pos)
        elif value == 'and':
            return Token(TokenType.AND, position=start_pos)
        elif value == 'or':
            return Token(TokenType.OR, position=start_pos)
        elif value == 'not':
            return Token(TokenType.NOT, position=start_pos)
        else:
            return Token(TokenType.IDENTIFIER, value, start_pos)
    
    def parse_number(self) -> Token:
        """Parse numeric literals."""
        start_pos = self.pos
        value = ""
        
        while self.pos < len(self.text) and (self.text[self.pos].isdigit() or self.text[self.pos] == '.'):
            value += self.text[self.pos]
            self.pos += 1
        
        try:
            if '.' in value:
                return Token(TokenType.NUMBER, float(value), start_pos)
            else:
                return Token(TokenType.NUMBER, int(value), start_pos)
        except ValueError:
            raise ParseError(f"Invalid number: {value}", start_pos)


def get_field_value(case: Dict[str, Any], path: str) -> Any:
    """Get field value from case using dotted path notation."""
    parts = path.split('.')
    current = case
    
    try:
        for part in parts:
            current = current[part]
        return current
    except (KeyError, TypeError):
        raise ParseError(f"Field not found: {path}")


def parse(expr: str) -> ASTNode:
    """Parse a boolean expression into an AST."""
    tokenizer = Tokenizer(expr)
    tokens = tokenizer.tokenize()
    parser = Parser(tokens)
    
    ast = parser.parse_expression()
    if parser.current.type != TokenType.EOF:
        raise ParseError(f"Unexpected token after expression: {parser.current.type.value}")
    
    return ast


def eval_expr(expr: str, case: Dict[str, Any]) -> bool:
    """Parse and evaluate a boolean expression."""
    ast = parse(expr)
    return bool(ast.eval(case))
