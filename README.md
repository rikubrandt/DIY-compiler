# DIY Compiler 

This project implements a simple compiler that supports the following language constructs:

- **Literals:**  
  - Integer literals (e.g., `42`)
  - Boolean literals (`true`, `false`)

- **Operators:**  
  - Binary: `+`, `-`, `*`, `/`, `%`, `==`, `!=`, `<`, `<=`, `>`, `>=`, `and`, `or`  
    _Note:_ Binary operators use standard precedence and are left-associative.
  - Unary: `-` and `not`

- **Library Functions:**  
  - `print_int`, `read_int`, and `print_bool`

- **Control Structures:**  
  - Blocks of statements `{ ... }`
  - Conditional expressions: `if-then` and `if-then-else`
  - Loops: `while` loops
  - **Break and Continue:**  
    - `break` exits the innermost loop  
    - `continue` returns control to the beginning of the innermost loop  
    _Note:_ Both have type `Unit`.

- **Variables and Assignment:**  
  - Local variables with initializers (e.g., `var x: Int = 10;`)
  - Assignment statements are right-associative

- **Functions:**  
  - Define functions with the `fun` keyword  
  - Example:  
    ```  
    fun square(x: Int): Int {
        return x * x;
    }
    
    fun vec_len_squared(x: Int, y: Int): Int {
        return square(x) + square(y);
    }
    
    fun print_int_twice(x: Int): Unit {
        print_int(x);
        print_int(x);
    }
    
    print_int_twice(vec_len_squared(3, 4));
    ```

## Compiler Components

This compiler consists of the following stages:

1. **Tokenizer:**  
   Converts source code into a stream of tokens.

2. **Parser:**  
   Builds an abstract syntax tree (AST) from the tokens.  
   _Note:_ The parser now emits a module AST node containing a top-level expression (or block) that can include function definitions.

3. **Type Checker:**  
   Validates the AST against the language's type rules.  
   _Extra:_ It also ensures that all break statements in a loop (or with an optional result value) have consistent types.

4. **IR Generator:**  
   Translates the typed AST into an intermediate representation.  
   _Tip:_ The IR generation phase keeps track of the innermost loop labels for handling break/continue.

5. **Assembly Generator:**  
   Converts the IR into assembly code for the target platform.

## Demonstration

Below is a simple demonstration that uses several language features:

```plaintext
fun square(x: Int): Int {
    return x * x;
}

fun print_int_twice(x: Int): Unit {
    print_int(x);
    print_int(x);
}

var a: Int = read_int();
var b: Int = read_int();
var result: Int = square(a) + square(b);

while (result < 100) {
    print_int(result);
    result = result + 1;
    if (result == 50) {
        break;
    }
}

print_int_twice(result);


```

## Setup

If you're on Debian/Ubuntu, this should install all needed system dependencies:

    apt install build-essential python3 curl git zlib1g-dev libssl-dev libbz2-dev libffi-dev libreadline-dev liblzma-dev libsqlite3-dev

Requirements:

- [Pyenv](https://github.com/pyenv/pyenv) for installing Python 3.12+
    - Recommended installation method: the "automatic installer"
      i.e. `curl https://pyenv.run | bash`
    - Follow the instructions at the end of the output to make pyenv available in your shell.
      You may need to restart your shell or even log out and log in again to make
      the `pyenv` command available.
- [Poetry](https://python-poetry.org/) for installing dependencies
    - Recommended installation method: the "official installer"
      i.e. `curl -sSL https://install.python-poetry.org | python3 -`
Install dependencies:

    # Install Python specified in `.python-version`
    pyenv install
    # Install dependencies specified in `pyproject.toml`
    poetry install

If `pyenv install` gives an error about `_tkinter`, you can ignore it.
If you see other errors, you may have to investigate.

If you have trouble with Poetry not picking up pyenv's python installation,
try `poetry env remove --all` and then `poetry install` again.

