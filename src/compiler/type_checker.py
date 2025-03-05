import compiler.ast_nodes as ast_nodes
from compiler.types_compiler import Int, Type, Unit, Bool, FunType
from typing import Optional, Any

# Symbol table


class TypeEnv:
    def __init__(self, parent: Optional["TypeEnv"] = None) -> None:
        self.env: dict[str, Any] = {}
        self.parent = parent

    def get(self, name: str) -> Any:
        if name in self.env:
            return self.env[name]
        elif self.parent:
            return self.parent.get(name)
        else:
            raise Exception(f"Undefined variable {name}")

    # Set type

    def set(self, name: str, typ: Any) -> None:
        self.env[name] = typ


def create_global_env() -> TypeEnv:
    env = TypeEnv()
    # Built-in print functions:
    env.set("print_int", FunType([Int], Unit))
    env.set("print_bool", FunType([Bool], Unit))
    # You can add other built-ins here if needed.
    return env


def typecheck(node: ast_nodes.Expression, env: TypeEnv | None = None) -> Type:

    if env is None:
        env = create_global_env()

    def _typecheck(n: ast_nodes.Expression) -> Any:
        match n:

            # Literals
            case ast_nodes.Literal(value=value):
                if isinstance(value, bool):
                    t = Bool
                elif isinstance(value, int):
                    t = Int
                else:
                    t = Unit

            # Identifiers
            case ast_nodes.Identifier(name=name):
                t = env.get(name)

            case ast_nodes.UnaryOp(op=op, operand=operand):
                t_operand = _typecheck(operand)
                if op == '-':
                    if t_operand is not Int:
                        raise Exception(
                            f"Unary '-' operator requires an Int operand, got {t_operand}")
                    t = Int
                elif op == 'not':
                    if t_operand is not Bool:
                        raise Exception(
                            f"Unary 'not' operator requires a Bool operand, got {t_operand}")
                    t = Bool
                else:
                    raise Exception(f"Unknown unary operator: {op}")

            # BinaryOps
            case ast_nodes.BinaryOp(left=left, op=op, right=right):
                t_left = _typecheck(left)
                t_right = _typecheck(right)
                if op in ["+", "-", "*", "/"]:
                    if t_left is not Int or t_right is not Int:
                        raise Exception(
                            f"Operator {op} requires int operands, got {t_left} and {t_right}")
                    t = Int
                elif op in ["<", "<=", ">", ">="]:
                    if t_left is not Int and t_right is not Int:
                        raise Exception(
                            f"Operator {op} requires int operands, got {t_left} and {t_right}")
                    t = Bool
                elif op in ["and", "or"]:
                    if t_left is not Bool or t_right is not Bool:
                        raise Exception(
                            f"Operator {op} requires bool operands, got {t_left} and {t_right}")
                    t = Bool
                elif op in ["==", "!="]:
                    if t_left != t_right:
                        raise Exception(
                            f"Operator {op} requires operands to be same, got {t_left} and {t_right}")
                    t = Bool
                elif op == "==":
                    if not isinstance(left, ast_nodes.Identifier):
                        raise Exception(
                            "Left side of assignment must be an identifier")
                    var_type = env.get(left.name)
                    if var_type != t_right:
                        raise Exception(
                            "Assigned value has a different type than the variable")
                    t = var_type
                elif op == "=":
                    if not isinstance(left, ast_nodes.Identifier):
                        raise Exception(
                            "Left side of assignment must be an identifier")
                    var_type = env.get(left.name)
                    if var_type != t_right:
                        raise Exception(
                            "Assigned value has a different type than the variable")
                    t = var_type

                else:
                    raise Exception(f"Unknown operator {op}")

            # Var declarations
            case ast_nodes.VarDeclaration(name=name, var_type=declared_type, value=value):
                t_value = _typecheck(value)
                if declared_type is not None:
                    # Convert the string to type object (e.g., "Int" -> Int)
                    declared = Int if declared_type == "Int" else Bool if declared_type == "Bool" else Unit
                    if declared != t_value:
                        raise Exception(
                            f"Type mismatch: declared {declared}, but initializer has type {t_value}")
                t = t_value
                env.set(name, t)

            # If expression

            case ast_nodes.IfExpression(if_side=if_side, then=then, else_side=else_side):
                t_cond = _typecheck(if_side)
                if t_cond is not Bool:
                    raise Exception(
                        f"If expression needs type Bool, got {t_cond}")
                t_then = _typecheck(then)
                t_else = _typecheck(
                    else_side) if else_side is not None else None
                if t_else is not None and t_then != t_else:
                    raise Exception(
                        f"Branches of if must have same type, got {t_then}, {t_else}")

                t = t_then

            # While loop
            case ast_nodes.WhileLoop(condition=condition, body=body):
                t_cond = _typecheck(condition)
                if t_cond is not Bool:
                    raise Exception(
                        f"While loops condition must be Bool, got type {t_cond}")
                _typecheck(body)
                t = Unit

            # Blocks

            case ast_nodes.Block(expressions=expressions, result=result):
                new_env = TypeEnv(env)

                for e in expressions:
                    _typecheck(e)
                t_result = _typecheck(result)
                t = t_result

            # Func calls

            case ast_nodes.FunctionCall(name=name, argument_list=args):
                fun_type = env.get(name.name)
                if not isinstance(fun_type, FunType):
                    raise Exception(f"{name.name} is not a function.")
                if len(fun_type.params) != len(args):
                    raise Exception("Wrong number of arguments.")
                for expected, arg in zip(fun_type.params, args):
                    t_arg = _typecheck(arg)
                    if t_arg != expected:
                        raise Exception(
                            f"Argument mistmatch with {t_arg}, expected: {expected}")
                t = fun_type.ret

            case _:
                raise Exception(f"Type checking not implemented for {n}")
        print("Typechecking node of type:", type(n))

        n.type = t
        return t

    return _typecheck(node)
