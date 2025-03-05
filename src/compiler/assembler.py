import os
import tempfile
import subprocess
from typing import Optional


def assemble(assembly_code: str, output_filename: str) -> None:
    """
    Assembles the given x86-64 assembly code into an executable binary.

    Args:
        assembly_code: The assembly code to assemble
        output_filename: The name of the output executable file
    """
    # Create a temporary file to hold the assembly code
    with tempfile.NamedTemporaryFile(suffix='.s', mode='w', delete=False) as f:
        asm_filename = f.name

        # Add helper functions (print_int, print_bool, read_int)
        # These implementations don't depend on the C standard library
        # They use direct Linux syscalls instead
        helpers = """
# Helper functions for I/O using Linux syscalls
.section .data
newline:
    .byte 10
digit_buffer:
    .zero 32

.section .text
# Function to print an integer (print_int)
# Takes one parameter in %rdi
print_int:
    pushq %rbp
    movq %rsp, %rbp
    
    # Save callee-saved registers
    pushq %rbx
    pushq %r12
    pushq %r13
    
    # Check if the number is negative
    movq %rdi, %rax
    movq $0, %r12  # r12 = negative flag
    cmpq $0, %rax
    jge .Lpositive
    
    # Handle negative numbers
    movq $1, %r12  # Set negative flag
    negq %rax  # Make the number positive for conversion
    
.Lpositive:
    # Convert integer to string (backwards)
    leaq digit_buffer+31(%rip), %rbx  # End of buffer
    movb $0, (%rbx)  # Null-terminate the string
    
    # If number is 0, special case
    cmpq $0, %rax
    jne .Lconvert_loop
    
    decq %rbx
    movb $'0', (%rbx)
    jmp .Lprint_result
    
.Lconvert_loop:
    cmpq $0, %rax
    je .Ldone_convert
    
    # Get next digit
    movq $0, %rdx
    movq $10, %rcx
    divq %rcx  # Divide by 10, remainder in %rdx
    
    # Convert to ASCII and store
    addq $'0', %rdx
    decq %rbx
    movb %dl, (%rbx)
    
    jmp .Lconvert_loop
    
.Ldone_convert:
    # Add negative sign if needed
    cmpq $0, %r12
    je .Lprint_result
    
    decq %rbx
    movb $'-', (%rbx)
    
.Lprint_result:
    # Calculate string length
    leaq digit_buffer+31(%rip), %r13
    subq %rbx, %r13  # r13 = length
    
    # Call write syscall
    movq $1, %rax  # syscall number for write
    movq $1, %rdi  # file descriptor 1 = stdout
    movq %rbx, %rsi  # buffer address
    movq %r13, %rdx  # buffer length
    syscall
    
    # Print newline
    movq $1, %rax  # syscall number for write
    movq $1, %rdi  # file descriptor 1 = stdout
    leaq newline(%rip), %rsi  # address of newline
    movq $1, %rdx  # length = 1
    syscall
    
    # Restore callee-saved registers
    popq %r13
    popq %r12
    popq %rbx
    
    # Return
    movq %rbp, %rsp
    popq %rbp
    ret

# Function to print a boolean (print_bool)
# Takes one parameter in %rdi (0 = false, anything else = true)
print_bool:
    pushq %rbp
    movq %rsp, %rbp
    
    # Convert to "true" or "false" string
    cmpq $0, %rdi
    je .Lprint_false
    
    # Print "true"
    movq $1, %rax  # syscall number for write
    movq $1, %rdi  # file descriptor 1 = stdout
    leaq .Ltrue_str(%rip), %rsi  # address of "true"
    movq $4, %rdx  # length = 4
    syscall
    jmp .Lbool_newline
    
.Lprint_false:
    # Print "false"
    movq $1, %rax  # syscall number for write
    movq $1, %rdi  # file descriptor 1 = stdout
    leaq .Lfalse_str(%rip), %rsi  # address of "false"
    movq $5, %rdx  # length = 5
    syscall
    
.Lbool_newline:
    # Print newline
    movq $1, %rax  # syscall number for write
    movq $1, %rdi  # file descriptor 1 = stdout
    leaq newline(%rip), %rsi  # address of newline
    movq $1, %rdx  # length = 1
    syscall
    
    # Return
    movq %rbp, %rsp
    popq %rbp
    ret

.section .rodata
.Ltrue_str:
    .string "true"
.Lfalse_str:
    .string "false"

.section .text
# Function to read an integer (read_int)
# Returns the integer in %rax
read_int:
    pushq %rbp
    movq %rsp, %rbp
    
    # Save callee-saved registers
    pushq %rbx
    pushq %r12
    pushq %r13
    pushq %r14
    
    # Allocate buffer on stack
    subq $32, %rsp
    movq %rsp, %rbx  # rbx = buffer address
    
    # Read from stdin
    movq $0, %rax  # syscall number for read
    movq $0, %rdi  # file descriptor 0 = stdin
    movq %rbx, %rsi  # buffer address
    movq $32, %rdx  # buffer size
    syscall
    
    # If error or EOF, return 0
    cmpq $0, %rax
    jle .Lread_error
    
    # Parse integer
    movq $0, %r12  # r12 = result
    movq $1, %r13  # r13 = sign (1 = positive, -1 = negative)
    movq $0, %r14  # r14 = index
    
    # Check for sign
    movb (%rbx, %r14, 1), %al
    cmpb $'-', %al
    jne .Lparse_digits
    
    # Handle negative sign
    movq $-1, %r13
    incq %r14
    
.Lparse_digits:
    cmpq %rax, %r14  # Check if we've reached the end of input
    jge .Lfinish_parse
    
    movb (%rbx, %r14, 1), %al
    
    # Check if character is a digit
    cmpb $'0', %al
    jl .Lfinish_parse
    cmpb $'9', %al
    jg .Lfinish_parse
    
    # Convert digit and add to result
    subb $'0', %al
    movzbq %al, %rcx
    
    # result = result * 10 + digit
    imulq $10, %r12
    addq %rcx, %r12
    
    incq %r14
    jmp .Lparse_digits
    
.Lfinish_parse:
    # Apply sign
    imulq %r13, %r12
    movq %r12, %rax
    jmp .Lread_done
    
.Lread_error:
    movq $0, %rax
    
.Lread_done:
    # Restore stack and callee-saved registers
    addq $32, %rsp
    popq %r14
    popq %r13
    popq %r12
    popq %rbx
    
    # Return
    movq %rbp, %rsp
    popq %rbp
    ret
"""
        # Write the full assembly code to the file
        f.write(helpers)
        f.write("\n")
        f.write(assembly_code)

    try:
        # Assemble the code with the GNU Assembler (gas)
        # IMPORTANT: Explicitly specifying x86-64 target for cross-platform compatibility
        subprocess.run(
            ['as', '--64', '-o', f'{asm_filename}.o', asm_filename], check=True)

        # Link to create an executable
        subprocess.run(
            ['ld', '-m', 'elf_x86_64', '-o',
                output_filename, f'{asm_filename}.o'],
            check=True
        )

        # Make the output file executable
        os.chmod(output_filename, 0o755)

        print(f"Assembly successful! Executable created at {output_filename}")

    except subprocess.CalledProcessError as e:
        print(f"Assembly failed: {e}")
        if os.path.exists(output_filename):
            os.remove(output_filename)

    finally:
        # Clean up temporary files
        if os.path.exists(asm_filename):
            os.remove(asm_filename)
        if os.path.exists(f'{asm_filename}.o'):
            os.remove(f'{asm_filename}.o')


# Example usage
if __name__ == "__main__":
    # Simple assembly program that prints the number 42
    assembly_code = """
    .section .text
    .global main
    main:
        pushq %rbp
        movq %rsp, %rbp
        
        # Print the number 42
        movq $42, %rdi
        callq print_int
        
        # Return 0
        movq $0, %rax
        movq %rbp, %rsp
        popq %rbp
        ret
    """

    assemble(assembly_code, "test_program")
    print("You can run the program with ./test_program")
