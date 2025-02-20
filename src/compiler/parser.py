
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
        if isinstance(expected, str) and token.text != expected:
            raise Exception(f'{token.loc}: expected "{expected}"')
        if isinstance(expected, list) and token.text not in expected:
            comma_separated = ", ".join([f'"{e}"' for e in expected])
            raise Exception(f'{token.loc}: expected one of: {comma_separated}')
        pos += 1
        return token
    
    def parse_if() -> ast.IfExpression:
        consume("if")
        if_side = parse_expression()
        consume("then")
        then = parse_expression()
        else_side = None
        if peek().text == ("else"):
            consume("else")
            else_side = parse_expression()

        return ast.IfExpression(
            if_side=if_side,
            then=then,
            else_side=else_side
        )
    def parse_function(name) -> ast.FunctionCall:
        consume("(")
        argument_list: list[ast.Expression] = []
        while peek().text != ")":
            if argument_list:
                if peek().text != ",":
                    raise Exception(f"unexpected token '{peek().text}', expected ','")
                consume(",")
            argument_list.append(parse_expression())
        consume(")")
        return ast.FunctionCall(name=name, argument_list=argument_list)



    def parse_primary() -> ast.Expression:
        """Literals, identifiers, if-expressions, function calls, and parenthesized expr."""
        token = peek()

        if token.text == "(":
            return parse_parenthesized()

        if token.text == "if":
            return parse_if()

        if token.type == "identifier":
            consume()
            if peek().text == "(":
                return parse_function(token.text)
            return ast.Identifier(name=token.text)
        
        if token.type == "int_literal":
            consume()
            return ast.Literal(value=int(token.text))
        
        if token.type in ["string_literal", "boolean_literal"]:
            consume()
            return ast.Literal(value=token.text)

        raise Exception(f"Unexpected token: {token.text}")

 
        
    def parse_unary() -> ast.Expression:
        if peek().text in ["not", "-"]:
            op_token = consume()
            operand = parse_unary()
            return ast.UnaryOp(op_token.text, operand)
        return parse_primary()
    
    def parse_parenthesized() -> ast.Expression:
        consume('(')
        expr = parse_expression()
        consume(')')
        return expr
    
    def parse_expression(precedence_level=0) -> ast.Expression:
        
        if precedence_level >= len(LEFT_ASSOCIATIVE_BINARY_OPERATORS) + len(RIGHT_ASSOCIATIVE_OPERATORS):
            return parse_unary()
        
        if precedence_level < len(LEFT_ASSOCIATIVE_BINARY_OPERATORS):
            left = parse_expression(precedence_level+1)
            operators = LEFT_ASSOCIATIVE_BINARY_OPERATORS[precedence_level]
            while peek().text in operators:
                op_token = consume()
                right = parse_expression(precedence_level+1)
                left = ast.BinaryOp(left, op_token.text, right)
            return left

        elif precedence_level -  len(LEFT_ASSOCIATIVE_BINARY_OPERATORS) < len(RIGHT_ASSOCIATIVE_OPERATORS):
            operators = RIGHT_ASSOCIATIVE_OPERATORS[precedence_level - len(LEFT_ASSOCIATIVE_BINARY_OPERATORS)]
            left = parse_expression(precedence_level+1)

            if peek().text in operators:
                op_token = consume()
                right = parse_expression(precedence_level)
                left = ast.BinaryOp(left, op_token.text, right)
            return left
        
        return parse_unary()


    if len(tokens) == 0:
        return None

    expr = parse_expression()

    if pos < len(tokens):
        raise Exception(f'{tokens[pos].loc}: unexpected token "{tokens[pos].text}"')
    return expr