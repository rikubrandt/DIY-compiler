from compiler.tokenizer import tokenize, Token, L

def test_identifier():
    assert tokenize("hello") == [
        Token(type="identifier", text="hello", loc=L)
    ]

def test_whitespace_and_identifier():
    assert tokenize("     \n       hello          ") == [
        Token(type="identifier", text="hello", loc=L)
    ]

def test_simple_expression():
    assert tokenize("3+5") == [
        Token(type="int_literal", text="3", loc=L),
        Token(type="operator", text="+", loc=L),
        Token(type="int_literal", text="5", loc=L)
    ]

def test_expression_with_unary_operator():
    assert tokenize("3 + -5") == [
        Token(type="int_literal", text="3", loc=L),
        Token(type="operator", text="+", loc=L),
        Token(type="operator", text="-", loc=L),
        Token(type="int_literal", text="5", loc=L)
    ]

def test_parentheses_expression():
    assert tokenize("(3+5)") == [
        Token(type="parenthesis", text="(", loc=L),
        Token(type="int_literal", text="3", loc=L),
        Token(type="operator", text="+", loc=L),
        Token(type="int_literal", text="5", loc=L),
        Token(type="parenthesis", text=")", loc=L),
    ]


def test_operators():
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



def test_comment():
    assert tokenize("// Comment") == [
    ]
    assert tokenize("# Comment") == [
    ]

def test_complex_expressions():
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
