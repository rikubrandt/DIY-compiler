import unittest
from compiler.tokenizer import tokenize
from compiler.parser import parse
from compiler.type_checker import typecheck, TypeEnv
from compiler.types import Int, Bool, Unit, FunType
from compiler import ast

class TestTypeChecker(unittest.TestCase):

    def test_literal_int(self):
        src = "42"
        ast_expr = parse(tokenize(src))
        t = typecheck(ast_expr)
        self.assertEqual(t, Int)
        self.assertEqual(ast_expr.type, Int)

    def test_literal_bool(self):
        src = "true"
        ast_expr = parse(tokenize(src))
        t = typecheck(ast_expr)
        self.assertEqual(t, Bool)
        self.assertEqual(ast_expr.type, Bool)

    def test_addition(self):
        src = "1 + 2"
        ast_expr = parse(tokenize(src))
        t = typecheck(ast_expr)
        self.assertEqual(t, Int)
        self.assertEqual(ast_expr.type, Int)

    def test_if_expression(self):
        src = "if true then 1 else 2"
        ast_expr = parse(tokenize(src))
        t = typecheck(ast_expr)
        self.assertEqual(t, Int)
        self.assertEqual(ast_expr.type, Int)

    def test_if_expression_type_error(self):
        src = "if 1 then 1 else 2"  # condition is not Bool
        ast_expr = parse(tokenize(src))
        with self.assertRaises(Exception):
            typecheck(ast_expr)

    def test_while_loop(self):
        src = "while true do 1"
        ast_expr = parse(tokenize(src))
        t = typecheck(ast_expr)
        self.assertEqual(t, Unit)
        self.assertEqual(ast_expr.type, Unit)

    def test_block(self):
        src = "{ 1; 2 }"
        ast_expr = parse(tokenize(src))
        t = typecheck(ast_expr)
        # Block's type is that of its final expression (2), which is Int.
        self.assertEqual(t, Int)
        self.assertEqual(ast_expr.type, Int)

    def test_var_declaration_top_level(self):
        src = "var x = 123"
        ast_expr = parse(tokenize(src))
        t = typecheck(ast_expr)
        # For a var declaration, we infer the type from its initializer.
        self.assertEqual(t, Int)
        self.assertEqual(ast_expr.type, Int)

    def test_assignment_right_associative(self):
        # To typecheck "a = b = c", we need to prepopulate the environment.
        env = TypeEnv()
        env.set("a", Int)
        env.set("b", Int)
        env.set("c", Int)
        src = "a = b = c"
        ast_expr = parse(tokenize(src))
        t = typecheck(ast_expr, env)
        self.assertEqual(t, Int)
        self.assertEqual(ast_expr.type, Int)

    def test_function_call(self):
        # Set up a function f with type (Int) => Bool in the environment.
        env = TypeEnv()
        env.set("f", FunType([Int], Bool))
        src = "f(42)"
        ast_expr = parse(tokenize(src))
        t = typecheck(ast_expr, env)
        self.assertEqual(t, Bool)
        self.assertEqual(ast_expr.type, Bool)

    def test_function_call_wrong_arg(self):
        # f expects an Int but we pass a Bool.
        env = TypeEnv()
        env.set("f", FunType([Int], Bool))
        src = "f(true)"
        ast_expr = parse(tokenize(src))
        with self.assertRaises(Exception):
            typecheck(ast_expr, env)

if __name__ == '__main__':
    unittest.main()
