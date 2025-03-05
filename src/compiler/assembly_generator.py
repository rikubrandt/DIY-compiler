from typing import List, Dict, Set, Callable
from dataclasses import dataclass
from src.compiler import ir


@dataclass
class IntrinsicArgs:
    """Arguments passed to intrinsic functions."""
    arg_refs: list[str]  # Assembly references to arguments
    result_register: str  # Register to store the result
    emit: Callable[[str], None]  # Function to emit Assembly code


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


# Dictionary of intrinsics for basic operations
all_intrinsics = {
    '+': lambda args: (
        args.emit(f"movq {args.arg_refs[0]}, {args.result_register}"),
        args.emit(f"addq {args.arg_refs[1]}, {args.result_register}")
    ),
    '-': lambda args: (
        args.emit(f"movq {args.arg_refs[0]}, {args.result_register}"),
        args.emit(f"subq {args.arg_refs[1]}, {args.result_register}")
    ),
    '*': lambda args: (
        args.emit(f"movq {args.arg_refs[0]}, {args.result_register}"),
        args.emit(f"imulq {args.arg_refs[1]}, {args.result_register}")
    ),
    '/': lambda args: (
        args.emit(f"movq {args.arg_refs[0]}, %rax"),
        args.emit(f"cqto"),  # Sign-extend %rax into %rdx:%rax
        args.emit(f"movq {args.arg_refs[1]}, %rcx"),
        args.emit(f"idivq %rcx"),  # Divide %rdx:%rax by %rcx, quotient in %rax
        args.emit(f"movq %rax, {args.result_register}")
    ),
    '%': lambda args: (
        args.emit(f"movq {args.arg_refs[0]}, %rax"),
        args.emit(f"cqto"),  # Sign-extend %rax into %rdx:%rax
        args.emit(f"movq {args.arg_refs[1]}, %rcx"),
        # Divide %rdx:%rax by %rcx, remainder in %rdx
        args.emit(f"idivq %rcx"),
        args.emit(f"movq %rdx, {args.result_register}")
    ),
    '<': lambda args: (
        args.emit(f"movq {args.arg_refs[0]}, %rax"),
        args.emit(f"cmpq {args.arg_refs[1]}, %rax"),
        args.emit(f"setl %al"),  # Set %al to 1 if %rax < arg1
        # Zero-extend %al into result
        args.emit(f"movzbq %al, {args.result_register}")
    ),
    '>': lambda args: (
        args.emit(f"movq {args.arg_refs[0]}, %rax"),
        args.emit(f"cmpq {args.arg_refs[1]}, %rax"),
        args.emit(f"setg %al"),  # Set %al to 1 if %rax > arg1
        args.emit(f"movzbq %al, {args.result_register}")
    ),
    '<=': lambda args: (
        args.emit(f"movq {args.arg_refs[0]}, %rax"),
        args.emit(f"cmpq {args.arg_refs[1]}, %rax"),
        args.emit(f"setle %al"),  # Set %al to 1 if %rax <= arg1
        args.emit(f"movzbq %al, {args.result_register}")
    ),
    '>=': lambda args: (
        args.emit(f"movq {args.arg_refs[0]}, %rax"),
        args.emit(f"cmpq {args.arg_refs[1]}, %rax"),
        args.emit(f"setge %al"),  # Set %al to 1 if %rax >= arg1
        args.emit(f"movzbq %al, {args.result_register}")
    ),
    '==': lambda args: (
        args.emit(f"movq {args.arg_refs[0]}, %rax"),
        args.emit(f"cmpq {args.arg_refs[1]}, %rax"),
        args.emit(f"sete %al"),  # Set %al to 1 if %rax == arg1
        args.emit(f"movzbq %al, {args.result_register}")
    ),
    '!=': lambda args: (
        args.emit(f"movq {args.arg_refs[0]}, %rax"),
        args.emit(f"cmpq {args.arg_refs[1]}, %rax"),
        args.emit(f"setne %al"),  # Set %al to 1 if %rax != arg1
        args.emit(f"movzbq %al, {args.result_register}")
    ),
    'and': lambda args: (
        args.emit(f"movq {args.arg_refs[0]}, %rax"),
        args.emit(f"andq {args.arg_refs[1]}, %rax"),
        args.emit(f"movq %rax, {args.result_register}")
    ),
    'or': lambda args: (
        args.emit(f"movq {args.arg_refs[0]}, %rax"),
        args.emit(f"orq {args.arg_refs[1]}, %rax"),
        args.emit(f"movq %rax, {args.result_register}")
    ),
    'unary_-': lambda args: (
        args.emit(f"movq {args.arg_refs[0]}, {args.result_register}"),
        args.emit(f"negq {args.result_register}")
    ),
    'unary_not': lambda args: (
        args.emit(f"movq {args.arg_refs[0]}, {args.result_register}"),
        args.emit(f"xorq $1, {args.result_register}")  # Flip the lowest bit
    ),
}


def generate_assembly(instructions: List[ir.Instruction]) -> str:
    """Generate x86-64 Assembly code from IR instructions."""
    lines = []

    def emit(line: str) -> None:
        lines.append(line)

    # Get all variables used in the program
    variables = get_all_ir_variables(instructions)
    locals = Locals(variables=variables)

    # Emit initial declarations and stack setup
    emit(".extern print_int")
    emit(".extern print_bool")
    emit(".extern read_int")
    emit(".global main")
    emit(".type main, @function")
    emit("")
    emit(".section .text")
    emit("")
    emit("main:")
    emit("    pushq %rbp")
    emit("    movq %rsp, %rbp")
    emit(f"    subq ${locals.stack_used()}, %rsp")
    emit("")

    # Process each instruction
    for insn in instructions:
        emit('# ' + str(insn))
        match insn:
            case ir.Label():
                emit("")
                # ".L" prefix marks the symbol as "private".
                emit(f'.L{insn.name}:')

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
                emit(f'    jmp .L{insn.label.name}')

            case ir.CondJump():
                # Compare condition with 0
                emit(f'    cmpq $0, {locals.get_ref(insn.cond)}')
                # Jump to then_label if condition is not 0 (true)
                emit(f'    jne .L{insn.then_label.name}')
                # Otherwise jump to else_label
                emit(f'    jmp .L{insn.else_label.name}')

            case ir.Call():
                # Check if this is an intrinsic operation
                fun_name = insn.fun.name

                if fun_name in all_intrinsics:
                    # Use the intrinsic implementation
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

    # Restore the stack and return
    emit("")
    emit("# Return from main")
    emit("    movq $0, %rax")  # Return value 0
    emit("    movq %rbp, %rsp")
    emit("    popq %rbp")
    emit("    ret")

    # Join all lines and return
    return '\n'.join(lines)
