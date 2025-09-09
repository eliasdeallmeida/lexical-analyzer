import re
from tabulate import tabulate

KEYWORDS = {
    "int", "float", "char", "if", "else", "while", "return",
    "for", "do", "switch", "case", "break", "continue", 
    "void", "struct", "typedef", "static", "const", "enum"
}

token_specification = [
    ("PP_DIRECTIVE", r"#.*"),
    ("COMMENT_BLOCK", r"/\*.*?\*/"),
    ("COMMENT_LINE", r"//.*"),
    ("FLOAT", r"\d+\.\d+"),
    ("WRONG_FLOAT", r"\d+,\d+"),
    ("INT", r"\d+"),
    ("CHAR", r"'(\\.|[^\\'])'"),
    ("UNTERMINATED_STRING", r"\"([^\"\\]|\\.)*$"),
    ("STRING", r"\"([^\"\\]|\\.)*\""),
    ("ID", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("INVALID_ID", r"\d+[A-Za-z_][A-Za-z0-9_]*"),
    ("OP", r"==|!=|<=|>=|&&|\|\||[+\-*/%<>=!&|]"),
    ("DELIM", r"[;,\(\)\{\}\[\]]"),
    ("NEWLINE", r"\n"),
    ("SKIP", r"[ \t]+"),
    ("MISMATCH", r".")
]

token_re = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in token_specification))

def lexer(code):
    tokens = []
    symbol_table = {}

    for match in token_re.finditer(code):
        kind = match.lastgroup
        value = match.group()

        if kind == "ID":
            if value in KEYWORDS:
                tokens.append(("KEYWORD", value, "-"))
            else:
                tokens.append(("IDENTIFIER", value, "-"))
                symbol_table[value] = symbol_table.get(value, 0) + 1

        elif kind == "INVALID_ID":
            tokens.append(("ERROR", value, "Identificador inválido"))

        elif kind == "WRONG_FLOAT":
            tokens.append(("ERROR", value, "Separador decimal inválido"))

        elif kind == "UNTERMINATED_STRING":
            tokens.append(("ERROR", value, "String não terminada"))

        elif kind == "INT":
            tokens.append(("INT", value, int(value)))

        elif kind == "FLOAT":
            tokens.append(("FLOAT", value, float(value)))

        elif kind == "CHAR":
            tokens.append(("CHAR", value, value[1]))  # pega apenas o caractere

        elif kind == "STRING":
            tokens.append(("STRING", value, value[1:-1]))  # remove aspas

        elif kind in ("COMMENT_LINE", "COMMENT_BLOCK", "SKIP", "NEWLINE"):
            continue

        elif kind == "MISMATCH":
            tokens.append(("ERROR", value, "Caractere inesperado"))

        else:
            tokens.append((kind, value, "-"))

    return tokens, symbol_table


def print_tokens(tokens):
    print("\n=== LISTA DE TOKENS ===")
    headers = ["TIPO", "LEXEMA", "ATRIBUTO"]
    table = [list(t) for t in tokens]
    print(tabulate(table, headers=headers, tablefmt="fancy_grid"))


def print_symbol_table(symbols):
    print("\n=== TABELA DE SÍMBOLOS ===")
    headers = ["IDENTIFICADOR", "OCORRÊNCIAS"]
    table = [[ident, count] for ident, count in symbols.items()]
    print(tabulate(table, headers=headers, tablefmt="fancy_grid"))


# Exemplo de uso
if __name__ == "__main__":
    code = """
#include <stdio.h>

int main() {
    int x = 10;
    float y = 3.14;
    char c = 'z';
    if (x < y) {
        return 1;
    }
    return 0;
}
    """
    tokens, symbols = lexer(code)
    print_tokens(tokens)
    print_symbol_table(symbols)
