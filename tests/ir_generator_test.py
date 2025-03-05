import unittest
from compiler.tokenizer import tokenize
from compiler.parser import parse
from compiler.type_checker import typecheck
from compiler.ir_generator import generate_ir, _var_counter, _label_counter
from compiler.ir import IRVar
from compiler.types_compiler import Int, Bool, Unit, FunType
from compiler.type_checker import TypeEnv


def reset_ir_counters():

    import compiler.ir_generator as irgen
    irgen._var_counter = 0
    irgen._label_counter = 0


class TestIRGenerator(unittest.TestCase):

    def setUp(self) -> None:
        reset_ir_counters()

        self.root_types = {
            IRVar("+"): FunType([Int, Int], Int),
            IRVar("<"): FunType([Int, Int], Bool),
            IRVar("unary_-"): FunType([Int], Int),

        }

    def test_ir_addition(self) -> None:
        src = "1 + 2"

        tokens = tokenize(src)
        ast_expr = parse(tokens)
        typecheck(ast_expr)  # This populates the ast_expr.type field.

        instructions = generate_ir(self.root_types, ast_expr)

        ir_output = "\n".join(str(instr) for instr in instructions)

        expected = (
            "LoadIntConst(1, x1)\n"
            "LoadIntConst(2, x2)\n"
            "Call(+, [x1, x2], x3)"
        )
        self.assertEqual(ir_output, expected)

    def test_ir_if_expression(self) -> None:
        # Test IR generation for: if true then 1 else 2
        src = "if true then 1 else 2"
        tokens = tokenize(src)
        ast_expr = parse(tokens)
        typecheck(ast_expr)
        instructions = generate_ir(self.root_types, ast_expr)
        ir_output = "\n".join(str(instr) for instr in instructions)
        expected = (
            "LoadBoolConst(True, x1)\n"
            "CondJump(x1, Label(L1), Label(L2))\n"
            "Label(L1)\n"
            "LoadIntConst(1, x2)\n"
            "Jump(Label(L3))\n"
            "Label(L2)\n"
            "LoadIntConst(2, x3)\n"
            "Jump(Label(L3))\n"
            "Label(L3)"
        )
        self.assertEqual(ir_output, expected)

    def test_ir_while_loop(self) -> None:
        src = "while a < b do f()"
        tokens = tokenize(src)
        ast_expr = parse(tokens)

        from compiler.type_checker import TypeEnv
        env = TypeEnv()
        env.set("a", Int)
        env.set("b", Int)
        from compiler.types_compiler import FunType
        env.set("f", FunType([], Unit))
        typecheck(ast_expr, env)

        root_types = {
            IRVar("a"): Int,
            IRVar("b"): Int,
            IRVar("<"): Bool,
            IRVar("f"): FunType([], Unit)
        }

        instructions = generate_ir(root_types, ast_expr)
        ir_output = "\n".join(str(instr) for instr in instructions)

        self.assertIn("CondJump", ir_output)
        self.assertIn("Jump", ir_output)
        self.assertIn("Call(f, [],", ir_output)

    def test_ir_literal_int(self) -> None:

        src = "42"
        tokens = tokenize(src)
        ast_expr = parse(tokens)
        typecheck(ast_expr)

        root_types = {}
        instructions = generate_ir(root_types, ast_expr)
        ir_output = "\n".join(str(instr) for instr in instructions)

        assert "LoadIntConst(42," in ir_output, f"IR output was:\n{ir_output}"

    def test_ir_literal_bool(self) -> None:

        src = "true"
        tokens = tokenize(src)
        ast_expr = parse(tokens)
        typecheck(ast_expr)
        root_types = {}
        instructions = generate_ir(root_types, ast_expr)
        ir_output = "\n".join(str(instr) for instr in instructions)

        assert "LoadBoolConst(True," in ir_output, f"IR output was:\n{ir_output}"

    def test_ir_binary_op(self) -> None:
        # Test IR for a simple binary operation: 1 + 2
        src = "1 + 2"
        tokens = tokenize(src)
        ast_expr = parse(tokens)
        typecheck(ast_expr)

        root_types = {IRVar("+"): Int}
        instructions = generate_ir(root_types, ast_expr)
        ir_output = "\n".join(str(instr) for instr in instructions)

        assert "LoadIntConst(1," in ir_output, f"IR output was:\n{ir_output}"
        assert "LoadIntConst(2," in ir_output, f"IR output was:\n{ir_output}"
        assert "Call(+, " in ir_output, f"IR output was:\n{ir_output}"

    def test_ir_function_call(self) -> None:
        src = "f(1)"
        tokens = tokenize(src)
        ast_expr = parse(tokens)

        from compiler.type_checker import TypeEnv
        env = TypeEnv()

        env.set("f", FunType([Int], Int))
        typecheck(ast_expr, env)

        root_types = {IRVar("f"): FunType([Int], Int)}
        instructions = generate_ir(root_types, ast_expr)
        ir_output = "\n".join(str(instr) for instr in instructions)
        self.assertIn("LoadIntConst(1,", ir_output)
        self.assertIn("Call(f, ", ir_output)

    def test_ir_block(self) -> None:
        src = "{ 1; 2 }"
        tokens = tokenize(src)
        ast_expr = parse(tokens)
        typecheck(ast_expr)
        root_types = {}
        instructions = generate_ir(root_types, ast_expr)
        ir_output = "\n".join(str(instr) for instr in instructions)
        assert "LoadIntConst(1," in ir_output, f"IR output was:\n{ir_output}"
        assert "LoadIntConst(2," in ir_output, f"IR output was:\n{ir_output}"


if __name__ == '__main__':
    unittest.main()
