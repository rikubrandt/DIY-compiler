from dataclasses import dataclass
from typing import Callable, List, Dict, Optional, Any
from compiler import ir
from compiler.tokenizer import SourceLocation


@dataclass
class IntrinsicArgs:
    arg_refs: list[str]
    result_register: str
    emit: Callable[[str], None]


class Locals:
    """Knows the memory location of every local variable."""
    _var_to_location: dict[ir.IRVar, str]
    _stack_used: int

    def __init__(self, variables: list[ir.IRVar]) -> None:
        self._var_to_location = {}
        offset = 8  # Start at -8(%rbp)

        # Assign each variable a stack location
        for var in variables:
            self._var_to_location[var] = f"-{offset}(%rbp)"
            offset += 8  # Move to next 8-byte slot

        # Calculate total stack space needed (round up to multiple of 16 for alignment)
        self._stack_used = offset - 8
        if self._stack_used % 16 != 0:
            self._stack_used += 8  # Ensure 16-byte alignment

    def get_ref(self, v: ir.IRVar) -> str:
        """Returns an Assembly reference like `-24(%rbp)`
        for the memory location that stores the given variable"""
        return self._var_to_location[v]

    def stack_used(self) -> int:
        """Returns the number of bytes of stack space needed for the local variables."""
        return self._stack_used


def get_all_ir_variables(instructions: list[ir.Instruction]) -> list[ir.IRVar]:
    """Returns a list of all IR variables used in the instructions."""
    variables = set()

    for insn in instructions:
        match insn:
            case ir.LoadBoolConst(dest=dest):
                variables.add(dest)
            case ir.LoadIntConst(dest=dest):
                variables.add(dest)
            case ir.Copy(source=source, dest=dest):
                variables.add(source)
                variables.add(dest)
            case ir.Call(fun=fun, args=args, dest=dest):
                variables.add(fun)
                variables.add(dest)
                for arg in args:
                    variables.add(arg)
            case ir.CondJump(cond=cond, then_label=_, else_label=_):
                variables.add(cond)

    # Add special unit variable
    variables.add(ir.IRVar("unit"))

    return list(variables)

# Define intrinsics for basic operations


def binary_arithmetic_op(op_instruction: str) -> Callable[[IntrinsicArgs], None]:
    def emit_op(args: IntrinsicArgs) -> None:
        if len(args.arg_refs) != 2:
            raise ValueError(f"Binary operation needs exactly 2 arguments")
        args.emit(f"movq {args.arg_refs[0]}, {args.result_register}")
        args.emit(
            f"{op_instruction} {args.arg_refs[1]}, {args.result_register}")
    return emit_op


def binary_comparison_op(jmp_instruction: str) -> Callable[[IntrinsicArgs], None]:
    def emit_op(args: IntrinsicArgs) -> None:
        if len(args.arg_refs) != 2:
            raise ValueError(f"Comparison operation needs exactly 2 arguments")
        args.emit(f"movq {args.arg_refs[0]}, {args.result_register}")
        args.emit(f"cmpq {args.arg_refs[1]}, {args.result_register}")
        args.emit(f"movq $0, {args.result_register}")  # Default to 0 (false)
        args.emit(f"{jmp_instruction} 1f")  # Jump if condition is true
        args.emit(f"jmp 2f")
        args.emit(f"1:")
        args.emit(f"movq $1, {args.result_register}")  # Set to 1 (true)
        args.emit(f"2:")
    return emit_op


def unary_op(op_instruction: str) -> Callable[[IntrinsicArgs], None]:
    def emit_op(args: IntrinsicArgs) -> None:
        if len(args.arg_refs) != 1:
            raise ValueError(f"Unary operation needs exactly 1 argument")
        args.emit(f"movq {args.arg_refs[0]}, {args.result_register}")
        args.emit(f"{op_instruction} {args.result_register}")
    return emit_op

# Fix: Define functions instead of using problematic lambda tuples


def division_op(args: IntrinsicArgs) -> None:
    args.emit(f"movq {args.arg_refs[0]}, %rax")
    args.emit(f"cqto")  # Sign-extend %rax into %rdx:%rax
    args.emit(f"idivq {args.arg_refs[1]}")
    args.emit(f"movq %rax, {args.result_register}")


def modulo_op(args: IntrinsicArgs) -> None:
    args.emit(f"movq {args.arg_refs[0]}, %rax")
    args.emit(f"cqto")  # Sign-extend %rax into %rdx:%rax
    args.emit(f"idivq {args.arg_refs[1]}")
    args.emit(f"movq %rdx, {args.result_register}")  # Remainder is in %rdx


def and_op(args: IntrinsicArgs) -> None:
    args.emit(f"movq {args.arg_refs[0]}, {args.result_register}")
    args.emit(f"andq {args.arg_refs[1]}, {args.result_register}")


def or_op(args: IntrinsicArgs) -> None:
    args.emit(f"movq {args.arg_refs[0]}, {args.result_register}")
    args.emit(f"orq {args.arg_refs[1]}, {args.result_register}")


