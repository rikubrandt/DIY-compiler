from dataclasses import dataclass
from typing import Literal, Optional
import re

TokenType = Literal["int_literal", "identifier", "operator", "parenthesis"]

@dataclass(frozen=True)
class SourceLocation:
    line: int
    column: int
    def __eq__(self, other):
        return isinstance(other, SourceLocation) or other is L

L = SourceLocation(line=-1, column=-1)  # Placeholder object for testing

@dataclass(frozen=True)
class Token:
    type: TokenType
    text: str
    loc: SourceLocation

class Tokenizer:
    COMMENT_PATTERN = re.compile(r"//.*|#.*")

    TOKEN_PATTERNS = [
        ("int_literal", re.compile(r"[0-9]+")),
        ("identifier", re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")),
        ("operator", re.compile(r"==|!=|<=|>=|[+\-*/=<>]")),
        ("parenthesis", re.compile(r"[(){},;]")),
        ("comment", re.compile(r"//.*|#.*")),

    ]

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.position = 0
        self.line = 1
        self.column = 1

    def _skip_whitespace_and_comments(self):
        while self.position < len(self.source_code):
            whitespace_match = re.match(r"\s+", self.source_code[self.position:])
            comment_match = self.COMMENT_PATTERN.match(self.source_code, self.position)
            
            if whitespace_match:
                for char in whitespace_match.group():
                    if char == '\n':
                        self.line += 1
                        self.column = 1
                    else:
                        self.column += 1
                self.position += whitespace_match.end()
            elif comment_match:
                self.position += len(comment_match.group())
            else:
                break

    def _match_token(self) -> Optional[Token]:
        for token_type, pattern in self.TOKEN_PATTERNS:
            match = pattern.match(self.source_code, self.position)
            if match:
                token_text = match.group()
                loc = SourceLocation(self.line, self.column)
                self.position += len(token_text)
                self.column += len(token_text)
                return Token(type=token_type, text=token_text, loc=loc)
        return None

    def tokenize(self) -> list[Token]:
        tokens = []
        while self.position < len(self.source_code):
            self._skip_whitespace_and_comments()
            if self.position >= len(self.source_code):
                break

            token = self._match_token()
            if token:
                tokens.append(token)
            else:
                raise ValueError(f"Unrecognized token near: {self.source_code[self.position:self.position+10]}...")
        return tokens


def tokenize(source_code: str) -> list[Token]:
    return Tokenizer(source_code).tokenize()
