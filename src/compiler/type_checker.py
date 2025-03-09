import compiler.ast_nodes as ast_nodes
from compiler.ast_nodes import BreakStatement

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
    # Built-in functions:
    env.set("print_int", FunType([Int], Unit))
    env.set("print_bool", FunType([Bool], Unit))
    env.set("read_int", FunType([], Int))

    return env


def typecheck_expressions(node: ast_nodes.Expression, env: TypeEnv | None = None) -> Type:
    
    # Helper to typecheck blocks
    def _typecheck_with_env(n: ast_nodes.Expression, new_env: TypeEnv) -> Any:
        nonlocal env
        old_env = env
        env = new_env
        result = _typecheck(n)
        env = old_env
        return result
    
    if env is None:
        env = create_global_env()

    loop_depth = 0 

    def _typecheck(n: ast_nodes.Expression) -> Any:
        nonlocal loop_depth

        match n:
            case ast_nodes.BreakStatement():
                if loop_depth <= 0:
                    raise Exception(f"Break statement in {n.location} is not inside loop.")
                t = Unit
            case ast_nodes.ContinueStatement():
                if loop_depth <= 0:
                    raise Exception(f"Continue statement in {n.location} is not inside loop.")
                t = Unit
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
                if op in ["+", "-", "*", "/", "%"]:
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
                loop_depth += 1
                body_type = _typecheck(body)
                loop_depth -= 1
                
                # Check if the body contains a return statement - if so, use its type
                # instead of automatically assigning Unit
                if isinstance(body, ast_nodes.Block):
                    # Look for return statements within the block
                    if has_return_statement(body):
                        t = body_type  # Use the body's type (which should be from the return)
                    else:
                        t = Unit
                else:
                    t = Unit


            # Blocks

            case ast_nodes.Block(expressions=expressions, result=result):
                new_env = TypeEnv(env)

                for e in expressions:
                    _typecheck_with_env(e, new_env)
                t_result = _typecheck_with_env(result, new_env)
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
                            f"Argument mismatch with {t_arg}, expected: {expected}")
                t = fun_type.ret
            case ast_nodes.ReturnStatement(value=value):
                try:
                    # Get expected return type from environment
                    expected_return_type = env.get("return")
                    
                    if value is None:
                        # Return without value is Unit
                        actual_return_type = Unit
                    else:
                        # Typecheck the return value
                        actual_return_type = _typecheck(value)
                    
                    # Make sure return type matches function's declared return type
                    if actual_return_type != expected_return_type:
                        raise Exception(f"Return type mismatch: returning {actual_return_type}, function declares {expected_return_type}")
                    
                    # Return statements have the type of their value, not just Unit
                    t = actual_return_type if value is not None else Unit
                    n.type = t  # Set the node's type explicitly
                except Exception as e:
                    if "Undefined variable return" in str(e):
                        raise Exception(f"Return statement at {n.location} is outside of a function")
                    else:
                        raise e

            case _:
                raise Exception(f"Type checking not implemented for {n}")
        print("Typechecking node of type:", type(n))

        n.type = t
        return t

    return _typecheck(node)

def convert_str_to_type(type_str: str) -> Type:
    """Convert a type string to a Type object"""
    if type_str == "Int":
        return Int
    elif type_str == "Bool":
        return Bool
    elif type_str == "Unit":
        return Unit
    else:
        raise Exception(f"Unknown type: {type_str}")

def typecheck_function(func_def: ast_nodes.FunctionDefinition, env: TypeEnv) -> FunType:
    """Typecheck a function definition and return its type"""
    func_env = TypeEnv(env)
    
    param_types: list[Type] = []
    for param in func_def.parameters:
        param_type = convert_str_to_type(param.param_type)
        param_types.append(param_type)
        # Add parameter to function environment
        func_env.set(param.name, param_type)
    
    return_type = convert_str_to_type(func_def.return_type)
    
    # Add a special 'return' variable to track return statements
    func_env.set("return", return_type)
    
    body_type = typecheck_expressions(func_def.body, func_env)
    
    has_return_stmt = False
    def find_return(node):
        nonlocal has_return_stmt
        if isinstance(node, ast_nodes.ReturnStatement):
            has_return_stmt = True
            return
            
        if isinstance(node, ast_nodes.Block):
            for expr in node.expressions:
                find_return(expr)
            find_return(node.result)
        elif isinstance(node, ast_nodes.IfExpression):
            find_return(node.then)
            if node.else_side:
                find_return(node.else_side)
        elif isinstance(node, ast_nodes.WhileLoop):
            find_return(node.body)
    
    find_return(func_def.body)
    
    if not has_return_stmt and body_type != return_type:
        raise Exception(f"Function {func_def.name} has return type {return_type}, but body has type {body_type}")
    
    return FunType(param_types, return_type)

def typecheck(module: ast_nodes.Module, env: TypeEnv | None = None) -> Type:
    
    env = create_global_env()
    #Add func signatures to env
    for func_def in module.function_definitions:
        param_types = [convert_str_to_type(param.param_type) for param in func_def.parameters]
        return_type = convert_str_to_type(func_def.return_type)
        func_type = FunType(param_types, return_type)
        env.set(func_def.name, func_type)

    # Typecheck func bodies
    for func_def in module.function_definitions:
        typecheck_function(func_def, env)

    result_type = Unit
    # Typecheck top-level expressions
    for expr in module.expressions:
        result_type = typecheck_expressions(expr, env)
    
    return result_type


def has_return_statement(node):
    if isinstance(node, ast_nodes.ReturnStatement):
        return True
        
    if isinstance(node, ast_nodes.Block):
        for expr in node.expressions:
            if has_return_statement(expr):
                return True
        return has_return_statement(node.result)
        
    if isinstance(node, ast_nodes.IfExpression):
        if has_return_statement(node.then):
            return True
        if node.else_side and has_return_statement(node.else_side):
            return True
            
    if isinstance(node, ast_nodes.WhileLoop):
        return has_return_statement(node.body)
        
    return False
