from dataclasses import dataclass
from typing import Dict, List
from compiler import ast_nodes
from compiler.ir import *
from compiler.types_compiler import Int, Bool, Unit, Type, FunType
from compiler.tokenizer import SourceLocation
from typing import Optional


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


def convert_str_to_type(type_str: str) -> Type:
    """Convert a type string to a Type object"""
    if type_str == "Int":
        return Int
    elif type_str == "Bool":
        return Bool
    elif type_str == "Unit":
        return Unit
    else:
        raise Exception(f"Unknown type: {type_str}")


def generate_ir(
    root_types: dict[IRVar, Type],
    root_module: ast_nodes.Module
) -> dict[str, list[Instruction]]:
    var_types: dict[IRVar, Type] = root_types.copy()
    
    function_types: dict[str, FunType] = {}

    functions_ir: dict[str, list[Instruction]] = {}
    
    def new_var(t: Type, prefix="x") -> IRVar:
        nonlocal var_count
        var_count += 1
        var = IRVar(f'{prefix}{var_count}')
        var_types[var] = t
        return var
    
    def new_label(loc=None) -> Label:
        nonlocal label_count
        label_count += 1
        if loc is None and root_module.expressions:
            loc = root_module.expressions[0].location
        return Label(loc or SourceLocation(), f'L{label_count}')
    
    def generate_function_ir(function_name: str, function_def: Optional[ast_nodes.FunctionDefinition] = None) -> list[Instruction]:
        nonlocal var_count, label_count, var_unit, loop_end_labels, loop_cond_labels, ins
        
        var_count = 0
        label_count = 0
        var_unit = IRVar('unit')
        var_types[var_unit] = Unit
        loop_end_labels = []
        loop_cond_labels = []
        ins = []
        
        function_symtab = SymTab(parent=None)
        
        for v in root_types.keys():
            function_symtab.add_local(v.name, v)
        
        for name, ir_var in function_vars.items():
            function_symtab.add_local(name, ir_var)
        
        if function_def:
            # Create parameters
            parameters = []
            for param in function_def.parameters:
                param_type = convert_str_to_type(param.param_type)
                param_var = new_var(param_type, prefix="p")
                parameters.append(param_var)
                function_symtab.add_local(param.name, param_var)
            
            return_type = convert_str_to_type(function_def.return_type)

            ret_var = new_var(return_type, prefix="ret")
            function_symtab.add_local("return", ret_var)

            result_var = visit(function_symtab, function_def.body)
                
        else:
            # This is the "main" function with top-level expressions
            if not root_module.expressions:
                return ins  # Return empty instructions list if no expressions
            
            # Handle multiple expressions by processing them in sequence
            var_final_result = None
            for expr in root_module.expressions:
                var_final_result = visit(function_symtab, expr)
            
            # Only print the final result in main if it has a printable type
            if var_final_result and var_types[var_final_result] == Int:
                var_print_int = function_symtab.require("print_int")
                var_print_result = new_var(Unit)
                ins.append(Call(root_module.location, var_print_int,
                              [var_final_result], var_print_result))
            elif var_final_result and var_types[var_final_result] == Bool:
                var_print_bool = function_symtab.require("print_bool")
                var_print_result = new_var(Unit)
                ins.append(Call(root_module.location, var_print_bool,
                              [var_final_result], var_print_result))
        
        return ins
    
    def visit(st: SymTab, expr: ast_nodes.Expression) -> IRVar:
        loc = expr.location

        match expr:
            case ast_nodes.Literal():
                # load the constant value.
                if expr.type == Unit:
                    return var_unit
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

                return var

            case ast_nodes.Identifier():
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

                    ins.append(Copy(loc, source_var, dest_var))

                    return dest_var

                elif expr.op == "and":
                    result_var = new_var(Bool)

                    left_var = visit(st, expr.left)

                    label_eval_right = new_label(loc)
                    label_short_circuit = new_label(loc)
                    label_end = new_label(loc)

                    ins.append(Copy(loc, left_var, result_var))
                    ins.append(
                        CondJump(loc, left_var, label_eval_right, label_short_circuit))

                    ins.append(label_eval_right)
                    right_var = visit(st, expr.right)
                    ins.append(Copy(loc, right_var, result_var))
                    ins.append(Jump(loc, label_end))

                    # Short-circuit branch: left was false; result remains false.
                    ins.append(label_short_circuit)

                    # End label for both branches.
                    ins.append(label_end)

                    return result_var

                elif expr.op == "or":
                    result_var = new_var(Bool)

                    left_var = visit(st, expr.left)

                    label_short_circuit = new_label(loc)
                    label_eval_right = new_label(loc)
                    label_end = new_label(loc)

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
                    l_then = new_label(loc)
                    l_end = new_label(loc)

                    var_cond = visit(st, expr.if_side)
                    ins.append(CondJump(loc, var_cond, l_then, l_end))

                    ins.append(l_then)
                    visit(st, expr.then)

                    ins.append(l_end)

                    return var_unit
                else:
                    l_then = new_label(loc)
                    l_else = new_label(loc)
                    l_end = new_label(loc)

                    # Evaluate the condition
                    var_cond = visit(st, expr.if_side)
                    ins.append(CondJump(loc, var_cond, l_then, l_else))

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
            case ast_nodes.BreakStatement():
                if not loop_end_labels:
                    raise Exception(f"Break statement outside of loop.")
                # Break out of last loop
                ins.append(Jump(loc, loop_end_labels[-1]))
                return var_unit
            case ast_nodes.ContinueStatement():
                if not loop_cond_labels:
                    raise Exception(f"Continue statement outside of loop.")
                ins.append(Jump(loc, loop_cond_labels[-1]))
                return var_unit
        
            case ast_nodes.WhileLoop():
                l_cond = new_label(loc)
                l_body = new_label(loc)
                l_end = new_label(loc)

                loop_cond_labels.append(l_cond)
                loop_end_labels.append(l_end)

                ins.append(Jump(loc, l_cond))

                ins.append(l_cond)
                var_cond = visit(st, expr.condition)
                ins.append(CondJump(loc, var_cond, l_body, l_end))

                # Body execution
                ins.append(l_body)
                visit(st, expr.body)
                ins.append(Jump(loc, l_cond))

                # End of while loop
                ins.append(l_end)


                # Pop when done
                loop_end_labels.pop()
                loop_cond_labels.pop()

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
                if expr.name in st.locals:
                    raise Exception(f"{loc}: variable '{expr.name}' already declared in this scope")

                # Create a new IR variable for this declaration
                var_decl = new_var(expr.type)
            
                st.add_local(expr.name, var_decl)

                ins.append(Copy(loc, var_init, var_decl))

                return var_unit

            case ast_nodes.FunctionCall():
                func_name = expr.name.name
                var_func = st.require(func_name)

                # Evaluate all arguments
                arg_vars = [visit(st, arg) for arg in expr.argument_list]

                # Create result variable
                var_result = new_var(expr.type)

                # Emit call instruction
                ins.append(Call(loc, var_func, arg_vars, var_result))

                return var_result
            case ast_nodes.ReturnStatement():
                ret_var = st.require("return")
                
                if expr.value is not None:
                    val_var = visit(st, expr.value)
                    
                    ins.append(Copy(loc, val_var, ret_var))
                else:
                    # Return without value (Unit)
                    ins.append(Copy(loc, var_unit, ret_var))
                
                return var_unit
    
    # First pass: Process function types and create function variables
    function_vars = {}
    
    for func_def in root_module.function_definitions:
        param_types = [convert_str_to_type(param.param_type) for param in func_def.parameters]
        return_type = convert_str_to_type(func_def.return_type)
        func_type = FunType(param_types, return_type)
        function_types[func_def.name] = func_type
        func_var = IRVar(func_def.name)
        var_types[func_var] = func_type
        function_vars[func_def.name] = func_var
    
    # Second pass: Generate IR for each function
    for func_def in root_module.function_definitions:
        # Init variables for this function
        var_count = 0
        label_count = 0
        var_unit = IRVar('unit')
        var_types[var_unit] = Unit
        loop_end_labels = []
        loop_cond_labels = []
        ins = []
        
        function_ir = generate_function_ir(func_def.name, func_def)
        
        # Store function IR
        functions_ir[func_def.name] = function_ir
    
    # Finally, process main func (top-level expressions)
    functions_ir["main"] = generate_function_ir("main")
    
    return functions_ir


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
    # Read functions
    root_types[IRVar("read_int")] = FunType([], Int)

    return root_types