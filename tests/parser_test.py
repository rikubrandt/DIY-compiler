
import unittest
from compiler.tokenizer import tokenize
from compiler.parser import parse
from compiler.types_compiler import Int, Bool, Unit
from compiler import ast_nodes


class TestParser(unittest.TestCase):

    def test_parser(self) -> None:
        assert parse(tokenize("1 + 2")) == ast_nodes.BinaryOp(
            left=ast_nodes.Literal(1),
            op="+",
            right=ast_nodes.Literal(2)
        )

    def test_parser2(self) -> None:
        assert parse(tokenize("1 + 2 + 3")) == ast_nodes.BinaryOp(
            left=ast_nodes.BinaryOp(
                left=ast_nodes.Literal(1),
                op="+",
                right=ast_nodes.Literal(2),
            ),
            op="+",
            right=ast_nodes.Literal(3),
        )

    def test_single_literal(self) -> None:
        self.assertEqual(
            parse(tokenize("42")),
            ast_nodes.Literal(42)
        )

    def test_identifier(self) -> None:
        self.assertEqual(
            parse(tokenize("x")),
            ast_nodes.Identifier("x")
        )

    def test_addition(self) -> None:
        self.assertEqual(
            parse(tokenize("1 + 2")),
            ast_nodes.BinaryOp(
                left=ast_nodes.Literal(1),
                op="+",
                right=ast_nodes.Literal(2)
            )
        )

    def test_subtraction(self) -> None:
        self.assertEqual(
            parse(tokenize("5 - 3")),
            ast_nodes.BinaryOp(
                left=ast_nodes.Literal(5),
                op="-",
                right=ast_nodes.Literal(3)
            )
        )

    def test_multiplication(self) -> None:
        self.assertEqual(
            parse(tokenize("2 * 3")),
            ast_nodes.BinaryOp(
                left=ast_nodes.Literal(2),
                op="*",
                right=ast_nodes.Literal(3)
            )
        )

    def test_division(self) -> None:
        self.assertEqual(
            parse(tokenize("8 / 4")),
            ast_nodes.BinaryOp(
                left=ast_nodes.Literal(8),
                op="/",
                right=ast_nodes.Literal(4)
            )
        )

    def test_operator_precedence(self) -> None:
        # Multiplication should be evaluated first.
        self.assertEqual(
            parse(tokenize("1 + 2 * 3")),
            ast_nodes.BinaryOp(
                left=ast_nodes.Literal(1),
                op="+",
                right=ast_nodes.BinaryOp(
                    left=ast_nodes.Literal(2),
                    op="*",
                    right=ast_nodes.Literal(3)
                )
            )
        )

    def test_parentheses(self) -> None:
        # Parentheses force addition to be evaluated first.
        self.assertEqual(
            parse(tokenize("(1 + 2) * 3")),
            ast_nodes.BinaryOp(
                left=ast_nodes.BinaryOp(
                    left=ast_nodes.Literal(1),
                    op="+",
                    right=ast_nodes.Literal(2)
                ),
                op="*",
                right=ast_nodes.Literal(3)
            )
        )

    def test_multiple_additions(self) -> None:
        # Should associate to the left:
        # ((1 + 2) + 3)
        self.assertEqual(
            parse(tokenize("1 + 2 + 3")),
            ast_nodes.BinaryOp(
                left=ast_nodes.BinaryOp(
                    left=ast_nodes.Literal(1),
                    op="+",
                    right=ast_nodes.Literal(2)
                ),
                op="+",
                right=ast_nodes.Literal(3)
            )
        )

    def test_nested_parentheses(self) -> None:
        # x + (y * (2 + 3))
        self.assertEqual(
            parse(tokenize("x + (y * (2 + 3))")),
            ast_nodes.BinaryOp(
                left=ast_nodes.Identifier("x"),
                op="+",
                right=ast_nodes.BinaryOp(
                    left=ast_nodes.Identifier("y"),
                    op="*",
                    right=ast_nodes.BinaryOp(
                        left=ast_nodes.Literal(2),
                        op="+",
                        right=ast_nodes.Literal(3)
                    )
                )
            )
        )

    def test_complex_expression(self) -> None:
        # (a + b) * (c - d) / e
        # Check that the AST correctly reflects operator precedence and associativity.
        self.assertEqual(
            parse(tokenize("(a + b) * (c - d) / e")),
            ast_nodes.BinaryOp(
                left=ast_nodes.BinaryOp(
                    left=ast_nodes.BinaryOp(
                        left=ast_nodes.Identifier("a"),
                        op="+",
                        right=ast_nodes.Identifier("b")
                    ),
                    op="*",
                    right=ast_nodes.BinaryOp(
                        left=ast_nodes.Identifier("c"),
                        op="-",
                        right=ast_nodes.Identifier("d")
                    )
                ),
                op="/",
                right=ast_nodes.Identifier("e")
            )
        )

    def test_if_expression(self) -> None:
        self.assertEqual(
            parse(tokenize("if a then b")),
            ast_nodes.IfExpression(
                if_side=ast_nodes.Identifier("a"),
                then=ast_nodes.Identifier("b")
            )
        )

    def test_if_else_expression(self) -> None:
        self.assertEqual(
            parse(tokenize("if a then b else c")),
            ast_nodes.IfExpression(
                if_side=ast_nodes.Identifier("a"),
                then=ast_nodes.Identifier("b"),
                else_side=ast_nodes.Identifier("c")
            )
        )

    def test_if_expression_with_addition_2(self) -> None:
        self.assertEqual(
            parse(tokenize("1 + if true then 2 else 3")),
            ast_nodes.BinaryOp(
                left=ast_nodes.Literal(1),
                op="+",
                right=ast_nodes.IfExpression(
                    if_side=ast_nodes.Literal(True),
                    then=ast_nodes.Literal(2),
                    else_side=ast_nodes.Literal(3)
                )
            )
        )

    def test_if_expression_with_addition(self) -> None:
        self.assertEqual(
            parse(tokenize("1 + if true then 2 else 3")),
            ast_nodes.BinaryOp(
                left=ast_nodes.Literal(1),
                op="+",
                right=ast_nodes.IfExpression(
                    if_side=ast_nodes.Literal(True),
                    then=ast_nodes.Literal(2),
                    else_side=ast_nodes.Literal(3)
                )
            )
        )

    def test_nested_if_expression(self) -> None:
        self.assertEqual(
            parse(tokenize("if a then if b then c else d else e")),
            ast_nodes.IfExpression(
                if_side=ast_nodes.Identifier("a"),
                then=ast_nodes.IfExpression(
                    if_side=ast_nodes.Identifier("b"),
                    then=ast_nodes.Identifier("c"),
                    else_side=ast_nodes.Identifier("d")
                ),
                else_side=ast_nodes.Identifier("e")
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

    def test_function(self) -> None:
        assert parse(tokenize("f(x, y)")) == ast_nodes.FunctionCall(
            name=ast_nodes.Identifier("f"),
            argument_list=[ast_nodes.Identifier(
                "x"), ast_nodes.Identifier("y")]
        )

    def test_function_with_expression_argument(self) -> None:
        assert parse(tokenize("f(x, x + y)")) == ast_nodes.FunctionCall(
            name=ast_nodes.Identifier("f"),
            argument_list=[
                ast_nodes.Identifier("x"),
                ast_nodes.BinaryOp(
                    left=ast_nodes.Identifier("x"),
                    op="+",
                    right=ast_nodes.Identifier("y")
                )
            ]
        )

    def test_function_call_missing_comma(self) -> None:
        with self.assertRaises(Exception) as context:
            parse(tokenize("f(x y)"))

        self.assertIn("unexpected token", str(context.exception))

    def test_arithmetic_operations(self) -> None:
        assert parse(tokenize("3 + 4 * 5")) == ast_nodes.BinaryOp(
            left=ast_nodes.Literal(3),
            op="+",
            right=ast_nodes.BinaryOp(
                left=ast_nodes.Literal(4),
                op="*",
                right=ast_nodes.Literal(5)
            )
        )

    def test_comparisons(self) -> None:
        assert parse(tokenize("a < b and b == c")) == ast_nodes.BinaryOp(
            left=ast_nodes.BinaryOp(
                left=ast_nodes.Identifier("a"),
                op="<",
                right=ast_nodes.Identifier("b")
            ),
            op="and",
            right=ast_nodes.BinaryOp(
                left=ast_nodes.Identifier("b"),
                op="==",
                right=ast_nodes.Identifier("c")
            )
        )

    def test_unary_not(self) -> None:
        assert parse(tokenize("not not x")) == ast_nodes.UnaryOp(
            op="not",
            operand=ast_nodes.UnaryOp(
                op="not",
                operand=ast_nodes.Identifier("x")
            )
        )

    def test_assignment_right_associative(self) -> None:
        assert parse(tokenize("a = b = c")) == ast_nodes.BinaryOp(
            left=ast_nodes.Identifier("a"),
            op="=",
            right=ast_nodes.BinaryOp(
                left=ast_nodes.Identifier("b"),
                op="=",
                right=ast_nodes.Identifier("c")
            )
        )

    def test_simple_block(self) -> None:
        assert parse(tokenize("{ x = 10; y = 20; x + y }")) == ast_nodes.Block(
            expressions=[
                ast_nodes.BinaryOp(ast_nodes.Identifier(
                    "x"), "=", ast_nodes.Literal(10)),
                ast_nodes.BinaryOp(ast_nodes.Identifier(
                    "y"), "=", ast_nodes.Literal(20))
            ],
            result=ast_nodes.BinaryOp(ast_nodes.Identifier(
                "x"), "+", ast_nodes.Identifier("y"))
        )

    def test_block_with_final_semicolon(self) -> None:
        assert parse(tokenize("{ x = 10; y = 20; }")) == ast_nodes.Block(
            expressions=[
                ast_nodes.BinaryOp(ast_nodes.Identifier(
                    "x"), "=", ast_nodes.Literal(10)),
                ast_nodes.BinaryOp(ast_nodes.Identifier(
                    "y"), "=", ast_nodes.Literal(20))
            ],
            result=ast_nodes.Literal(value=None)
        )

    def test_nested_blocks(self) -> None:
        assert parse(tokenize("{ x = { y = 2; y + 1 }; x * 3 }")) == ast_nodes.Block(
            expressions=[
                ast_nodes.BinaryOp(
                    ast_nodes.Identifier("x"),
                    "=",
                    ast_nodes.Block(
                        expressions=[
                            ast_nodes.BinaryOp(ast_nodes.Identifier("y"),
                                               "=", ast_nodes.Literal(2))
                        ],
                        result=ast_nodes.BinaryOp(
                            ast_nodes.Identifier("y"), "+", ast_nodes.Literal(1))
                    )
                )
            ],
            result=ast_nodes.BinaryOp(
                ast_nodes.Identifier("x"), "*", ast_nodes.Literal(3))
        )

    def test_block_with_if_expression(self) -> None:
        assert parse(tokenize("{ if a then b else c }")) == ast_nodes.Block(
            expressions=[],
            result=ast_nodes.IfExpression(
                if_side=ast_nodes.Identifier("a"),
                then=ast_nodes.Identifier("b"),
                else_side=ast_nodes.Identifier("c")
            )
        )

    def test_block_missing_semicolon_should_fail(self) -> None:
        with self.assertRaises(Exception):
            parse(tokenize("{ x = 10 y = 20 }"))

    def test_empty_block(self) -> None:
        assert parse(tokenize("{}")) == ast_nodes.Block(
            expressions=[], result=ast_nodes.Literal(value=None))

    def test_nested_blocks_no_extra_semicolon(self) -> None:
        assert parse(tokenize("{ { a } { b } }")) == ast_nodes.Block(
            expressions=[
                ast_nodes.Block(
                    expressions=[], result=ast_nodes.Identifier("a")),
            ],
            result=ast_nodes.Block(
                expressions=[], result=ast_nodes.Identifier("b"))
        )

    def test_missing_semicolon_should_fail(self) -> None:
        with self.assertRaises(Exception):
            parse(tokenize("{ a b }"))

    def test_if_then_block_with_no_semicolon(self) -> None:
        assert parse(tokenize("{ if true then { a } b }")) == ast_nodes.Block(
            expressions=[
                ast_nodes.IfExpression(
                    if_side=ast_nodes.Literal(True),
                    then=ast_nodes.Block(
                        expressions=[], result=ast_nodes.Identifier("a")),
                    else_side=None
                ),
            ],
            result=ast_nodes.Identifier("b")
        )

    def test_if_then_else_block_with_following_expr(self) -> None:
        assert parse(tokenize("{ if true then { a } else { b } c }")) == ast_nodes.Block(
            expressions=[
                ast_nodes.IfExpression(
                    if_side=ast_nodes.Literal(True),
                    then=ast_nodes.Block(
                        expressions=[], result=ast_nodes.Identifier("a")),
                    else_side=ast_nodes.Block(
                        expressions=[], result=ast_nodes.Identifier("b")),
                ),
            ],
            result=ast_nodes.Identifier("c")
        )

    def test_if_then_else_block_without_trailing_expr(self) -> None:
        assert parse(tokenize("{ if true then { a } else { b } }")) == ast_nodes.Block(
            expressions=[
            ],
            result=ast_nodes.IfExpression(
                if_side=ast_nodes.Literal(True),
                then=ast_nodes.Block(
                    expressions=[], result=ast_nodes.Identifier("a")),
                else_side=ast_nodes.Block(
                    expressions=[], result=ast_nodes.Identifier("b")),
            )
        )

    def test_variable_declaration_top_level(self) -> None:
        assert parse(tokenize("var x = 123")) == ast_nodes.VarDeclaration(
            name="x", value=ast_nodes.Literal(123),
        )

    def test_variable_declaration_in_block_2(self) -> None:
        assert parse(tokenize("{ var x = 123;}")) == ast_nodes.Block(
            expressions=[ast_nodes.VarDeclaration(
                name="x", value=ast_nodes.Literal(123))],
            result=ast_nodes.Literal(None)
        )

    def test_variable_declaration_in_block(self) -> None:
        assert parse(tokenize("{ var x = 123; x }")) == ast_nodes.Block(
            expressions=[ast_nodes.VarDeclaration(
                name="x", value=ast_nodes.Literal(123))],
            result=ast_nodes.Identifier("x")
        )

    def test_invalid_nested_declaration(self) -> None:
        with self.assertRaises(Exception):
            parse(tokenize("1 + var x = 123"))

    def test_unary_simple(self) -> None:
        assert parse(tokenize("-3")) == (
            ast_nodes.UnaryOp(
                op='-',
                type=Int,
                operand=ast_nodes.Literal(
                    value=3
                )
            )
        )

    def test_semicolon(self) -> None:
        assert parse(tokenize("print_int(5/4);")) == (
            ast_nodes.FunctionCall(
                type=Unit,
                name=ast_nodes.Identifier(type=Unit, name='print_int'),
                argument_list=[
                    ast_nodes.BinaryOp(
                        type=Unit,
                        left=ast_nodes.Literal(type=Int, value=5),
                        op='/',
                        right=ast_nodes.Literal(type=Unit, value=4)
                    )
                ]
            )
        )

    def test_semicolon_2(self) -> None:
        assert parse(tokenize("print_int(5/4)")) == (
            ast_nodes.FunctionCall(
                type=Unit,
                name=ast_nodes.Identifier(type=Unit, name='print_int'),
                argument_list=[
                    ast_nodes.BinaryOp(
                        type=Unit,
                        left=ast_nodes.Literal(type=Int, value=5),
                        op='/',
                        right=ast_nodes.Literal(type=Int, value=4)
                    )
                ]
            ))
