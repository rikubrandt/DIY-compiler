import sys
import subprocess
# This function should compile your source to assembly.
from compiler.__main__ import call_compiler
from compiler.assembler import assemble


def main():
    if len(sys.argv) < 2:
        print("Usage: {} <source_file>".format(sys.argv[0]))
        sys.exit(1)

    source_file = sys.argv[1]

    # Read the source file containing your program
    with open(source_file, 'r') as f:
        source_code = f.read()

    # Compile the source code into assembly using your call_compiler pipeline.
    # This function should return a string containing the x86 assembly code.
    assembly_code = call_compiler(source_code, source_file)

    # Name for the generated executable
    executable_file = "program.out"

    # Assemble the code into an executable file.
    # Set link_with_c=True if you need to link against the C standard library.
    assemble(assembly_code, executable_file, link_with_c=True)

    print("Executable '{}' generated successfully.".format(executable_file))

    # Run the executable and capture its output
    result = subprocess.run(["./" + executable_file],
                            capture_output=True, text=True)
    print("Program output:")
    print(result.stdout)
    if result.stderr:
        print("Program errors:")
        print(result.stderr)


if __name__ == '__main__':
    main()
