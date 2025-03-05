from compiler.tokenizer import tokenize, Token, L


def test_identifier() -> None:
    assert tokenize("hello") == [
        Token(type="identifier", text="hello", loc=L)
    ]


def test_whitespace_and_identifier() -> None:
    assert tokenize("     \n       hello          ") == [
        Token(type="identifier", text="hello", loc=L)
    ]


def test_simple_expression() -> None:
    assert tokenize("3+5") == [
        Token(type="int_literal", text="3", loc=L),
        Token(type="operator", text="+", loc=L),
        Token(type="int_literal", text="5", loc=L)
    ]


def test_expression_with_unary_operator() -> None:
    assert tokenize("3 + -5") == [
        Token(type="int_literal", text="3", loc=L),
        Token(type="operator", text="+", loc=L),
        Token(type="operator", text="-", loc=L),
        Token(type="int_literal", text="5", loc=L)
    ]


def test_parentheses_expression() -> None:
    assert tokenize("(3+5)") == [
        Token(type="parenthesis", text="(", loc=L),
        Token(type="int_literal", text="3", loc=L),
        Token(type="operator", text="+", loc=L),
        Token(type="int_literal", text="5", loc=L),
        Token(type="parenthesis", text=")", loc=L),
    ]


def test_operators() -> None:
    assert tokenize("+ - * / = == != < <= > >=") == [
        Token(type="operator", text="+", loc=L),
        Token(type="operator", text="-", loc=L),
        Token(type="operator", text="*", loc=L),
        Token(type="operator", text="/", loc=L),
        Token(type="operator", text="=", loc=L),
        Token(type="operator", text="==", loc=L),
        Token(type="operator", text="!=", loc=L),
        Token(type="operator", text="<", loc=L),
        Token(type="operator", text="<=", loc=L),
        Token(type="operator", text=">", loc=L),
        Token(type="operator", text=">=", loc=L),
    ]


def test_comment() -> None:
    assert tokenize("// Comment") == [
    ]
    assert tokenize("# Comment") == [
    ]


def test_complex_expressions() -> None:
    assert tokenize("3 * (3 + 5)") == [
        Token(type="int_literal", text="3", loc=L),
        Token(type="operator", text="*", loc=L),
        Token(type="parenthesis", text="(", loc=L),
        Token(type="int_literal", text="3", loc=L),
        Token(type="operator", text="+", loc=L),
        Token(type="int_literal", text="5", loc=L),
        Token(type="parenthesis", text=")", loc=L),
    ]

    assert tokenize("a < b >= c") == [
        Token(type="identifier", text="a", loc=L),
        Token(type="operator", text="<", loc=L),
        Token(type="identifier", text="b", loc=L),
        Token(type="operator", text=">=", loc=L),
        Token(type="identifier", text="c", loc=L),
    ]


def test_boolean_literals() -> None:
    assert tokenize("true false") == [
        Token(type="boolean_literal", text="true", loc=L),
        Token(type="boolean_literal", text="false", loc=L),
    ]


def test_keywords() -> None:
    assert tokenize("if then else while do var Int Bool Unit") == [
        Token(type="keyword", text="if", loc=L),
        Token(type="keyword", text="then", loc=L),
        Token(type="keyword", text="else", loc=L),
        Token(type="keyword", text="while", loc=L),
        Token(type="keyword", text="do", loc=L),
        Token(type="keyword", text="var", loc=L),
        Token(type="keyword", text="Int", loc=L),
        Token(type="keyword", text="Bool", loc=L),
        Token(type="keyword", text="Unit", loc=L),
    ]


def test_function_call() -> None:
    assert tokenize("f(x, y)") == [
        Token(type="identifier", text="f", loc=L),
        Token(type="parenthesis", text="(", loc=L),
        Token(type="identifier", text="x", loc=L),
        Token(type="parenthesis", text=",", loc=L),
        Token(type="identifier", text="y", loc=L),
        Token(type="parenthesis", text=")", loc=L),
    ]


def test_function_call_with_expression() -> None:
    assert tokenize("g(2 + 3, y)") == [
        Token(type="identifier", text="g", loc=L),
        Token(type="parenthesis", text="(", loc=L),
        Token(type="int_literal", text="2", loc=L),
        Token(type="operator", text="+", loc=L),
        Token(type="int_literal", text="3", loc=L),
        Token(type="parenthesis", text=",", loc=L),
        Token(type="identifier", text="y", loc=L),
        Token(type="parenthesis", text=")", loc=L),
    ]


def test_if_statement() -> None:
    assert tokenize("if x > 5 then y = 3") == [
        Token(type="keyword", text="if", loc=L),
        Token(type="identifier", text="x", loc=L),
        Token(type="operator", text=">", loc=L),
        Token(type="int_literal", text="5", loc=L),
        Token(type="keyword", text="then", loc=L),
        Token(type="identifier", text="y", loc=L),
        Token(type="operator", text="=", loc=L),
        Token(type="int_literal", text="3", loc=L),
    ]


