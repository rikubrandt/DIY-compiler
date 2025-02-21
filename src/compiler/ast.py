from dataclasses import dataclass, field
from typing import Optional
from compiler.tokenizer import SourceLocation, L

@dataclass(frozen=True, kw_only=True)
class Expression:
    "Base for expressions"
    location: SourceLocation = field(default=L, compare=False)

@dataclass(frozen=True)
class Identifier(Expression):
    name: str

@dataclass(frozen=True)
class Literal(Expression):
    value: int | bool | str | None

@dataclass(frozen=True)
class BinaryOp(Expression):
    left: Expression
    op: str
    right: Expression

@dataclass(frozen=True)
class IfExpression(Expression):
    if_side: Expression 
    then: Expression
    else_side: Optional[Expression] = None

@dataclass(frozen=True)
class FunctionCall(Expression):
    name: Identifier
    argument_list: list[Expression]

@dataclass(frozen=True)
class UnaryOp(Expression):
    op: str
    operand: Optional[str] = None

@dataclass(frozen=True)
class Block(Expression):
    expressions: list[Expression]
    result: Expression

@dataclass(frozen=True)
class VarDeclaration(Expression):
    name: str
    value: Expression
    var_type: Optional[str] = None

@dataclass(frozen=True)
class WhileLoop(Expression):
    condition: Expression
    body: Expression
