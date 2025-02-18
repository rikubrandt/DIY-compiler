from dataclasses import dataclass

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


