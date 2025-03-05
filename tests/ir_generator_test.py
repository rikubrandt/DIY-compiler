import unittest
from compiler.tokenizer import tokenize
from compiler.parser import parse
from compiler.type_checker import typecheck
import compiler.ir_generator
from compiler.ir_generator import setup_root_types, generate_ir
from compiler.ir import IRVar, LoadIntConst, LoadBoolConst, Call, Copy, Jump, CondJump, Label
import dataclasses


class TestIRGenerator(unittest.TestCase):

    def compile_to_ir(self, source_code):
        """Helper method to compile source code to IR instructions."""
        tokens = tokenize(source_code)
        ast = parse(tokens)
        typecheck(ast)
        root_types = setup_root_types()
        return generate_ir(root_types, ast)

    def assert_ir_matches(self, ir_instructions, expected_instructions):
        """Assert that generated IR matches expected output, ignoring locations."""
        # First, check if the length matches
        self.assertEqual(len(ir_instructions), len(expected_instructions),
                         f"IR instruction count mismatch: {len(ir_instructions)} vs {len(expected_instructions)}")

        for i, (actual, expected) in enumerate(zip(ir_instructions, expected_instructions)):
            # Compare instruction types
            self.assertEqual(type(actual), type(expected),
                             f"Instruction {i} type mismatch: {type(actual)} vs {type(expected)}")

            # Compare field values except location
            for field in [f.name for f in dataclasses.fields(expected) if f.name != 'location']:
                if hasattr(expected, field) and hasattr(actual, field):
                    expected_value = getattr(expected, field)
                    actual_value = getattr(actual, field)

                    # For lists, compare elements
                    if isinstance(expected_value, list):
                        self.assertEqual(len(actual_value), len(expected_value),
                                         f"List length mismatch in instruction {i}, field {field}")
                        for j, (act_item, exp_item) in enumerate(zip(actual_value, expected_value)):
                            self.assertEqual(str(act_item), str(exp_item),
                                             f"List item {j} mismatch in instruction {i}, field {field}")
                    else:
                        # Convert to string for easier comparison of IRVar objects
                        self.assertEqual(str(actual_value), str(expected_value),
                                         f"Value mismatch in instruction {i}, field {field}")

    def test_simple_literal(self):
        """Test IR generation for a simple integer literal."""
        ir = self.compile_to_ir("42")

        # Expected IR for "42":
        # 1. Load constant 42 to x1
        # 2. Call print_int with [x1] and store in x2
        expected = [
            LoadIntConst(None, 42, IRVar("x1")),
            Call(None, IRVar("print_int"), [IRVar("x1")], IRVar("x2"))
        ]

        self.assert_ir_matches(ir, expected)

    def test_boolean_literal(self):
        """Test IR generation for a boolean literal."""
        ir = self.compile_to_ir("true")

        expected = [
            LoadBoolConst(None, True, IRVar("x1")),
            Call(None, IRVar("print_bool"), [IRVar("x1")], IRVar("x2"))
        ]

        self.assert_ir_matches(ir, expected)

    def test_simple_binary_op(self):
        """Test IR generation for a simple binary operation."""
        ir = self.compile_to_ir("1 + 2")

        expected = [
            LoadIntConst(None, 1, IRVar("x1")),
            LoadIntConst(None, 2, IRVar("x2")),
            Call(None, IRVar("+"), [IRVar("x1"), IRVar("x2")], IRVar("x3")),
            Call(None, IRVar("print_int"), [IRVar("x3")], IRVar("x4"))
        ]

        self.assert_ir_matches(ir, expected)

    def test_complex_expression(self):
        """Test IR generation for a more complex expression."""
        ir = self.compile_to_ir("1 + 2 * 3")

        expected = [
            LoadIntConst(None, 1, IRVar("x1")),
            LoadIntConst(None, 2, IRVar("x2")),
            LoadIntConst(None, 3, IRVar("x3")),
            Call(None, IRVar("*"), [IRVar("x2"), IRVar("x3")], IRVar("x4")),
            Call(None, IRVar("+"), [IRVar("x1"), IRVar("x4")], IRVar("x5")),
            Call(None, IRVar("print_int"), [IRVar("x5")], IRVar("x6"))
        ]

        self.assert_ir_matches(ir, expected)

    def test_variable_declaration(self):
        """Test IR generation for variable declaration."""
        ir = self.compile_to_ir("var x = 5")

        expected = [
            LoadIntConst(None, 5, IRVar("x1")),
            Copy(None, IRVar("x1"), IRVar("x2")),
            Call(None, IRVar("print_int"), [IRVar("x2")], IRVar("x3"))
        ]

        self.assert_ir_matches(ir, expected)

    def test_variable_assignment(self):
        """Test IR generation for variable assignment."""
        ir = self.compile_to_ir("{ var x = 5; x = 10 }")

        expected = [
            LoadIntConst(None, 5, IRVar("x1")),
            Copy(None, IRVar("x1"), IRVar("x2")),
            LoadIntConst(None, 10, IRVar("x3")),
            Copy(None, IRVar("x3"), IRVar("x2")),
            Call(None, IRVar("print_int"), [IRVar("x2")], IRVar("x4"))
        ]

        self.assert_ir_matches(ir, expected)

    def test_if_then(self):
        """Test IR generation for if-then expression."""
        ir = self.compile_to_ir("if true then 42")

        # We can't predict label names exactly, so check the structure
        self.assertEqual(len(ir), 5)
        self.assertIsInstance(ir[0], LoadBoolConst)
        self.assertIsInstance(ir[1], CondJump)
        self.assertIsInstance(ir[2], Label)
        self.assertIsInstance(ir[3], LoadIntConst)
        self.assertIsInstance(ir[4], Label)

    def test_if_then_else(self):
        """Test IR generation for if-then-else expression."""
        ir = self.compile_to_ir("if true then 42 else 24")
        print("IR: \n")
        print(ir)
        instructions_to_check = {
            LoadBoolConst: 1,
            CondJump: 1,
            Label: 3,  # then, else, end labels
            LoadIntConst: 2,  # 42 and 24
            Copy: 2,
            Jump: 1,
            Call: 1  # print_int
        }

        for instr_type, count in instructions_to_check.items():
            actual_count = sum(1 for ins in ir if isinstance(ins, instr_type))
            self.assertEqual(actual_count, count,
                             f"Expected {count} instructions of type {instr_type.__name__}, found {actual_count}")

    def test_while_loop(self) -> None:
        """Test IR generation for while loop."""
        ir = self.compile_to_ir("{ var i = 0; while i < 5 do i = i + 1 }")

        # Check the structure of the while loop
        # We should have:
        # - Variable declaration for i
        # - Jump to condition check
        # - Label for condition
        # - Code for i < 5
        # - CondJump
        # - Label for body
        # - Code for i = i + 1
        # - Jump back to condition
        # - Label for end

        # First find the Jump instruction which should be after the var declaration
        jump_index = next((i for i, ins in enumerate(ir)
                          if isinstance(ins, Jump)), -1)
        self.assertGreater(jump_index, 0, "Jump instruction not found")

        # Check that we have the expected labels
        label_indices = [i for i, ins in enumerate(
            ir) if isinstance(ins, Label)]
        self.assertEqual(len(label_indices), 3,
                         "Expected 3 labels for while loop")


if __name__ == '__main__':
    unittest.main()
