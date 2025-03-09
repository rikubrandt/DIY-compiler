from compiler.tokenizer import Token
from compiler import ast_nodes
from compiler.types_compiler import Int, Bool, Unit

LEFT_ASSOCIATIVE_BINARY_OPERATORS = [
    ["or"],
    ["and"],
    ["==", "!="],
    ["<", "<=", ">", ">="],
    ["+", "-"],
    ["*", "/", "%"],
]

RIGHT_ASSOCIATIVE_OPERATORS = [
    ["="],
]


def parse(tokens: list[Token]) -> ast_nodes.Module | None:
    pos = 0

    def peek() -> Token:
        if pos < len(tokens):
            return tokens[pos]
        else:
            return Token(type="end", text="", loc=tokens[-1].loc)

    def consume(expected: str | list[str] | None = None) -> Token:
        nonlocal pos
        token = peek()
        if expected is not None:
            if isinstance(expected, str):
                if token.text != expected:
                    raise Exception(
                        f'{token.loc}: expected "{expected}", found "{token.text}"')
            else:
                if token.text not in expected:
                    comma_separated = ", ".join([f'"{e}"' for e in expected])
                    raise Exception(
                        f'{token.loc}: expected one of: {comma_separated}, found "{token.text}"')
        pos += 1
        return token
        
    def parse_parameter() -> ast_nodes.Parameter:
        """Parse a function parameter: name: Type"""
        param_token = consume()
        if param_token.type != "identifier":
            raise Exception(f'{param_token.loc}: expected parameter name, found "{param_token.text}"')
        
        consume(":")
        type_token = consume()
        if type_token.text not in ["Int", "Bool", "Unit"]:
            raise Exception(
                f'{type_token.loc}: expected type (Int, Bool, Unit), found "{type_token.text}"')
        
        return ast_nodes.Parameter(name=param_token.text, param_type=type_token.text, location=param_token.loc)
    
    def parse_function_definition() -> ast_nodes.FunctionDefinition:
        """Parse a function definition: fun name(param1: Type, ...): ReturnType { ... }"""
        start_token = consume("fun")
        
        # Parse function name
        name_token = consume()
        if name_token.type != "identifier":
            raise Exception(f'{name_token.loc}: expected function name, found "{name_token.text}"')
        
        # Parse parameters
        consume("(")
        parameters: list[ast_nodes.Parameter] = []
        
        if peek().text != ")":  # If not empty parameter list
            while True:
                param = parse_parameter()
                parameters.append(param)
                
                if peek().text == ")":
                    break
                    
                consume(",")  # Parameters are comma-separated
        
        consume(")")
        
        # Parse return type
        consume(":")
        return_type_token = consume()
        if return_type_token.text not in ["Int", "Bool", "Unit"]:
            raise Exception(
                f'{return_type_token.loc}: expected return type (Int, Bool, Unit), found "{return_type_token.text}"')
        
        # Parse function body (a block)
        body = parse_block()
        
        return ast_nodes.FunctionDefinition(
            name=name_token.text,
            parameters=parameters,
            return_type=return_type_token.text,
            body=body,
            location=start_token.loc
        )

    def parse_variable_declaration(allow_decl: bool) -> ast_nodes.VarDeclaration:
        start_token = consume("var")
        id_token = consume()
        if id_token.type != "identifier":
            raise Exception(f'{id_token.loc}: expected identifier after "var"')
        var_type = None
        if peek().text == ":":
            consume(":")
            type_token = consume()
            if type_token.text not in ["Int", "Bool", "Unit"]:
                raise Exception(
                    f'{type_token.loc}: expected type (Int, Bool, Unit), found "{type_token.text}"')
            var_type = type_token.text
        consume("=")
        init_expr = parse_expression(0, allow_decl=False)
        return ast_nodes.VarDeclaration(name=id_token.text, var_type=var_type, value=init_expr, location=start_token.loc)

    def parse_if() -> ast_nodes.IfExpression:
        start_token = consume("if")
        condition = parse_expression(0, allow_decl=False)
        consume("then")
        then_expr = parse_expression(0, allow_decl=False)
        else_expr = None
        if peek().text == "else":
            consume("else")
            else_expr = parse_expression(0, allow_decl=False)
        return ast_nodes.IfExpression(if_side=condition, then=then_expr, else_side=else_expr, location=start_token.loc)

    def parse_while() -> ast_nodes.WhileLoop:
        start_token = consume("while")
        condition = parse_expression(0, allow_decl=False)
        consume("do")
        body = parse_expression(0, allow_decl=False)
        return ast_nodes.WhileLoop(condition=condition, body=body, location=start_token.loc)

    def parse_block() -> ast_nodes.Block:
        start_token = consume("{")
        statements: list[ast_nodes.Expression] = []
        
        if peek().text == "}":
            consume("}")
            return ast_nodes.Block(
                expressions=[],
                result=ast_nodes.Literal(value=None, type=Unit, location=start_token.loc),
                location=start_token.loc
            )
        
        while True:
            stmt = parse_expression(0, allow_decl=True)
            statements.append(stmt)
            
            if peek().text == "}":
                break
                
            can_skip_semicolon = isinstance(stmt, (ast_nodes.Block, ast_nodes.IfExpression, 
                                                ast_nodes.WhileLoop))
            
            if peek().text == ";":
                consume(";")
                if peek().text == "}":
                    statements.append(ast_nodes.Literal(value=None, type=Unit, location=stmt.location))
                    break
            elif not can_skip_semicolon:
                raise Exception(f"Missing semicolon after '{tokens[pos-1].text}' before '{peek().text}'")
        
        consume("}")
        
        if not statements:
            result = ast_nodes.Literal(value=None, type=Unit, location=start_token.loc)
        else:
            result = statements.pop()
            
        return ast_nodes.Block(expressions=statements, result=result, location=start_token.loc)



    def parse_return() -> ast_nodes.ReturnStatement:
        """Parse a return statement: return expr;"""
        start_token = consume("return")
        
        if peek().text != ";":
            value = parse_expression(0, allow_decl=False)
            # Return statements must be followed by a semicolon
            if peek().text != ";":
                raise Exception(f"Expected semicolon after return statement, found {peek().text}")
            consume(";")
            return ast_nodes.ReturnStatement(value=value, location=start_token.loc)
        else:
            consume(";")
            return ast_nodes.ReturnStatement(location=start_token.loc)

    def parse_function(name: str) -> ast_nodes.FunctionCall:
        start_token = consume("(")
        args: list[ast_nodes.Expression] = []
        while peek().text != ")":
            if args:
                if peek().text != ",":
                    raise Exception(
                        f"unexpected token '{peek().text}', expected ','")
                consume(",")
            arg = parse_expression(0, allow_decl=False)
            args.append(arg)
        consume(")")
        return ast_nodes.FunctionCall(name=ast_nodes.Identifier(name), argument_list=args, location=start_token.loc)

    def parse_parenthesized() -> ast_nodes.Expression:
        consume("(")
        expr = parse_expression(0, allow_decl=False)
        consume(")")
        return expr

    # Primary expressions:
    def parse_primary(allow_decl: bool = False) -> ast_nodes.Expression:
        token = peek()
        if token.text == "var":
            if not allow_decl:
                raise Exception(
                    f'{token.loc}: variable declarations are not allowed in this context')
            return parse_variable_declaration(allow_decl)
        if token.text == "return":
            return parse_return()
        if token.text == "{":
            return parse_block()
        if token.text == "(":
            return parse_parenthesized()
        if token.text == "if":
            return parse_if()
        if token.text == "while":
            return parse_while()
        if token.text == "break":
            consume()
            return ast_nodes.BreakStatement()
        if token.text == "continue":
            consume()
            return ast_nodes.ContinueStatement()
        if token.type == "identifier":
            consume()
            if peek().text == "(":
                return parse_function(token.text)
            return ast_nodes.Identifier(name=token.text, location=token.loc)
        if token.type == "int_literal":
            consume()
            return ast_nodes.Literal(value=int(token.text), type=Int, location=token.loc)
        if token.type == "boolean_literal":
            consume()
            return ast_nodes.Literal(value=(token.text == "true"), type=Bool, location=token.loc)
        raise Exception(f"Unexpected token: {token.text}")

    def parse_unary(allow_decl: bool = False) -> ast_nodes.Expression:
        if peek().text in ["not", "-"]:
            op_token = consume()
            operand = parse_unary(allow_decl)
            return ast_nodes.UnaryOp(op=op_token.text, operand=operand, location=op_token.loc)
        return parse_primary(allow_decl)

    def parse_expression(precedence_level: int = 0, allow_decl: bool = False) -> ast_nodes.Expression:
        total_levels = len(LEFT_ASSOCIATIVE_BINARY_OPERATORS) + len(RIGHT_ASSOCIATIVE_OPERATORS)
        
        if precedence_level >= total_levels:
            return parse_unary(allow_decl)
            
        if precedence_level == 0:
            left = parse_expression(precedence_level + 1, allow_decl)
            
            if peek().text in RIGHT_ASSOCIATIVE_OPERATORS[0]:
                op_token = consume()
                # Recursively parse at the same precedence level (right associative)
                right = parse_expression(precedence_level, allow_decl=False)
                left = ast_nodes.BinaryOp(left, op_token.text, right, location=op_token.loc)
            return left
        
        else:
            level = precedence_level - 1
            
            if level < len(LEFT_ASSOCIATIVE_BINARY_OPERATORS):
                left = parse_expression(precedence_level + 1, allow_decl)
                operators = LEFT_ASSOCIATIVE_BINARY_OPERATORS[level]
                
                while peek().text in operators:
                    op_token = consume()
                    right = parse_expression(precedence_level + 1, allow_decl=False)
                    left = ast_nodes.BinaryOp(left, op_token.text, right, location=op_token.loc)
                return left
            
            return parse_unary(allow_decl)

    def can_skip_semicolon(expr) -> bool:
        """Determine if this expression type can be followed by another expression without a semicolon"""
    
        # Basic types that don't need semicolons
        if isinstance(expr, (ast_nodes.Block, ast_nodes.IfExpression, 
                            ast_nodes.WhileLoop, ast_nodes.FunctionDefinition)):
            return True
        
        # Special case for binary operations with 'or' and 'and'
        if isinstance(expr, ast_nodes.BinaryOp) and expr.op in ['or', 'and']:
            return True
        
        # Special case for variable declarations with block values
        # This handles cases like: var x = { ... } expr
        if isinstance(expr, ast_nodes.VarDeclaration):
            if isinstance(expr.value, (ast_nodes.Block, ast_nodes.IfExpression, ast_nodes.WhileLoop)):
                return True
        
        return False

    def parse_module() -> ast_nodes.Module:
        """Parse a complete module, which may contain function definitions and top-level expressions."""
        module_loc = tokens[0].loc if tokens else None
        
        # Parse function definitions and top-level expressions
        function_definitions: list[ast_nodes.FunctionDefinition] = []
        expressions: list[ast_nodes.Expression] = []
        
        while pos < len(tokens) and peek().type != "end":
            # Parse the current top-level item
            if peek().text == "fun":
                # Parse function definition
                func_def = parse_function_definition()
                function_definitions.append(func_def)
            else:
                # Parse top-level expression
                expr = parse_expression(0, allow_decl=True)
                expressions.append(expr)
                
                # Check if we need a semicolon after this expression
                if pos < len(tokens) and peek().type != "end":                
                    # If there's a semicolon, consume it
                    if peek().text == ";":
                        consume(";")
                        # If this is the end of input after semicolon, add Unit
                        if pos >= len(tokens) or peek().type == "end":
                            expressions.append(ast_nodes.Literal(value=None, type=Unit, location=expr.location))
                    # No semicolon, check if that's allowed
                    elif not can_skip_semicolon(expr):
                        next_token = peek()
                        raise Exception(f"{next_token.loc}: Expected semicolon after expression, found '{next_token.text}'")
        
        return ast_nodes.Module(
            function_definitions=function_definitions,
            expressions=expressions,
            location=module_loc
        )







    
    if len(tokens) == 0:
        return None

    # Parse the entire module
    return parse_module()