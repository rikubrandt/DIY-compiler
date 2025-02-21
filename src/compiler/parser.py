from compiler.tokenizer import Token
from compiler import ast

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

def parse(tokens: list[Token]) -> ast.Expression | None:
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
                    raise Exception(f'{token.loc}: expected "{expected}", found "{token.text}"')
            else:
                if token.text not in expected:
                    comma_separated = ", ".join([f'"{e}"' for e in expected])
                    raise Exception(f'{token.loc}: expected one of: {comma_separated}, found "{token.text}"')
        pos += 1
        return token

    def parse_variable_declaration(allow_decl: bool) -> ast.VarDeclaration:
        consume("var")  
        id_token = consume()
        if id_token.type != "identifier":
            raise Exception(f'{id_token.loc}: expected identifier after "var"')
        var_type = None
        if peek().text == ":":
            consume(":")
            type_token = consume()
            if type_token.text not in ["Int", "Bool", "Unit"]:
                raise Exception(f'{type_token.loc}: expected type (Int, Bool, Unit), found "{type_token.text}"')
            var_type = type_token.text
        consume("=")
        init_expr = parse_expression(0, allow_decl=False)
        return ast.VarDeclaration(name=ast.Identifier(id_token.text), var_type=var_type, value=init_expr)

    def parse_if() -> ast.IfExpression:
        consume("if")
        condition = parse_expression(0, allow_decl=False)
        consume("then")
        then_expr = parse_expression(0, allow_decl=False)
        else_expr = None
        if peek().text == "else":
            consume("else")
            else_expr = parse_expression(0, allow_decl=False)
        return ast.IfExpression(if_side=condition, then=then_expr, else_side=else_expr)

    def parse_while() -> ast.WhileLoop:
        consume("while")
        condition = parse_expression(0, allow_decl=False)
        consume("do")
        body = parse_expression(0, allow_decl=False)
        return ast.WhileLoop(condition=condition, body=body)

    def parse_block() -> ast.Block:
        consume("{")
        statements: list[ast.Expression] = []
        trailing_semicolon = False
        # In blocks, declarations are allowed.
        while peek().text != "}":
            stmt = parse_expression(0, allow_decl=True)
            statements.append(stmt)
            if peek().text == ";":
                consume(";")
                trailing_semicolon = True
            else:
                trailing_semicolon = False
                # For non-control-flow statements, a semicolon is required.
                if peek().text != "}" and not isinstance(stmt, (ast.Block, ast.IfExpression, ast.WhileLoop)):
                    raise Exception(f"Missing semicolon before '{peek().text}'")
        consume("}")

        # If there is a trailing semicolon or the block is empty, the result is Literal(None).
        if trailing_semicolon or not statements:
            result = ast.Literal(value=None)
        else:
            result = statements.pop()
        return ast.Block(expressions=statements, result=result)

    def parse_function(name: str) -> ast.FunctionCall:
        consume("(")
        args: list[ast.Expression] = []
        while peek().text != ")":
            if args:
                if peek().text != ",":
                    raise Exception(f"unexpected token '{peek().text}', expected ','")
                consume(",")
            arg = parse_expression(0, allow_decl=False)
            args.append(arg)
        consume(")")
        return ast.FunctionCall(name=ast.Identifier(name), argument_list=args)

    def parse_parenthesized() -> ast.Expression:
        consume("(")
        expr = parse_expression(0, allow_decl=False)
        consume(")")
        return expr

    # Primary expressions: literals, identifiers, parenthesized expressions, if, while, blocks, variable declarations.
    def parse_primary(allow_decl: bool = False) -> ast.Expression:
        token = peek()
        if token.text == "var":
            if not allow_decl:
                raise Exception(f'{token.loc}: variable declarations are not allowed in this context')
            return parse_variable_declaration(allow_decl)
        if token.text == "{":
            return parse_block()
        if token.text == "(":
            return parse_parenthesized()
        if token.text == "if":
            return parse_if()
        if token.text == "while":
            return parse_while()
        if token.type == "identifier":
            consume()  # consume the identifier
            if peek().text == "(":
                return parse_function(token.text)
            return ast.Identifier(name=token.text)
        if token.type == "int_literal":
            consume()
            return ast.Literal(value=int(token.text))
        if token.type == "boolean_literal":
            consume()
            return ast.Literal(value=(token.text == "true"))
        if token.type == "string_literal":
            consume()
            return ast.Literal(value=token.text)
        raise Exception(f"Unexpected token: {token.text}")

    def parse_unary(allow_decl: bool = False) -> ast.Expression:
        if peek().text in ["not", "-"]:
            op_token = consume()
            operand = parse_unary(allow_decl)
            return ast.UnaryOp(op_token.text, operand)
        return parse_primary(allow_decl)


    def parse_expression(precedence_level: int = 0, allow_decl: bool = False) -> ast.Expression:

        total_levels = len(LEFT_ASSOCIATIVE_BINARY_OPERATORS) + len(RIGHT_ASSOCIATIVE_OPERATORS)
        if precedence_level >= total_levels:
            return parse_unary(allow_decl)
        
        # Left-associative operators.
        if precedence_level < len(LEFT_ASSOCIATIVE_BINARY_OPERATORS):
            # Propagate allow_decl into the left operand.
            left = parse_expression(precedence_level + 1, allow_decl)
            operators = LEFT_ASSOCIATIVE_BINARY_OPERATORS[precedence_level]
            while peek().text in operators:
                op_token = consume()
                # After an operator, declarations are not allowed.
                right = parse_expression(precedence_level + 1, allow_decl=False)
                left = ast.BinaryOp(left, op_token.text, right)
            return left
        
        # Right-associative operators.
        elif precedence_level - len(LEFT_ASSOCIATIVE_BINARY_OPERATORS) < len(RIGHT_ASSOCIATIVE_OPERATORS):
            operators = RIGHT_ASSOCIATIVE_OPERATORS[precedence_level - len(LEFT_ASSOCIATIVE_BINARY_OPERATORS)]
            left = parse_expression(precedence_level + 1, allow_decl)
            if peek().text in operators:
                op_token = consume()
                right = parse_expression(precedence_level, allow_decl=False)
                left = ast.BinaryOp(left, op_token.text, right)
            return left
        return parse_unary(allow_decl)



    if len(tokens) == 0:
        return None
    expr = parse_expression(0, allow_decl=True)
    if pos < len(tokens):
        raise Exception(f'{tokens[pos].loc}: unexpected token "{tokens[pos].text}"')
    return expr
