
from compiler.tokenizer import Token
from compiler import ast

def parse(tokens: list[Token]) -> ast.Expression:
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
    
    def parse_factor() -> ast.Expression:
        if peek().text == ("("):
            return parse_parenthesized()
        if peek().type == 'int_literal':
            return parse_int_literal()
        elif peek().type == 'identifier':
            return parse_identifier()
        else:
            raise Exception(f'{peek().loc}: expected an integer literal or an identifier')


    def parse_identifier() -> ast.Identifier:
        token = peek()
        if token.type == "identifier":
            consume()
            return ast.Identifier(name=token.text)
        else:
            raise Exception(f"Expected literal found, {token.text}")
    
    def parse_int_literal() -> ast.Literal:
        token = peek()
        if token.type == "int_literal":
            consume()
            return ast.Literal(value=int(token.text))
        else:
            raise Exception(f"Expected literal found, {token.text}")

    def parse_term() -> ast.Expression:
        left = parse_factor()
        while peek().text in ['*', '/']:
            operator_token = consume()
            operator = operator_token.text
            right = parse_factor()
            left = ast.BinaryOp(
                left,
                operator,
                right
            )
        return left    
        
    def parse_parenthesized() -> ast.Expression:
        consume('(')
        expr = parse_expression()
        consume(')')
        return expr
    
    def parse_expression() -> ast.Expression:
        left: ast.Expression = parse_term()
        while peek().text in ["+", "-"]:
            op_token = consume()
            right = parse_term()
            left = ast.BinaryOp(left, op_token.text, right)
        
        return left

    return parse_expression()