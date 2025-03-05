from dataclasses import dataclass
from typing import Dict, List
from compiler import ast_nodes
from compiler.ir import *
from compiler.types_compiler import Int, Bool, Unit, Type
from compiler.tokenizer import SourceLocation
from typing import Optional

# --- Simple Symbol Table for IR Variables ---


class SymTab:
    def __init__(self, parent: Optional["SymTab"] = None):
        self.parent = parent
        self.table: Dict[str, IRVar] = {}

    def add(self, name: str, var: IRVar) -> None:
        self.table[name] = var

    def lookup(self, name: str) -> IRVar:
        if name in self.table:
            return self.table[name]
        elif self.parent:
            return self.parent.lookup(name)
        else:
            raise Exception(f"Undefined variable: {name}")

    def create_child(self) -> "SymTab":
        return SymTab(self)


# --- Global Counters and Fresh Name Generators ---
_var_counter = 0
_label_counter = 0


def new_var(t: Type, name: Optional[str] = None) -> IRVar:
    global _var_counter
    if name is not None:
        return IRVar(name)
    _var_counter += 1
    return IRVar(f"x{_var_counter}")


def new_label(loc: Optional[SourceLocation], name: Optional[str] = None) -> Label:
    global _label_counter
    if name is not None:
        return Label(name=name, location=loc)
    _label_counter += 1
    return Label(name=f"L{_label_counter}", location=loc)

# --- IR Generator ---


def generate_ir(
    root_types: Dict[IRVar, Type],
    root_expr: ast_nodes.Expression
) -> List[Instruction]:
    # Copy the global types mapping.
    var_types: Dict[IRVar, Type] = dict(root_types)
    # Create a special variable for unit.
    var_unit = IRVar("unit")
    var_types[var_unit] = Unit

    instructions: List[Instruction] = []

    # Build a global symbol table mapping global names to IRVars.
    global_symtab = SymTab()
    for v in root_types.keys():
        global_symtab.add(v.name, v)

    # The core recursive function to traverse the AST and emit IR.
    def visit(st: SymTab, expr: ast_nodes.Expression) -> IRVar:
        loc = expr.location
        if isinstance(expr, ast_nodes.Literal):
            if isinstance(expr.value, bool):
                var = new_var(Bool)  # first bool literal becomes x1
                instructions.append(LoadBoolConst(
                    location=loc, value=expr.value, dest=var))
                return var
            elif isinstance(expr.value, int):
                # subsequent int literals become x2, x3, etc.
                var = new_var(Int)
                instructions.append(LoadIntConst(
                    location=loc, value=expr.value, dest=var))
                return var
            elif expr.value is None:
                return var_unit
            else:
                raise Exception(
                    f"{loc}: Unsupported literal type: {type(expr.value)}")
        elif isinstance(expr, ast_nodes.Identifier):
            return st.lookup(expr.name)
        elif isinstance(expr, ast_nodes.BinaryOp):
            if expr.op == "=":
                if not isinstance(expr.left, ast_nodes.Identifier):
                    raise Exception(
                        f"{loc}: Left-hand side of assignment must be an identifier.")
                var_right = visit(st, expr.right)
                var_left = st.lookup(expr.left.name)
                instructions.append(
                    Copy(location=loc, source=var_right, dest=var_left))
                return var_left
            else:
                var_left = visit(st, expr.left)
                var_right = visit(st, expr.right)
                op_var = st.lookup(expr.op)
                result_var = new_var(expr.type)
                instructions.append(Call(location=loc, fun=op_var, args=[
                                    var_left, var_right], dest=result_var))
                return result_var
        elif isinstance(expr, ast_nodes.UnaryOp):
            var_operand = visit(st, expr.operand)
            op_var = st.lookup(f"unary_{expr.op}")
            result_var = new_var(expr.type)
            instructions.append(Call(location=loc, fun=op_var, args=[
                                var_operand], dest=result_var))
            return result_var
        elif isinstance(expr, ast_nodes.IfExpression):
            # Generate labels (without forced names so that they are L1, L2, L3).
            var_cond = visit(st, expr.if_side)
            then_label = new_label(loc)    # becomes L1
            else_label = new_label(loc)    # becomes L2
            if_end_label = new_label(loc)   # becomes L3
            instructions.append(CondJump(
                location=loc, cond=var_cond, then_label=then_label, else_label=else_label))
            # Then branch:
            instructions.append(then_label)
            # the then branch should emit, e.g., "LoadIntConst(1, x2)"
            visit(st, expr.then)
            instructions.append(Jump(location=loc, label=if_end_label))
            # Else branch:
            instructions.append(else_label)
            if expr.else_side is not None:
                visit(st, expr.else_side)  # should emit "LoadIntConst(2, x3)"
            else:
                # If no else branch, use unit.
                instructions.append(LoadIntConst(
                    location=loc, value=0, dest=var_unit))
            instructions.append(Jump(location=loc, label=if_end_label))
            instructions.append(if_end_label)
            # For simplicity, we do not merge the branch values.
            return var_unit
        elif isinstance(expr, ast_nodes.FunctionCall):
            var_fun = visit(st, expr.name)
            arg_vars = [visit(st, arg) for arg in expr.argument_list]
            result_var = new_var(expr.type)
            instructions.append(
                Call(location=loc, fun=var_fun, args=arg_vars, dest=result_var))
            return result_var
        elif isinstance(expr, ast_nodes.Block):
            child = st.create_child()
            for e in expr.expressions:
                visit(child, e)
            return visit(child, expr.result)
        elif isinstance(expr, ast_nodes.VarDeclaration):
            var_init = visit(st, expr.value)
            newv = new_var(expr.type)
            st.add(expr.name, newv)
            instructions.append(Copy(location=loc, source=var_init, dest=newv))
            return newv
        elif isinstance(expr, ast_nodes.WhileLoop):
            # For a while loop, emit:
            #   Jump(cond_label)
            #   L_then:
            #     <body>
            #   cond_label:
            #     <evaluate condition>
            #     CondJump(condition, L_then, L_end)
            #   L_end:
            start_label = new_label(loc)  # L?
            cond_label = new_label(loc)   # L?
            end_label = new_label(loc)    # L?
            instructions.append(Jump(location=loc, label=cond_label))
            instructions.append(start_label)
            visit(st, expr.body)
            instructions.append(cond_label)
            var_cond = visit(st, expr.condition)
            instructions.append(CondJump(
                location=loc, cond=var_cond, then_label=start_label, else_label=end_label))
            instructions.append(end_label)
            return var_unit
        else:
            raise Exception(f"{loc}: IR generation not implemented for {expr}")

    visit(global_symtab, root_expr)
    return instructions


# reset counters for testing
def reset_ir_counters() -> None:
    global _var_counter, _label_counter
    _var_counter = 0
    _label_counter = 0
