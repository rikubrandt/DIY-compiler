import unittest
from compiler.tokenizer import tokenize
from compiler.parser import parse
from compiler.type_checker import typecheck, TypeEnv
from compiler.types_compiler import Int, Bool, Unit, IntType
from compiler import ast_nodes


class TestTypeChecker(unittest.TestCase):
    def test_int_literal(self) -> None:
        tokens = tokenize("5")
        node = parse(tokens)

        if node is not None:
            typecheck(node)
            assert node.type == Int

    def test_bool_literal(self) -> None:
        tokens = tokenize("true")
        node = parse(tokens)

        if node is not None:
            typecheck(node)
            assert node.type == Bool

    def test_unit_literal(self) -> None:
        tokens = tokenize("{}")
        node = parse(tokens)

        if node is not None:
            typecheck(node)
            assert node.type == Unit

    def test_binary_op_addition(self) -> None:
        tokens = tokenize("5 + 3")
        node = parse(tokens)

        if node is not None:
            env = TypeEnv()
            env.set("+", ast_nodes.BinaryOp)
            typecheck(node, env)
            assert node.type == Int

    def test_binary_op_nested(self) -> None:
        tokens = tokenize("5 + 3 + 2")
        node = parse(tokens)

        if node is not None:
            env = TypeEnv()
            env.set("+", ast_nodes.BinaryOp)
            typecheck(node, env)

    def test_comparison_lt(self) -> None:
        tokens = tokenize("3 < 5")
        node = parse(tokens)

        if node is not None:
            env = TypeEnv()
            env.set("<", ast_nodes.BinaryOp)
            typecheck(node, env)
            assert node.type == Bool

    def test_comparison_gt(self) -> None:
        tokens = tokenize("8 > 5")
        node = parse(tokens)

        if node is not None:
            env = TypeEnv()
            env.set(">", ast_nodes.BinaryOp)
            typecheck(node, env)
            assert node.type == Bool

    def test_logical_and(self) -> None:
        tokens = tokenize("true and false")
        node = parse(tokens)

        if node is not None:
            env = TypeEnv()
            env.set("and", ast_nodes.BinaryOp)
            typecheck(node, env)
            assert node.type == Bool

    def test_var_declaration(self) -> None:
        tokens = tokenize("var x = 5")
        node = parse(tokens)

        if node is not None:
            typecheck(node)
            assert node.type == Int

    def test_var_declaration_with_type(self) -> None:
        tokens = tokenize("var x: Int = 5")
        node = parse(tokens)

        if node is not None:
            typecheck(node)
            assert node.type == Int

    def test_var_declaration_type_mismatch(self) -> None:
        tokens = tokenize("var x: Bool = 5")
        node = parse(tokens)

        if node is not None:
            with self.assertRaises(Exception):
                typecheck(node)

    def test_simple_unary(self) -> None:
        tokens = tokenize("-3")
        print(tokens)
        node = parse(tokens)
        print(node)
        typecheck(node)
        assert node.type == Int


if __name__ == "__main__":
    unittest.main()
