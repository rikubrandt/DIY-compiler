#!/bin/bash

# Build the Docker image
docker build -t x86-compiler-platform -f Compiler-Dockerfile .

# Default source file
SOURCE_FILE="testcompiler"
OUTPUT_NAME="${SOURCE_FILE%.*}_out"

# Check if a file was provided as an argument
if [ $# -ge 1 ]; then
  SOURCE_FILE=$1
fi

# Check if an output name was provided
if [ $# -ge 2 ]; then
  OUTPUT_NAME=$2
fi

echo "Compiling $SOURCE_FILE to $OUTPUT_NAME..."

# Run the compiler in Docker 
docker run --platform=linux/amd64 --rm -v "$(pwd):/app" -w /app x86-compiler-platform bash -c "
cd /app && python3 -c \"
import sys
sys.path.insert(0, '/app')
from compiler import tokenizer, parser, type_checker, ir_generator
from compiler.assembly_generator import generate_assembly
from compiler.assembler import assemble

def call_compiler(source_code, out_filename):
    # Tokenization
    tokens = tokenizer.tokenize(source_code)
    print(f'Tokenization complete: {len(tokens)} tokens')
    
    # Parsing
    ast_root = parser.parse(tokens)
    if ast_root is None:
        print('Empty program')
        return None
    print('Parsing complete')
    
    # Type checking
    type_checker.typecheck(ast_root)
    print('Type checking complete')
    
    # IR generation
    root_types = ir_generator.setup_root_types()
    ir_instructions = ir_generator.generate_ir(
        root_types=root_types,
        root_expr=ast_root
    )
    print(f'IR generation complete: {len(ir_instructions)} instructions')
    
    # Assembly generation
    asm_code = generate_assembly(ir_instructions)
    print('Assembly generation complete')
    
    # Invoke the assembler
    assemble(asm_code, out_filename)
    
    print(f'Compilation successful! Output saved to {out_filename}')
    return out_filename

with open('$SOURCE_FILE', 'r') as f:
    source_code = f.read()

call_compiler(source_code, '$OUTPUT_NAME')
\"

# Now run the generated executable
./$OUTPUT_NAME
"