# Dictionary mapping operator names to functions that emit assembly code
all_intrinsics: Dict[str, Callable[[IntrinsicArgs], None]] = {}

# Register arithmetic operations
all_intrinsics["+"] = binary_arithmetic_op("addq")
all_intrinsics["-"] = binary_arithmetic_op("subq")
all_intrinsics["*"] = binary_arithmetic_op("imulq")
all_intrinsics["/"] = division_op
all_intrinsics["%"] = modulo_op

# Register comparison operations
all_intrinsics["=="] = binary_comparison_op("je")
all_intrinsics["!="] = binary_comparison_op("jne")
all_intrinsics["<"] = binary_comparison_op("jl")
all_intrinsics["<="] = binary_comparison_op("jle")
all_intrinsics[">"] = binary_comparison_op("jg")
all_intrinsics[">="] = binary_comparison_op("jge")

# Register logical operations
all_intrinsics["and"] = and_op
all_intrinsics["or"] = or_op

# Register unary operations
all_intrinsics["not"] = unary_op("notq")
all_intrinsics["unary_-"] = unary_op("negq")


def generate_assembly(instructions: list[ir.Instruction]) -> str:
    lines = []
    def emit(line: str) -> None: lines.append(line)

    # Get all variables and create the Locals mapping
    locals = Locals(
        variables=get_all_ir_variables(instructions)
    )

    # Emit declarations and standard function prologue
    emit("    .extern print_int")
    emit("    .extern print_bool")
    emit("    .extern read_int")
    emit("    .global main")
    emit("    .type main, @function")
    emit("")
    emit("    .section .text")
    emit("")
    emit("main:")
    emit("    pushq %rbp")
    emit("    movq %rsp, %rbp")
    emit(
        f"    subq ${locals.stack_used()}, %rsp  # Reserve stack space for locals")
    emit("")

    # Process each IR instruction
    for insn in instructions:
        emit('# ' + str(insn))
        match insn:
            case ir.Label():
                emit("")
                # ".L" prefix marks the symbol as "private"
                emit(f'.L{insn.name}:')

            case ir.LoadIntConst():
                if -2**31 <= insn.value < 2**31:
                    emit(
                        f'    movq ${insn.value}, {locals.get_ref(insn.dest)}')
                else:
                    # For large integers, use movabsq with a temporary register
                    emit(f'    movabsq ${insn.value}, %rax')
                    emit(f'    movq %rax, {locals.get_ref(insn.dest)}')

            case ir.LoadBoolConst():
                # Represent booleans as 0 (false) or 1 (true)
                value = 1 if insn.value else 0
                emit(f'    movq ${value}, {locals.get_ref(insn.dest)}')

            case ir.Copy():
                # Use %rax as temporary since x86 can't move directly between memory locations
                emit(f'    movq {locals.get_ref(insn.source)}, %rax')
                emit(f'    movq %rax, {locals.get_ref(insn.dest)}')

            case ir.Jump():
                emit(f'    jmp .L{insn.label.name}')

            case ir.CondJump():
                # Compare condition with 0 (false)
                emit(f'    movq {locals.get_ref(insn.cond)}, %rax')
                emit(f'    cmpq $0, %rax')
                # Jump to then_label if not equal to 0 (true), else to else_label
                emit(f'    jne .L{insn.then_label.name}')
                emit(f'    jmp .L{insn.else_label.name}')

            case ir.Call():
                # Handle intrinsics (built-in operations)
                if insn.fun.name in all_intrinsics:
                    arg_refs = [locals.get_ref(arg) for arg in insn.args]
                    all_intrinsics[insn.fun.name](IntrinsicArgs(
                        arg_refs=arg_refs,
                        result_register="%rax",
                        emit=lambda s: emit("    " + s)
                    ))
                    # Store the result
                    emit(f'    movq %rax, {locals.get_ref(insn.dest)}')
                else:
                    # Regular function call
                    # Prepare arguments according to the calling convention
                    arg_registers = ["%rdi", "%rsi",
                                     "%rdx", "%rcx", "%r8", "%r9"]

                    # Limit to 6 arguments (that fit in registers)
                    if len(insn.args) > 6:
                        emit(f'    # Warning: only first 6 arguments supported')

                    # Move arguments to appropriate registers
                    for i, arg in enumerate(insn.args[:6]):
                        emit(
                            f'    movq {locals.get_ref(arg)}, {arg_registers[i]}')

                    # Call the function
                    emit(f'    callq {insn.fun.name}')

                    # Store the result (which is in %rax)
                    emit(f'    movq %rax, {locals.get_ref(insn.dest)}')

    # Function epilogue - restore stack and return
    emit("")
    emit("    # Epilogue - restore stack and return")
    emit("    movq %rbp, %rsp")
    emit("    popq %rbp")
    emit("    ret")

    return "\n".join(lines)
