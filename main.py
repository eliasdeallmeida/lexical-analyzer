import re
from tabulate import tabulate

# Palavras-chave da linguagem C
KEYWORDS = {
    "int", "float", "char", "if", "else", "while", "return",
    "for", "do", "switch", "case", "break", "continue",
    "void", "struct", "typedef", "const", "enum"
}

# Especificação de tokens
token_specification = [
    ("PP_DIRECTIVE", r"#.*"),
    ("COMMENT_BLOCK", r"/\*.*?\*/"),
    ("COMMENT_LINE", r"//.*"),
    ("FLOAT", r"\d+\.\d+"),
    ("INT", r"\d+"),
    ("CHAR", r"'(\\.|[^\\'])'"),
    ("STRING", r"\"([^\"\\]|\\.)*\""),
    ("ID", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("OP", r"==|!=|<=|>=|&&|\|\||[+\-*/%<>=!&|.]"),
    ("DELIM", r"[;,\(\)\{\}\[\]]"),
    ("NEWLINE", r"\n"),
    ("SKIP", r"[ \t]+"),
    ("MISMATCH", r".")
]

token_re = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in token_specification))

def lexer(code):
    tokens = []
    symbol_table = {}
    symbol_index = 1

    for match in token_re.finditer(code):
        kind = match.lastgroup
        value = match.group()

        if kind == "ID":
            if value in KEYWORDS:
                tokens.append((value, value))  # keyword
            else:
                if value not in symbol_table:
                    symbol_table[value] = symbol_index
                    symbol_index += 1
                tokens.append((f"id,{symbol_table[value]}", value))

        elif kind == "INT":
            tokens.append((f"num,{value}", value))  # atributo é o valor literal

        elif kind == "FLOAT":
            tokens.append((f"float,{value}", value))  # atributo é o valor literal

        elif kind == "CHAR":
            tokens.append((f"char,{value[1]}", value))

        elif kind == "STRING":
            tokens.append((f"string,{value[1:-1]}", value))

        elif kind in ("COMMENT_LINE", "COMMENT_BLOCK", "SKIP", "NEWLINE"):
            continue

        elif kind == "MISMATCH":
            tokens.append(("ERROR", value))

        else:
            tokens.append((value, value))  # operadores e delimitadores

    return tokens, symbol_table

def print_tokens(tokens):
    print("\n=== LISTA DE TOKENS ===")
    headers = ["TOKEN", "LEXEMA"]
    print(tabulate(tokens, headers=headers, tablefmt="fancy_grid"))

def print_symbol_table(symbols):
    print("\n=== TABELA DE SÍMBOLOS ===")
    headers = ["#", "IDENTIFICADOR"]
    table = [[idx, ident] for ident, idx in symbols.items()]
    print(tabulate(table, headers=headers, tablefmt="fancy_grid"))

if __name__ == "__main__":
    code = """
#include <stdio.h>

int main() {
    int a = 10, b = 4;
    float c = (float)a / b;
    printf("%f\\n", c);
    return 0;
}
    """
    tokens, symbols = lexer(code)
    print_tokens(tokens)
    print_symbol_table(symbols)
