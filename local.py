import sys
import subprocess
# This function should compile your source to assembly.
from compiler.__main__ import call_compiler
from compiler.assembler import assemble

def pretty_print(node, indent=0):
    """
    Recursively pretty-print an AST node, skipping location information.
    """
    indent_str = "  " * indent
    if hasattr(node, "__dict__"):
        result = f"{indent_str}{node.__class__.__name__}(\n"
        for key, value in node.__dict__.items():
            # Skip location-related attributes.
            if key in ("location", "loc"):
                continue
            result += f"{indent_str}  {key} = "
            if isinstance(value, list):
                result += "[\n"
                for item in value:
                    result += pretty_print(item, indent + 2) + ",\n"
                result += f"{indent_str}  ]\n"
            elif hasattr(value, "__dict__"):
                result += "\n" + pretty_print(value, indent + 2) + "\n"
            else:
                result += f"{value!r}\n"
        result += f"{indent_str})"
        return result
    else:
        return f"{indent_str}{node!r}"


def main():
    if len(sys.argv) < 2:
        print("Usage: {} <source_file>".format(sys.argv[0]))
        sys.exit(1)

    source_file = sys.argv[1]

    # Read the source file containing your program
    with open(source_file, 'r') as f:
        source_code = f.read()

    from compiler import tokenizer, parser, type_checker, ir_generator
    from compiler.assembly_generator import generate_assembly
    from compiler.assembler import assemble_and_get_executable

    # Run compilation pipeline
    tokens = tokenizer.tokenize(source_code)
    ast_root = parser.parse(tokens)
    print(pretty_print(ast_root))
    type_checker.typecheck(ast_root)
    root_types = ir_generator.setup_root_types()
    ir_instructions = ir_generator.generate_ir(
        root_types=root_types, root_module=ast_root)
    
    print(ir_instructions)
    asm_code = generate_assembly(ir_instructions)
    print(asm_code)
    executable_file = assemble(asm_code, "./test.out")

    print("Executable '{}' generated successfully.".format(executable_file))

    # Run the executable and capture its output
    result = subprocess.run(["./" + "test.out"],
                            capture_output=True, text=True)
    print("Program output:")
    print(result.stdout)
    if result.stderr:
        print("Program errors:")
        print(result.stderr)


if __name__ == '__main__':
    main()