def test_if_else_statement() -> None:
    assert tokenize("if a then b else c") == [
        Token(type="keyword", text="if", loc=L),
        Token(type="identifier", text="a", loc=L),
        Token(type="keyword", text="then", loc=L),
        Token(type="identifier", text="b", loc=L),
        Token(type="keyword", text="else", loc=L),
        Token(type="identifier", text="c", loc=L),
    ]


def test_while_loop() -> None:
    assert tokenize("while x < 10 do { x = x * 2; }") == [
        Token(type="keyword", text="while", loc=L),
        Token(type="identifier", text="x", loc=L),
        Token(type="operator", text="<", loc=L),
        Token(type="int_literal", text="10", loc=L),
        Token(type="keyword", text="do", loc=L),
        Token(type="parenthesis", text="{", loc=L),
        Token(type="identifier", text="x", loc=L),
        Token(type="operator", text="=", loc=L),
        Token(type="identifier", text="x", loc=L),
        Token(type="operator", text="*", loc=L),
        Token(type="int_literal", text="2", loc=L),
        Token(type="parenthesis", text=";", loc=L),
        Token(type="parenthesis", text="}", loc=L),
    ]


def test_variable_declaration() -> None:
    assert tokenize("var x = 10") == [
        Token(type="keyword", text="var", loc=L),
        Token(type="identifier", text="x", loc=L),
        Token(type="operator", text="=", loc=L),
        Token(type="int_literal", text="10", loc=L),
    ]


def test_typed_variable_declaration() -> None:
    assert tokenize("var y: Int = 5") == [
        Token(type="keyword", text="var", loc=L),
        Token(type="identifier", text="y", loc=L),
        Token(type="parenthesis", text=":", loc=L),
        Token(type="keyword", text="Int", loc=L),
        Token(type="operator", text="=", loc=L),
        Token(type="int_literal", text="5", loc=L),
    ]


def test_unary_operator() -> None:
    assert tokenize("not x") == [
        Token(type="operator", text="not", loc=L),
        Token(type="identifier", text="x", loc=L),
    ]


def test_nested_parentheses() -> None:
    assert tokenize("(x * (y + (z - 3)))") == [
        Token(type="parenthesis", text="(", loc=L),
        Token(type="identifier", text="x", loc=L),
        Token(type="operator", text="*", loc=L),
        Token(type="parenthesis", text="(", loc=L),
        Token(type="identifier", text="y", loc=L),
        Token(type="operator", text="+", loc=L),
        Token(type="parenthesis", text="(", loc=L),
        Token(type="identifier", text="z", loc=L),
        Token(type="operator", text="-", loc=L),
        Token(type="int_literal", text="3", loc=L),
        Token(type="parenthesis", text=")", loc=L),
        Token(type="parenthesis", text=")", loc=L),
        Token(type="parenthesis", text=")", loc=L),
    ]


def test_block() -> None:
    assert tokenize("{ a = 1; b = 2; c = a + b; }") == [
        Token(type="parenthesis", text="{", loc=L),
        Token(type="identifier", text="a", loc=L),
        Token(type="operator", text="=", loc=L),
        Token(type="int_literal", text="1", loc=L),
        Token(type="parenthesis", text=";", loc=L),
        Token(type="identifier", text="b", loc=L),
        Token(type="operator", text="=", loc=L),
        Token(type="int_literal", text="2", loc=L),
        Token(type="parenthesis", text=";", loc=L),
        Token(type="identifier", text="c", loc=L),
        Token(type="operator", text="=", loc=L),
        Token(type="identifier", text="a", loc=L),
        Token(type="operator", text="+", loc=L),
        Token(type="identifier", text="b", loc=L),
        Token(type="parenthesis", text=";", loc=L),
        Token(type="parenthesis", text="}", loc=L),
    ]


def test_nested_blocks() -> None:
    assert tokenize("{ { x = 1; } { y = 2; } z = x + y; }") == [
        Token(type="parenthesis", text="{", loc=L),
        Token(type="parenthesis", text="{", loc=L),
        Token(type="identifier", text="x", loc=L),
        Token(type="operator", text="=", loc=L),
        Token(type="int_literal", text="1", loc=L),
        Token(type="parenthesis", text=";", loc=L),
        Token(type="parenthesis", text="}", loc=L),
        Token(type="parenthesis", text="{", loc=L),
        Token(type="identifier", text="y", loc=L),
        Token(type="operator", text="=", loc=L),
        Token(type="int_literal", text="2", loc=L),
        Token(type="parenthesis", text=";", loc=L),
        Token(type="parenthesis", text="}", loc=L),
        Token(type="identifier", text="z", loc=L),
        Token(type="operator", text="=", loc=L),
        Token(type="identifier", text="x", loc=L),
        Token(type="operator", text="+", loc=L),
        Token(type="identifier", text="y", loc=L),
        Token(type="parenthesis", text=";", loc=L),
        Token(type="parenthesis", text="}", loc=L),
    ]
