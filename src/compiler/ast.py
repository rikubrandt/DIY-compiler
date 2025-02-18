from dataclasses import dataclass
from typing import Optional

@dataclass
class Expression:
    "Base for expressions"


@dataclass
class Identifier(Expression):
    name: str

@dataclass
class Literal(Expression):
    value: int

@dataclass
class BinaryOp(Expression):
    left: Expression
    op: str
    right: Expression

@dataclass
class IfExpression(Expression):
    if_side: Expression 
    then: Expression
    else_side: Optional[Expression] = None

@dataclass
class FunctionCall(Expression):
    name: str
    argument_list: list[Expression]
