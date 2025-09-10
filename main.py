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
    ("HEX_NUMBER", r"0[xX][0-9a-fA-F]+"),
    ("OCT_NUMBER", r"0[0-7]+"),
    ("NUMBER", r"\d+"),
    ("CHAR", r"'(\\.|[^\\'])'"),
    ("STRING", r"\"([^\"\\]|\\.)*\""),
    ("INVALID_ID", r"\d[A-Za-z0-9_]*"),  # ID que começa com número
    ("INVALID_FLOAT", r"\d+,\d+"),       # Float com vírgula
    ("ID", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("LOGICAL_OP", r"&&|\|\||!"),
    ("OP", r"==|!=|<=|>=|\+=|\-=|\*=|\/=|%=|<<|>>|\+\+|\-\-|\?|:|&|\||\^|[+\-*/%<>=~.]"),
    ("DELIM", r"[;,(){}[\]]"),
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
                tokens.append((value, value, "Palavra-chave"))
            else:
                if value not in symbol_table:
                    symbol_table[value] = {"index": symbol_index, "count": 1}
                    symbol_index += 1
                else:
                    symbol_table[value]["count"] += 1
                
                attr = f"ID,{symbol_table[value]['index']}"
                tokens.append(("ID", value, attr))
        
        elif kind in ("NUMBER", "OCT_NUMBER", "HEX_NUMBER"):
            tokens.append(("INT", value, value))
        elif kind == "FLOAT":
            tokens.append(("FLOAT", value, value))
        elif kind == "CHAR":
            tokens.append(("CHAR", value, value[1]))
        elif kind == "STRING":
            tokens.append(("STRING", value, value[1:-1]))

        elif kind == "INVALID_ID":
            tokens.append(("ERROR", value, "ID inválido: começa com número"))
        elif kind == "INVALID_FLOAT":
            tokens.append(("ERROR", value, "Float inválido: usa vírgula"))
        
        elif kind in ("COMMENT_LINE", "COMMENT_BLOCK", "SKIP", "NEWLINE"):
            continue

        elif kind == "MISMATCH":
            tokens.append(("ERROR", value, "Token não reconhecido"))
        
        else:
            tokens.append((kind, value, "Sem atributo"))

    return tokens, symbol_table

def print_tokens(tokens):
    print("\n=== LISTA DE TOKENS ===")
    headers = ["TIPO", "LEXEMA", "ATRIBUTO"]
    print(tabulate(tokens, headers=headers, tablefmt="fancy_grid"))

def print_symbol_table(symbols):
    print("\n=== TABELA DE SÍMBOLOS ===")
    headers = ["#", "IDENTIFICADOR", "OCORRÊNCIAS"]
    table = [[symbol['index'], ident, symbol['count']] for ident, symbol in symbols.items()]
    print(tabulate(table, headers=headers, tablefmt="fancy_grid"))

if __name__ == "__main__":
    code = """
#include <stdio.h>

// Programa para calcular a área de um círculo


int main() {
    float raio = 5.0; // raio do círculo
    const float PI = 3.14159;
    
    float area;
    
    // Calcula a área
    area = PI * raio * raio;
    
    printf("A área do círculo é: %f\n", area);
    
    return 0;
}
    """
    tokens, symbols = lexer(code)
    print_tokens(tokens)
    print_symbol_table(symbols)