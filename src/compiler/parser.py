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


def parse(tokens: list[Token]) -> ast_nodes.Expression | None:
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
                if peek().text != "}" and not isinstance(stmt, (ast_nodes.Block, ast_nodes.IfExpression, ast_nodes.WhileLoop)):
                    raise Exception(
                        f"Missing semicolon before '{peek().text}'")
        consume("}")

        # If there is a trailing semicolon or the block is empty, the result is Literal(None).
        if trailing_semicolon or not statements:
            result = ast_nodes.Literal(value=None)
        else:
            result = statements.pop()
            assert isinstance(result, ast_nodes.Expression)
        return ast_nodes.Block(expressions=statements, result=result, location=start_token.loc)

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

    # Primary expressions: literals, identifiers, parenthesized expressions, if, while, blocks, variable declarations.
    def parse_primary(allow_decl: bool = False) -> ast_nodes.Expression:
        token = peek()
        if token.text == "var":
            if not allow_decl:
                raise Exception(
                    f'{token.loc}: variable declarations are not allowed in this context')
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



    if len(tokens) == 0:
        return None




    top_level_statements: list[ast_nodes.Expression] = [parse_expression(0, allow_decl=True)]
    while pos < len(tokens) and peek().type != "end":
        if peek().text == ";":
            consume(";")
            # If there is another expression, add it.
            if pos < len(tokens) and peek().type != "end":
                top_level_statements.append(parse_expression(0, allow_decl=True))
            else:
                top_level_statements.append(ast_nodes.Literal(value=None, type=Unit, location=top_level_statements[-1].location))
        else:
            # No semicolon between expressions.
            
            # Check if the next token is the start of a valid top-level construct
            is_valid_next_token = False
            
            # Case 1: After a block, if, or while
            if isinstance(top_level_statements[-1], (ast_nodes.Block, ast_nodes.IfExpression, ast_nodes.WhileLoop)):
                is_valid_next_token = True
            # Case 2: If the next token is an identifier at the end of the program
            elif peek().type == "identifier" and pos + 1 >= len(tokens):
                is_valid_next_token = True
            # Case 3: If the next token is the start of a function call (likely print_bool, print_int, etc.)
            elif peek().type == "identifier" and pos + 1 < len(tokens) and tokens[pos + 1].text == "(":
                is_valid_next_token = True
            # Case 4: If the previous token had 'or' or 'and' operators
            elif any(isinstance(expr, ast_nodes.BinaryOp) and expr.op in ['or', 'and'] 
                    for expr in top_level_statements):
                is_valid_next_token = True
                
            if is_valid_next_token:
                top_level_statements.append(parse_expression(0, allow_decl=True))
            else:
                raise Exception(f'{peek().loc}: unexpected token "{peek().text}"')

    # If there's just one top-level expression, return it directly.
    # Otherwise, combine them into a Block.
    if len(top_level_statements) == 1:
        return top_level_statements[0]
    else:
        return ast_nodes.Block(
            expressions=top_level_statements[:-1],
            result=top_level_statements[-1],
            location=top_level_statements[0].location
        )