from base64 import b64encode
import json
import re
import sys
from socketserver import ForkingTCPServer, StreamRequestHandler
from traceback import format_exception
from typing import Any
from compiler.assembly_generator import generate_assembly
from compiler import assembler, type_checker, parser, tokenizer, ir_generator, ir, types_compiler


def call_compiler(source_code: str, out_filename: str) -> str:
    """Compiles source code and saves the output to a file."""
    # Tokenization
    tokens = tokenizer.tokenize(source_code)

    # Parsing
    ast_root = parser.parse(tokens)
    if ast_root is None:
        print("Empty program")
        return None

    # Type checking
    type_env = type_checker.TypeEnv()
    # Add built-in functions to the environment
    type_env.set("print_int", types_compiler.FunType(
        [types_compiler.Int], types_compiler.Unit))
    type_env.set("print_bool", types_compiler.FunType(
        [types_compiler.Bool], types_compiler.Unit))
    type_env.set("read_int", types_compiler.FunType([], types_compiler.Int))
    # Add operators
    type_env.set(
        "+", types_compiler.FunType([types_compiler.Int, types_compiler.Int], types_compiler.Int))
    type_env.set(
        "-", types_compiler.FunType([types_compiler.Int, types_compiler.Int], types_compiler.Int))
    type_env.set(
        "*", types_compiler.FunType([types_compiler.Int, types_compiler.Int], types_compiler.Int))
    type_env.set(
        "/", types_compiler.FunType([types_compiler.Int, types_compiler.Int], types_compiler.Int))
    type_env.set("%", types_compiler.FunType(
        [types_compiler.Int, types_compiler.Int], types_compiler.Int))
    type_env.set("<", types_compiler.FunType(
        [types_compiler.Int, types_compiler.Int], types_compiler.Bool))
    type_env.set("<=", types_compiler.FunType(
        [types_compiler.Int, types_compiler.Int], types_compiler.Bool))
    type_env.set(">", types_compiler.FunType(
        [types_compiler.Int, types_compiler.Int], types_compiler.Bool))
    type_env.set(">=", types_compiler.FunType(
        [types_compiler.Int, types_compiler.Int], types_compiler.Bool))
    type_env.set("==", types_compiler.FunType(
        [types_compiler.Int, types_compiler.Int], types_compiler.Bool))
    type_env.set("!=", types_compiler.FunType(
        [types_compiler.Int, types_compiler.Int], types_compiler.Bool))
    type_env.set("and", types_compiler.FunType(
        [types_compiler.Bool, types_compiler.Bool], types_compiler.Bool))
    type_env.set("or", types_compiler.FunType(
        [types_compiler.Bool, types_compiler.Bool], types_compiler.Bool))
    type_env.set("not", types_compiler.FunType(
        [types_compiler.Bool], types_compiler.Bool))
    type_env.set(
        "unary_-", types_compiler.FunType([types_compiler.Int], types_compiler.Int))

    type_checker.typecheck(ast_root, type_env)

    # IR generation
    ir_instructions = ir_generator.generate_ir(
        root_types={ir.IRVar(name): type_env.get(name)
                    for name in type_env.env},
        root_expr=ast_root
    )

    # Assembly generation - this is the new step!
    asm_code = generate_assembly(ir_instructions)

    # Invoke the assembler - also new!
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
            raise Exception("Output file flag --output=... required")
        executable = call_compiler(source_code, input_file or '(source code)')
        with open(output_file, 'wb') as f:
            f.write(executable)
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
