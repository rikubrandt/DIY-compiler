import subprocess
import tempfile
import os


def assemble(assembly_code: str, out_filename: str) -> None:
    """
    Assembles the given assembly code and produces an executable.

    Args:
        assembly_code: The assembly code to compile
        out_filename: The name of the output executable file
    """
    # Create a temporary file for the assembly code
    with tempfile.NamedTemporaryFile(suffix='.s', delete=False) as f:
        asm_filename = f.name
        f.write(assembly_code.encode('utf-8'))

    try:
        # Add definitions for built-in functions
        with open(asm_filename, 'a') as f:
            f.write('''
# Built-in functions
print_int:
    pushq %rbp
    movq %rsp, %rbp
    # Convert int to string and print it
    movq %rdi, %rsi      # Move int to second parameter
    movq $format_int, %rdi  # Format string is first parameter
    callq printf
    movq %rbp, %rsp
    popq %rbp
    ret

print_bool:
    pushq %rbp
    movq %rsp, %rbp
    # Convert bool to string and print it
    testq %rdi, %rdi
    jz .Lfalse
    movq $str_true, %rdi
    jmp .Lprint_bool_end
.Lfalse:
    movq $str_false, %rdi
.Lprint_bool_end:
    callq puts
    movq %rbp, %rsp
    popq %rbp
    ret

read_int:
    pushq %rbp
    movq %rsp, %rbp
    subq $16, %rsp        # Reserve space for the input value
    movq $format_int_scan, %rdi  # Format string
    leaq -8(%rbp), %rsi  # Buffer for integer
    callq scanf
    movq -8(%rbp), %rax  # Load the read value into result register
    movq %rbp, %rsp
    popq %rbp
    ret

.section .rodata
format_int:
    .asciz "%ld"
format_int_scan:
    .asciz "%ld"
str_true:
    .asciz "true"
str_false:
    .asciz "false"
''')

        # Run the GNU Assembler to assemble the code
        subprocess.run(['gcc', '-g', '-no-pie', asm_filename,
                       '-o', out_filename], check=True)
        print(f"Successfully assembled {out_filename}")

    finally:
        # Clean up the temporary file
        os.unlink(asm_filename)
