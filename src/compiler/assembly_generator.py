from typing import List, Dict, Set
from compiler import ir
from compiler.intrinsics import all_intrinsics, IntrinsicArgs


class Locals:
    """Knows the memory location of every local variable."""
    _var_to_location: Dict[ir.IRVar, str]
    _stack_used: int

    def __init__(self, variables: List[ir.IRVar]) -> None:
        """Initialize with the set of all variables used in the program."""
        self._var_to_location = {}

        # Each variable needs 8 bytes of stack space (64 bits)
        offset = 8
        for var in variables:
            # Stack grows downwards, so we use negative offsets from %rbp
            self._var_to_location[var] = f"-{offset}(%rbp)"
            offset += 8

        # Round up to a multiple of 16 for stack alignment
        self._stack_used = ((offset - 1) // 16 + 1) * 16

    def get_ref(self, v: ir.IRVar) -> str:
        """Returns an Assembly reference like `-24(%rbp)`
        for the memory location that stores the given variable"""
        return self._var_to_location[v]

    def stack_used(self) -> int:
        """Returns the number of bytes of stack space needed for the local variables."""
        return self._stack_used


def get_all_ir_variables(instructions: List[ir.Instruction]) -> List[ir.IRVar]:
    """Find all IR variables used in the given instructions."""
    variables: Set[ir.IRVar] = set()

    for insn in instructions:
        match insn:
            case ir.LoadIntConst() | ir.LoadBoolConst():
                variables.add(insn.dest)
            case ir.Copy():
                variables.add(insn.source)
                variables.add(insn.dest)
            case ir.Call():
                variables.add(insn.fun)
                variables.update(insn.args)
                variables.add(insn.dest)
            case ir.CondJump():
                variables.add(insn.cond)

    return list(variables)


def generate_function_assembly(function_name: str, instructions: List[ir.Instruction], label_prefix) -> List[str]:
    """Generate assembly code for single func."""
    lines = []

    def emit(line: str) -> None:
        lines.append(line)

    # Get all variables used in the function
    variables = get_all_ir_variables(instructions)
    locals = Locals(variables=variables)

    # Identify parameter variables (assuming they follow your naming convention with 'p' prefix)
    parameter_vars = sorted([v for v in variables if v.name.startswith('p')], 
                          key=lambda v: int(v.name[1:]) if v.name[1:].isdigit() else 0)
    
    # Find return variable (if any)
    return_vars = [v for v in variables if v.name.startswith('ret')]
    return_var = return_vars[0] if return_vars else None
    
    # Emit function header
    if function_name == "main":
        emit(".global main")
        emit(".type main, @function")
        emit("")
        emit(f"{function_name}:")
    else:
        emit(f".global {function_name}")
        emit(f".type {function_name}, @function")
        emit("")
        emit(f"{function_name}:")

    # Function prologue
    emit("    pushq %rbp")
    emit("    movq %rsp, %rbp")
    emit(f"    subq ${locals.stack_used()}, %rsp")
    
    # Save parameter registers to their stack locations
    param_registers = ['%rdi', '%rsi', '%rdx', '%rcx', '%r8', '%r9']
    for i, param_var in enumerate(parameter_vars[:6]):  # Maximum 6 parameters in registers
        emit(f"    # Save parameter {i+1} ({param_var.name}) from {param_registers[i]}")
        emit(f"    movq {param_registers[i]}, {locals.get_ref(param_var)}")
    
    emit("")

    # Process each instruction
    for insn in instructions:
        emit('# ' + str(insn))
        match insn:
            case ir.Label():
                emit("")
                # ".L" prefix marks the symbol as "private".
                emit(f'{label_prefix}{insn.name}:')

            case ir.LoadIntConst():
                if -2**31 <= insn.value < 2**31:
                    emit(
                        f'    movq ${insn.value}, {locals.get_ref(insn.dest)}')
                else:
                    # Use a different instruction for large integers
                    emit(f'    movabsq ${insn.value}, %rax')
                    emit(f'    movq %rax, {locals.get_ref(insn.dest)}')

            case ir.LoadBoolConst():
                # Represent true as 1 and false as 0
                value = 1 if insn.value else 0
                emit(f'    movq ${value}, {locals.get_ref(insn.dest)}')

            case ir.Copy():
                # Copy via %rax because movq can't have two memory arguments
                emit(f'    movq {locals.get_ref(insn.source)}, %rax')
                emit(f'    movq %rax, {locals.get_ref(insn.dest)}')

            case ir.Jump():
                emit(f'    jmp {label_prefix}{insn.label.name}')

            case ir.CondJump():
                # Compare condition with 0
                emit(f'    cmpq $0, {locals.get_ref(insn.cond)}')
                # Jump to then_label if condition is not 0 (true)
                emit(f'    jne {label_prefix}{insn.then_label.name}')
                # Otherwise jump to else_label
                emit(f'    jmp {label_prefix}{insn.else_label.name}')

            case ir.Call():
                # Check if this is an intrinsic operation
                fun_name = insn.fun.name

                if fun_name in all_intrinsics:
                    # Use the intrinsic implementation from intrinsics.py
                    arg_refs = [locals.get_ref(arg) for arg in insn.args]
                    all_intrinsics[fun_name](IntrinsicArgs(
                        arg_refs=arg_refs,
                        result_register='%rax',
                        emit=lambda s: emit(f'    {s}')
                    ))
                    # Store the result
                    emit(f'    movq %rax, {locals.get_ref(insn.dest)}')
                else:
                    # Function call - use the calling convention
                    # Argument registers: %rdi, %rsi, %rdx, %rcx, %r8, %r9
                    arg_registers = ['%rdi', '%rsi',
                                     '%rdx', '%rcx', '%r8', '%r9']

                    # Limit to 6 arguments for now
                    if len(insn.args) > 6:
                        raise Exception(
                            f"Function {fun_name} has too many arguments ({len(insn.args)})")

                    # Load arguments into registers
                    for i, arg in enumerate(insn.args):
                        emit(
                            f'    movq {locals.get_ref(arg)}, {arg_registers[i]}')

                    # Call the function
                    emit(f'    callq {fun_name}')

                    # Store the return value (%rax) in the destination
                    emit(f'    movq %rax, {locals.get_ref(insn.dest)}')

    # Return value handling
    if function_name == "main":
        emit("# Return from main")
        emit("    movq $0, %rax")  # Return value 0
    else:
        emit(f"# Return from {function_name}")
        # Load return value into %rax if we have one
        if return_var:
            emit(f"    movq {locals.get_ref(return_var)}, %rax")
    
    emit("    movq %rbp, %rsp")
    emit("    popq %rbp")
    emit("    ret")

    return lines


def generate_assembly(functions_ir: Dict[str, List[ir.Instruction]]) -> str:
    lines = []

    def emit(line: str) -> None:
        lines.append(line)

    emit(".extern print_int")
    emit(".extern print_bool")
    emit(".extern read_int")
    emit("")
    emit(".section .text")
    emit("")

    for i, (function_name, instructions) in enumerate(functions_ir.items()):
        label_prefix = f".{function_name}_L"

        function_ins = generate_function_assembly(function_name, instructions, label_prefix)
        lines.extend(function_ins)

        if i < len(functions_ir) - 1:  # Add blank line between functions, but not after the last one
            emit("")
    
    return "\n".join(lines)