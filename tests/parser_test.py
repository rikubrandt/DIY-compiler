
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

    def test_single_literal(self):
            self.assertEqual(
                parse(tokenize("42")),
                ast.Literal(42)
            )

    def test_identifier(self):
        self.assertEqual(
            parse(tokenize("x")),
            ast.Identifier("x")
        )

    def test_addition(self):
        self.assertEqual(
            parse(tokenize("1 + 2")),
            ast.BinaryOp(
                left=ast.Literal(1),
                op="+",
                right=ast.Literal(2)
            )
        )

    def test_subtraction(self):
        self.assertEqual(
            parse(tokenize("5 - 3")),
            ast.BinaryOp(
                left=ast.Literal(5),
                op="-",
                right=ast.Literal(3)
            )
        )

    def test_multiplication(self):
        self.assertEqual(
            parse(tokenize("2 * 3")),
            ast.BinaryOp(
                left=ast.Literal(2),
                op="*",
                right=ast.Literal(3)
            )
        )

    def test_division(self):
        self.assertEqual(
            parse(tokenize("8 / 4")),
            ast.BinaryOp(
                left=ast.Literal(8),
                op="/",
                right=ast.Literal(4)
            )
        )

    def test_operator_precedence(self):
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

    def test_parentheses(self):
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

    def test_multiple_additions(self):
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

    def test_nested_parentheses(self):
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

    def test_complex_expression(self):
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

