import re
from tabulate import tabulate
from typing import List, Tuple, Dict, Any

class Lexer:
    """
    Analisador Léxico para uma linguagem C-like.
    
    Responsável por converter um código fonte em uma sequência de tokens,
    identificando palavras-chave, identificadores, literais, operadores e erros.
    """

    # --- Configuração Estática (Melhora a Modularidade) ---
    _KEYWORDS = {
        "int", "float", "double", "char", "void", "if", "else", "while", "for", "return",
        "switch", "case", "default", "break", "continue", "struct", "union", "enum",
        "typedef", "const", "static", "extern", "goto", "sizeof"
    }

    _OPERATORS_MAP = {
        "ARITH_OP": {"+", "-", "*", "/", "%"},
        "REL_OP": {"==", "!=", "<", "<=", ">", ">="},
        "LOGIC_OP": {"&&", "||", "!"},
        "BIT_OP": {"&", "|", "^", "~", "<<", ">>"},
        "ASSIGN_OP": {"=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>="},
        "INCDEC": {"++", "--"},
        "ARROW": {"->"},
        "ELLIPSIS": {"..."},
        "TERNARY": {"?", ":"},
    }

    _DELIMITERS_MAP = {
        "LPAREN": {"("}, "RPAREN": {")"},
        "LBRACE": {"{"}, "RBRACE": {"}"},
        "LBRACKET": {"["}, "RBRACKET": {"]"},
        "SEMICOLON": {";"},
        "COMMA": {","},
        "DOT": {"."},
    }

    # --- Especificação dos Tokens (Ordem é Importante) ---
    _TOKEN_SPECIFICATION = [
        ("PP_DIRECTIVE", r"^[ \t]*\#.*"),
        ("COMMENT_BLOCK", r"/\*[\s\S]*?\*/"),
        ("COMMENT_LINE", r"//.*"),
        ("STRING", r'"(?:\\.|[^"\\])*"'),
        ("CHAR", r"'(?:\\.|[^'\\])?'"),
        ("ERROR_CHAR_MULTI", r"'.{2,}'"),
        ("ERROR_UNTERM_STRING", r'"(?:[^"/\n]|/(?![/*]))*'),
        ("ERROR_UNTERM_CHAR", r"'(?:[^'/\n]|/(?![/*]))*"),
        ("NUM_ID_ERROR", r"\d+[A-Za-z_][A-Za-z0-9_]*"),
        ("NUMBER_COMMA", r"\d+,\d+"),
        ("ELLIPSIS", r"\.\.\."),
        ("OP_3", r"<<=|>>="),
        ("OP_2", r"==|!=|<=|>=|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<|>>|&&|\|\||\+\+|--|->"),
        ("OP_1", r"[+\-*/%<>=!&|^~?:]"),
        ("DELIM", r"[()\[\]{};,\.]"),
        ("FLOAT", r"\d+\.\d+"),
        ("INT", r"\d+"),
        ("ID", r"[A-Za-z_][A-Za-z0-9_]*"),
        ("NEWLINE", r"\n+"),
        ("SKIP", r"[ \t]+"),
        ("MISMATCH", r"."),
    ]

    def __init__(self, source: str):
        self.src = source
        self.tokens: List[Tuple[str, str, Any, int, int]] = []
        self.symbols: Dict[str, Dict[str, Any]] = {}
        self.next_id = 1

        # Compila o regex uma vez para otimizar a performance
        self.tok_regex = re.compile(
            "|".join(f"(?P<{pair[0]}>{pair[1]})" for pair in self._TOKEN_SPECIFICATION),
            re.MULTILINE
        )

        # Mapeamento de operadores para suas categorias (para performance)
        self._flat_op_to_cat = self._build_flat_op_map()

        # Mapeamento de tipos de erro para mensagens (centraliza as mensagens)
        self._error_messages = {
            'ERROR_UNTERM_STRING': "string não terminada",
            'ERROR_UNTERM_CHAR': "literal de caractere não terminado",
            'ERROR_CHAR_MULTI': "literal de caractere com múltiplos caracteres",
            'NUM_ID_ERROR': "identificador não pode começar com número",
            'NUMBER_COMMA': "vírgula como separador decimal (use ponto)",
            'MISMATCH': "caractere inesperado",
        }

    @classmethod
    def _build_flat_op_map(cls) -> Dict[str, str]:
        """Cria um dicionário para categorizar operadores e delimitadores rapidamente."""
        flat_map = {}
        for cat, op_set in {**cls._OPERATORS_MAP, **cls._DELIMITERS_MAP}.items():
            for op in op_set:
                flat_map[op] = cat
        return flat_map

    def tokenize(self) -> Tuple[List[Any], Dict[str, Any]]:
        """
        Executa a análise léxica no código fonte.

        Itera sobre todas as correspondências encontradas pelo regex compilado,
        ignora o que não é relevante (comentários, espaços) e despacha
        cada token para o método de tratamento apropriado.
        """
        for mo in self.tok_regex.finditer(self.src):
            kind = mo.lastgroup
            
            if kind in ("COMMENT_BLOCK", "COMMENT_LINE", "SKIP", "NEWLINE"):
                continue

            lexeme = mo.group()
            line, col = self._get_line_col(mo.start())
            
            # --- Despacho de Handlers (Melhora a Legibilidade) ---
            if kind.startswith("ERROR"):
                self._handle_error(kind, lexeme, line, col)
            elif kind in ("STRING", "CHAR"):
                self._handle_literal(kind, lexeme, line, col)
            elif kind in ("FLOAT", "INT"):
                self._handle_numeric_literal(kind, lexeme, line, col)
            elif kind == "ID":
                self._handle_identifier(lexeme, line, col)
            elif kind == "PP_DIRECTIVE":
                self._handle_pp_directive(lexeme, line, col)
            else: # Operadores e Delimitadores
                self._handle_operator(lexeme, line, col)

        # Adiciona token de Fim de Arquivo (EOF)
        eof_line, eof_col = self._get_line_col(len(self.src))
        self._add_token("EOF", "", None, eof_line, eof_col)
        
        return self.tokens, self.symbols

    # --- Métodos de Tratamento (Handlers) ---

    def _add_token(self, ttype: str, lexeme: str, attr: Any, line: int, col: int):
        """Adiciona um token formatado à lista de tokens."""
        self.tokens.append((ttype, lexeme, attr, line, col))

    def _handle_error(self, kind: str, lexeme: str, line: int, col: int):
        message = self._error_messages.get(kind, "Erro desconhecido")
        self._add_token("ERROR", lexeme, message, line, col)

    def _handle_literal(self, kind: str, lexeme: str, line: int, col: int):
        ttype = "STRING_LITERAL" if kind == "STRING" else "CHAR_LITERAL"
        content = lexeme[1:-1]
        self._add_token(ttype, lexeme, content, line, col)

    def _handle_numeric_literal(self, kind: str, lexeme: str, line: int, col: int):
        try:
            if kind == "FLOAT":
                val = float(lexeme)
                self._add_token("FLOAT_LITERAL", lexeme, val, line, col)
            else: # INT
                val = int(lexeme)
                self._add_token("INT_LITERAL", lexeme, val, line, col)
        except ValueError:
            msg = "float inválido" if kind == "FLOAT" else "inteiro inválido"
            self._add_token("ERROR", lexeme, msg, line, col)
    
    def _handle_identifier(self, lexeme: str, line: int, col: int):
        if lexeme in self._KEYWORDS:
            self._add_token("KEYWORD", lexeme, None, line, col)
        else:
            assigned_id = self._add_symbol(lexeme)
            self._add_token("IDENTIFIER", lexeme, assigned_id, line, col)

    def _handle_pp_directive(self, lexeme: str, line: int, col: int):
        self._add_token("PP_DIRECTIVE", lexeme.rstrip("\r\n"), None, line, col)

    def _handle_operator(self, lexeme: str, line: int, col: int):
        cat = self._flat_op_to_cat.get(lexeme, "UNKNOWN_OP_DELIM")
        self._add_token(cat, lexeme, None, line, col)

    # --- Métodos Auxiliares ---

    def _get_line_col(self, pos: int) -> Tuple[int, int]:
        """Calcula a linha e coluna (1-based) para uma dada posição no código."""
        line = self.src.count('\n', 0, pos) + 1
        last_nl = self.src.rfind('\n', 0, pos)
        col = (pos - last_nl) if last_nl != -1 else pos + 1
        return line, col

    def _add_symbol(self, name: str) -> str:
        """Adiciona um novo identificador à tabela de símbolos ou incrementa a contagem."""
        if name not in self.symbols:
            assigned_id = f"id{self.next_id}"
            self.symbols[name] = {"id": assigned_id, "count": 1}
            self.next_id += 1
        else:
            self.symbols[name]["count"] += 1
        return self.symbols[name]["id"]

    def pretty_print(self):
        """Imprime as tabelas de tokens e de símbolos de forma legível."""
        # Tabela de Tokens
        token_rows = [
            [f"{line}:{col}", ttype, lex, attr if attr is not None else ""]
            for ttype, lex, attr, line, col in self.tokens
        ]
        print("\nTabela de Tokens:")
        print(tabulate(token_rows, headers=["Pos", "Tipo", "Lexema", "Atributo"], tablefmt="grid"))

        # Tabela de Símbolos
        def id_key(item):
            return int(item[1]["id"][2:]) if item[1]["id"].startswith("id") else 0
        
        sorted_symbols = sorted(self.symbols.items(), key=id_key)
        sym_rows = [
            [data["id"], name, data["count"]]
            for name, data in sorted_symbols
        ]
        print("\nTabela de Símbolos:")
        print(tabulate(sym_rows, headers=["ID", "Identificador", "Ocorrências"], tablefmt="grid"))


# ---------------- Bloco de Teste ----------------
if __name__ == "__main__":
    code = r'''
#include <stdio.h>
#define PI 3.14

int main() {
    // Casos válidos
    char c = '\n';
    char empty_c = '';    // char vazio (agora válido)
    char s_vazia[] = "";  // string vazia (sempre foi válida)
    float x = 3.14;
    int y = 42;
    y += 5;
    if (x >= 2.0 && y != 0) {
        printf("valor: %d\n", y);
    }
    // erros propositais:
    float e1 = 3,14;      // vírgula no float
    int 123abc = 10;      // id começa com número
    char bad_char = 'ab'; // char com >1 caractere
    char unterm_c = 'a;    // char não terminado
    char s[] = "texto sem fechar; // string nao terminada
    a -> b;
    a ... b;
}
'''
    lexer = Lexer(code)
    lexer.tokenize()
    lexer.pretty_print()
