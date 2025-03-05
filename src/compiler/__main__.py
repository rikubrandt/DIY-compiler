from base64 import b64encode
import json
import re
import sys
import os
from socketserver import ForkingTCPServer, StreamRequestHandler
from traceback import format_exception
from typing import Any
from src.compiler.assembly_generator import generate_assembly
from src.compiler import assembler, type_checker, parser, tokenizer, ir_generator


def call_compiler(source_code: str, out_filename: str) -> str:
    """Compiles source code and saves the output to a file."""
    # Tokenization
    tokens = tokenizer.tokenize(source_code)
    print(f"Tokenization complete: {len(tokens)} tokens")

    # Parsing
    ast_root = parser.parse(tokens)
    if ast_root is None:
        print("Empty program")
        return None
    print("Parsing complete")

    # Type checking
    type_checker.typecheck(ast_root)
    print("Type checking complete")

    # IR generation
    root_types = ir_generator.setup_root_types()
    ir_instructions = ir_generator.generate_ir(
        root_types=root_types,
        root_expr=ast_root
    )
    print(f"IR generation complete: {len(ir_instructions)} instructions")

    # Assembly generation
    asm_code = generate_assembly(ir_instructions)
    print("Assembly generation complete")

    # Invoke the assembler
    assembler.assemble(asm_code, out_filename)

    print(f"Compilation successful! Output saved to {out_filename}")

    return out_filename


def main() -> int:
    # === Option parsing ===
    command: str | None = None
    input_file: str | None = None
    output_file: str | None = None
    host = "127.0.0.1"
    port = 3000

    # Simple parsing for file + output name scenario
    if len(sys.argv) == 3 and not sys.argv[1].startswith("-") and not sys.argv[2].startswith("-"):
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        command = "compile"
    else:
        # More complex parsing for other scenarios
        for arg in sys.argv[1:]:
            if (m := re.fullmatch(r'--output=(.+)', arg)) is not None:
                output_file = m[1]
            elif (m := re.fullmatch(r'--host=(.+)', arg)) is not None:
                host = m[1]
            elif (m := re.fullmatch(r'--port=(.+)', arg)) is not None:
                port = int(m[1])
            elif arg.startswith('-'):
                raise Exception(f"Unknown argument: {arg}")
            elif command is None:
                command = arg
            elif input_file is None:
                input_file = arg
            else:
                raise Exception("Multiple input files not supported")

    if command is None:
        # Default to compile if command missing but input file provided
        if input_file is not None:
            command = "compile"
        else:
            print(f"Error: command argument missing", file=sys.stderr)
            return 1

    def read_source_code() -> str:
        if input_file is not None:
            with open(input_file) as f:
                return f.read()
        else:
            return sys.stdin.read()

    # === Command implementations ===
    if command == 'compile':
        source_code = read_source_code()
        if output_file is None:
            # If no output file specified, use input filename without extension
            if input_file:
                output_file = os.path.splitext(input_file)[0]
            else:
                output_file = "a.out"

        try:
            executable_path = call_compiler(source_code, output_file)
            print(f"You can run the program with ./{executable_path}")
            return 0
        except Exception as e:
            print(f"Compilation error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1

    elif command == 'serve':
        try:
            run_server(host, port)
        except KeyboardInterrupt:
            pass
    else:
        print(f"Error: unknown command: {command}", file=sys.stderr)
        return 1
    return 0


def run_server(host: str, port: int) -> None:
    class Server(ForkingTCPServer):
        allow_reuse_address = True
        request_queue_size = 32

    class Handler(StreamRequestHandler):
        def handle(self) -> None:
            result: dict[str, Any] = {}
            try:
                input_str = self.rfile.read().decode()
                input = json.loads(input_str)
                if input["command"] == "compile":
                    source_code = input["code"]
                    executable = call_compiler(source_code, "(source code)")
                    result["program"] = b64encode(executable).decode()
                elif input["command"] == "ping":
                    pass
                else:
                    result["error"] = "Unknown command: " + input['command']
            except Exception as e:
                result["error"] = "".join(format_exception(e))
            result_str = json.dumps(result)
            self.request.sendall(str.encode(result_str))

    print(f"Starting TCP server at {host}:{port}")
    with Server((host, port), Handler) as server:
        server.serve_forever()


if __name__ == '__main__':
    sys.exit(main())
