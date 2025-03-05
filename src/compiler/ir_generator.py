from dataclasses import dataclass
from typing import Dict, List
from compiler import ast_nodes
from compiler.ir import *
from compiler.types_compiler import Int, Bool, Unit, Type, FunType
from compiler.tokenizer import SourceLocation
from typing import Optional

# --- Simple Symbol Table for IR Variables ---


class SymTab:
    def __init__(self, parent=None):
        self.locals = {}
        self.parent = parent

    def add_local(self, name, value):
        self.locals[name] = value

    def lookup(self, name):
        if name in self.locals:
            return self.locals[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def require(self, name):
        value = self.lookup(name)
        if value is None:
            raise Exception(f"Undefined name: {name}")
        return value


# IR Generator implementation
def generate_ir(
    # 'root_types' parameter should map all global names
    # like 'print_int' and '+' to their types.
    root_types: dict[IRVar, Type],
    root_expr: ast_nodes.Expression
) -> list[Instruction]:
    var_types: dict[IRVar, Type] = root_types.copy()
    var_count = 0

    # 'var_unit' is used when an expression's type is 'Unit'.
    var_unit = IRVar('unit')
    var_types[var_unit] = Unit

    label_count = 0

    def new_var(t: Type) -> IRVar:
        # Create a new unique IR variable and
        # add it to var_types
        nonlocal var_count
        var_count += 1
        var = IRVar(f'x{var_count}')
        var_types[var] = t
        return var

    def new_label() -> Label:
        nonlocal label_count
        label_count += 1
        return Label(root_expr.location, f'L{label_count}')

    # We collect the IR instructions that we generate
    # into this list.
    ins: list[Instruction] = []

    # This function visits an AST node,
    # appends IR instructions to 'ins',
    # and returns the IR variable where
    # the emitted IR instructions put the result.
    #
    # It uses a symbol table to map local variables
    # (which may be shadowed) to unique IR variables.
    # The symbol table will be updated in the same way as
    # in the interpreter and type checker.
    def visit(st: SymTab, expr: ast_nodes.Expression) -> IRVar:
        loc = expr.location

        match expr:
            case ast_nodes.Literal():
                # Create an IR variable to hold the value,
                # and emit the correct instruction to
                # load the constant value.
                match expr.value:
                    case bool():
                        var = new_var(Bool)
                        ins.append(LoadBoolConst(
                            loc, expr.value, var))
                    case int():
                        var = new_var(Int)
                        ins.append(LoadIntConst(
                            loc, expr.value, var))
                    case None:
                        var = var_unit
                    case _:
                        raise Exception(
                            f"{loc}: unsupported literal: {type(expr.value)}")

                # Return the variable that holds
                # the loaded value.
                return var

            case ast_nodes.Identifier():
                # Look up the IR variable that corresponds to
                # the source code variable.
                return st.require(expr.name)

            case ast_nodes.BinaryOp():
                # Special handling for assignment
                if expr.op == "=":
                    if not isinstance(expr.left, ast_nodes.Identifier):
                        raise Exception(
                            f"{loc}: left-hand side of assignment must be an identifier")

                    # Get the variable to assign to
                    dest_var = st.require(expr.left.name)

                    # Evaluate the right-hand side
                    source_var = visit(st, expr.right)

                    # Copy the value
                    ins.append(Copy(loc, source_var, dest_var))

                    # Return the destination variable
                    return dest_var

                # Special handling for short-circuit operators
                elif expr.op == "and":
                    # Create a result variable
                    result_var = new_var(Bool)

                    # Evaluate the left operand
                    left_var = visit(st, expr.left)

                    # Create labels for short-circuit and end
                    label_short_circuit = new_label()
                    label_end = new_label()

                    # If left is false, short-circuit with false result
                    ins.append(Copy(loc, left_var, result_var))
                    ins.append(CondJump(loc, left_var, Label(
                        loc, ""), label_short_circuit))

                    # Otherwise, evaluate the right side and use its value
                    right_var = visit(st, expr.right)
                    ins.append(Copy(loc, right_var, result_var))
                    ins.append(Jump(loc, label_end))

                    # Short-circuit label (result is already false from left_var)
                    ins.append(label_short_circuit)

                    # End label
                    ins.append(label_end)

                    return result_var

                elif expr.op == "or":
                    result_var = new_var(Bool)

                    left_var = visit(st, expr.left)

                    label_short_circuit = new_label()
                    label_eval_right = new_label()
                    label_end = new_label()

                    ins.append(Copy(loc, left_var, result_var))
                    ins.append(
                        CondJump(loc, left_var, label_short_circuit, label_eval_right))

                    ins.append(label_eval_right)
                    right_var = visit(st, expr.right)
                    ins.append(Copy(loc, right_var, result_var))
                    ins.append(Jump(loc, label_end))

                    ins.append(label_short_circuit)
                    ins.append(label_end)

                    return result_var

                else:
                    var_op = st.require(expr.op)
                    var_left = visit(st, expr.left)
                    var_right = visit(st, expr.right)
                    var_result = new_var(expr.type)
                    ins.append(Call(
                        loc, var_op, [var_left, var_right], var_result))
                    return var_result

            case ast_nodes.UnaryOp():
                op_name = f"unary_{expr.op}"
                var_op = st.require(op_name)

                var_operand = visit(st, expr.operand)

                var_result = new_var(expr.type)

                ins.append(Call(loc, var_op, [var_operand], var_result))

                return var_result

            case ast_nodes.IfExpression():
                if expr.else_side is None:
                    # Create (but don't emit) some jump targets.
                    l_then = new_label()
                    l_end = new_label()

                    # Recursively emit instructions for
                    # evaluating the condition.
                    var_cond = visit(st, expr.if_side)
                    # Emit a conditional jump instruction
                    # to jump to 'l_then' or 'l_end',
                    # depending on the content of 'var_cond'.
                    ins.append(CondJump(loc, var_cond, l_then, l_end))

                    # Emit the label that marks the beginning of
                    # the "then" branch.
                    ins.append(l_then)
                    # Recursively emit instructions for the "then" branch.
                    visit(st, expr.then)

                    ins.append(l_end)

                    # An if-then expression doesn't return anything, so we
                    # return a special variable "unit".
                    return var_unit
                else:
                    # If-then-else case
                    l_then = new_label()
                    l_else = new_label()
                    l_end = new_label()

                    # Evaluate the condition
                    var_cond = visit(st, expr.if_side)
                    ins.append(CondJump(loc, var_cond, l_then, l_else))

                    # Create a result variable based on the type of the then branch
                    var_result = new_var(expr.type)

                    # Then branch
                    ins.append(l_then)
                    var_then = visit(st, expr.then)
                    ins.append(Copy(loc, var_then, var_result))
                    ins.append(Jump(loc, l_end))

                    # Else branch
                    ins.append(l_else)
                    var_else = visit(st, expr.else_side)
                    ins.append(Copy(loc, var_else, var_result))

                    # End of if-then-else
                    ins.append(l_end)

                    return var_result

            case ast_nodes.WhileLoop():
                # Create labels for the loop
                l_cond = new_label()
                l_body = new_label()
                l_end = new_label()

                # Jump to the condition evaluation
                ins.append(Jump(loc, l_cond))

                # Condition evaluation
                ins.append(l_cond)
                var_cond = visit(st, expr.condition)
                ins.append(CondJump(loc, var_cond, l_body, l_end))

                # Body execution
                ins.append(l_body)
                visit(st, expr.body)
                ins.append(Jump(loc, l_cond))

                # End of while loop
                ins.append(l_end)

                # While loops return Unit
                return var_unit

            case ast_nodes.Block():
                # Create a new symbol table for block scope
                block_st = SymTab(st)

                # Evaluate each expression in the block
                for e in expr.expressions:
                    visit(block_st, e)

                # Evaluate and return the result expression
                return visit(block_st, expr.result)

            case ast_nodes.VarDeclaration():
                # Evaluate the initial value
                var_init = visit(st, expr.value)

                # Create a new IR variable for this declaration
                var_decl = new_var(expr.type)

                # Add the variable to the symbol table
                st.add_local(expr.name, var_decl)

                # Copy the initial value
                ins.append(Copy(loc, var_init, var_decl))

                # Return the new variable
                return var_decl

            case ast_nodes.FunctionCall():
                # Get the function variable
                func_name = expr.name.name
                var_func = st.require(func_name)

                # Evaluate all arguments
                arg_vars = [visit(st, arg) for arg in expr.argument_list]

                # Create result variable
                var_result = new_var(expr.type)

                # Emit call instruction
                ins.append(Call(loc, var_func, arg_vars, var_result))

                return var_result

    # Convert 'root_types' into a SymTab
    # that maps all available global names to
    # IR variables of the same name.
    # In the Assembly generator stage, we will give
    # definitions for these globals. For now,
    # they just need to exist.
    root_symtab = SymTab(parent=None)
    for v in root_types.keys():
        root_symtab.add_local(v.name, v)

    # Start visiting the AST from the root.
    var_final_result = visit(root_symtab, root_expr)

    # Add a call to print the final result
    if var_types[var_final_result] == Int:
        var_print_int = root_symtab.require("print_int")
        var_print_result = new_var(Unit)
        ins.append(Call(root_expr.location, var_print_int,
                   [var_final_result], var_print_result))
    elif var_types[var_final_result] == Bool:
        var_print_bool = root_symtab.require("print_bool")
        var_print_result = new_var(Unit)
        ins.append(Call(root_expr.location, var_print_bool,
                   [var_final_result], var_print_result))

    return ins

# Example usage:


@staticmethod
def setup_root_types() -> dict[IRVar, Type]:
    """Set up root_types with built-in operations and functions."""
    root_types = {}

    # Binary operators
    for op in ["+", "-", "*", "/", "%", "<", "<=", ">", ">=", "==", "!="]:
        root_types[IRVar(op)] = FunType([Int, Int], Bool if op in [
            "<", "<=", ">", ">=", "==", "!="] else Int)

    # Logical operators
    for op in ["and", "or"]:
        root_types[IRVar(op)] = FunType([Bool, Bool], Bool)

    # Unary operators
    root_types[IRVar("unary_not")] = FunType([Bool], Bool)
    root_types[IRVar("unary_-")] = FunType([Int], Int)

    # Print functions
    root_types[IRVar("print_int")] = FunType([Int], Unit)
    root_types[IRVar("print_bool")] = FunType([Bool], Unit)

    return root_types
