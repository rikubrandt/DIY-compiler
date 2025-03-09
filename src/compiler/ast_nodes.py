from dataclasses import dataclass, field
from typing import Optional
from compiler.tokenizer import SourceLocation, L
from compiler.types_compiler import Unit, Type


@dataclass(kw_only=True)
class Expression:
    "Base for expressions"
    location: SourceLocation = field(default=L, compare=False)
    type: Type = field(default=Unit, compare=False)


@dataclass()
class Identifier(Expression):
    name: str


@dataclass()
class Literal(Expression):
    value: int | bool | str | None


@dataclass()
class BinaryOp(Expression):
    left: Expression
    op: str
    right: Expression


@dataclass()
class IfExpression(Expression):
    if_side: Expression
    then: Expression
    else_side: Optional[Expression] = None


@dataclass()
class FunctionCall(Expression):
    name: Identifier
    argument_list: list[Expression]


@dataclass()
class UnaryOp(Expression):
    op: str
    operand: Expression


@dataclass()
class Block(Expression):
    expressions: list[Expression]
    result: Expression


@dataclass()
class VarDeclaration(Expression):
    name: str
    value: Expression
    var_type: Optional[str] = None


@dataclass()
class WhileLoop(Expression):
    condition: Expression
    body: Expression

@dataclass()
class BreakStatement(Expression):
    ...

@dataclass()
class ContinueStatement(Expression):
    ...


@dataclass()
class Parameter:
    name: str
    param_type: str
    location: SourceLocation = field(default=L, compare=False)


@dataclass()
class FunctionDefinition:
    name: str
    parameters: list[Parameter]
    return_type: str
    body: Expression
    location: SourceLocation = field(default=L, compare=False)


@dataclass()
class Module:
    function_definitions: list[FunctionDefinition]
    expressions: list[Expression]
    location: SourceLocation = field(default=L, compare=False)

@dataclass()
class ReturnStatement(Expression):
    value: Optional[Expression] = None