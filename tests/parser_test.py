
import unittest
from compiler.tokenizer import tokenize
from compiler.parser import parse

from compiler import ast


class TestParser(unittest.TestCase):

    def test_parser(self) -> None:
        assert parse(tokenize("1 + 2")) == ast.BinaryOp(
            left=ast.Literal(1),
            op="+",
            right=ast.Literal(2)
        )

    def test_parser2(self) -> None:
        assert parse(tokenize("1 + 2 + 3")) == ast.BinaryOp(
            left=ast.BinaryOp(
                left=ast.Literal(1),
                op="+",
                right=ast.Literal(2),
            ),
            op="+",
            right=ast.Literal(3),
        )

    def test_single_literal(self) -> None:
            self.assertEqual(
                parse(tokenize("42")),
                ast.Literal(42)
            )

    def test_identifier(self) -> None:
        self.assertEqual(
            parse(tokenize("x")),
            ast.Identifier("x")
        )

    def test_addition(self) -> None:
        self.assertEqual(
            parse(tokenize("1 + 2")),
            ast.BinaryOp(
                left=ast.Literal(1),
                op="+",
                right=ast.Literal(2)
            )
        )

    def test_subtraction(self) -> None:
        self.assertEqual(
            parse(tokenize("5 - 3")),
            ast.BinaryOp(
                left=ast.Literal(5),
                op="-",
                right=ast.Literal(3)
            )
        )

    def test_multiplication(self) -> None:
        self.assertEqual(
            parse(tokenize("2 * 3")),
            ast.BinaryOp(
                left=ast.Literal(2),
                op="*",
                right=ast.Literal(3)
            )
        )

    def test_division(self) -> None:
        self.assertEqual(
            parse(tokenize("8 / 4")),
            ast.BinaryOp(
                left=ast.Literal(8),
                op="/",
                right=ast.Literal(4)
            )
        )

    def test_operator_precedence(self) -> None:
        # Multiplication should be evaluated first.
        self.assertEqual(
            parse(tokenize("1 + 2 * 3")),
            ast.BinaryOp(
                left=ast.Literal(1),
                op="+",
                right=ast.BinaryOp(
                    left=ast.Literal(2),
                    op="*",
                    right=ast.Literal(3)
                )
            )
        )

    def test_parentheses(self) -> None:
        # Parentheses force addition to be evaluated first.
        self.assertEqual(
            parse(tokenize("(1 + 2) * 3")),
            ast.BinaryOp(
                left=ast.BinaryOp(
                    left=ast.Literal(1),
                    op="+",
                    right=ast.Literal(2)
                ),
                op="*",
                right=ast.Literal(3)
            )
        )

    def test_multiple_additions(self) -> None:
        # Should associate to the left:
        # ((1 + 2) + 3)
        self.assertEqual(
            parse(tokenize("1 + 2 + 3")),
            ast.BinaryOp(
                left=ast.BinaryOp(
                    left=ast.Literal(1),
                    op="+",
                    right=ast.Literal(2)
                ),
                op="+",
                right=ast.Literal(3)
            )
        )

    def test_nested_parentheses(self) -> None:
        # x + (y * (2 + 3))
        self.assertEqual(
            parse(tokenize("x + (y * (2 + 3))")),
            ast.BinaryOp(
                left=ast.Identifier("x"),
                op="+",
                right=ast.BinaryOp(
                    left=ast.Identifier("y"),
                    op="*",
                    right=ast.BinaryOp(
                        left=ast.Literal(2),
                        op="+",
                        right=ast.Literal(3)
                    )
                )
            )
        )

    def test_complex_expression(self) -> None:
        # (a + b) * (c - d) / e
        # Check that the AST correctly reflects operator precedence and associativity.
        self.assertEqual(
            parse(tokenize("(a + b) * (c - d) / e")),
            ast.BinaryOp(
                left=ast.BinaryOp(
                    left=ast.BinaryOp(
                        left=ast.Identifier("a"),
                        op="+",
                        right=ast.Identifier("b")
                    ),
                    op="*",
                    right=ast.BinaryOp(
                        left=ast.Identifier("c"),
                        op="-",
                        right=ast.Identifier("d")
                    )
                ),
                op="/",
                right=ast.Identifier("e")
            )
        )

    def test_if_expression(self) -> None:
        self.assertEqual(
            parse(tokenize("if a then b")),
            ast.IfExpression(
                if_side=ast.Identifier("a"),
                then=ast.Identifier("b")
            )
        )

    def test_if_else_expression(self) -> None:
        self.assertEqual(
            parse(tokenize("if a then b else c")),
            ast.IfExpression(
                if_side=ast.Identifier("a"),
                then=ast.Identifier("b"),
                else_side=ast.Identifier("c")
            )
        )

    def test_if_expression_with_addition(self) -> None:
        self.assertEqual(
            parse(tokenize("1 + if true then 2 else 3")),
            ast.BinaryOp(
                left=ast.Literal(1),
                op="+",
                right=ast.IfExpression(
                    if_side=ast.Identifier("true"),
                    then=ast.Literal(2),
                    else_side=ast.Literal(3)
                )
            )
        )
    def test_if_expression_with_addition(self) -> None:
        self.assertEqual(
            parse(tokenize("1 + if true then 2 else 3")),
            ast.BinaryOp(
                left=ast.Literal(1),
                op="+",
                right=ast.IfExpression(
                    if_side=ast.Identifier("true"),
                    then=ast.Literal(2),
                    else_side=ast.Literal(3)
                )
            )
        )

    def test_nested_if_expression(self) -> None:
        self.assertEqual(
            parse(tokenize("if a then if b then c else d else e")),
            ast.IfExpression(
                if_side=ast.Identifier("a"),
                then=ast.IfExpression(
                    if_side=ast.Identifier("b"),
                    then=ast.Identifier("c"),
                    else_side=ast.Identifier("d")
                ),
                else_side=ast.Identifier("e")
            )
        )

    def test_raises_garbage(self) -> None:
        with self.assertRaises(Exception):
            parse(tokenize("a + b b"))

    def test_empty_input(self) -> None:
        self.assertEqual(
            parse(tokenize("")),
            None
        )

    def test_incorrect_formula(self) -> None:
        with self.assertRaises(Exception):
            parse(tokenize("(a + b b) * (c - d) / e"))

    def test_function(self):
        assert parse(tokenize("f(x, y)")) == ast.FunctionCall(
            name="f",
            argument_list=[ast.Identifier("x"), ast.Identifier("y")]
        )

    def test_function_with_expression_argument(self) -> None:
        assert parse(tokenize("f(x, x + y)")) == ast.FunctionCall(
            name="f",
            argument_list=[
                ast.Identifier("x"),  
                ast.BinaryOp(        
                    left=ast.Identifier("x"),
                    op="+",
                    right=ast.Identifier("y")
                )
            ]
        )

    def test_function_call_missing_comma(self) -> None:
        with self.assertRaises(Exception) as context:
            parse(tokenize("f(x y)")) 

        self.assertIn("unexpected token", str(context.exception))


    def test_arithmetic_operations(self):
        assert parse(tokenize("3 + 4 * 5")) == ast.BinaryOp(
            left=ast.Literal(3),
            op="+",
            right=ast.BinaryOp(
                left=ast.Literal(4),
                op="*",
                right=ast.Literal(5)
            )
        )

    def test_comparisons(self):
        assert parse(tokenize("a < b and b == c")) == ast.BinaryOp(
            left=ast.BinaryOp(
                left=ast.Identifier("a"),
                op="<",
                right=ast.Identifier("b")
            ),
            op="and",
            right=ast.BinaryOp(
                left=ast.Identifier("b"),
                op="==",
                right=ast.Identifier("c")
            )
        )

    def test_unary_not(self):
        assert parse(tokenize("not not x")) == ast.UnaryOp(
            op="not",
            operand=ast.UnaryOp(
                op="not",
                operand=ast.Identifier("x")
            )
        )

    def test_assignment_right_associative(self):
        assert parse(tokenize("a = b = c")) == ast.BinaryOp(
            left=ast.Identifier("a"),
            op="=",
            right=ast.BinaryOp(
                left=ast.Identifier("b"),
                op="=",
                right=ast.Identifier("c")
            )
        )
