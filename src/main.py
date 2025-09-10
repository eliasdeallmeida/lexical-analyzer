import re
from tabulate import tabulate
from typing import List, Tuple, Dict, Any

class Lexer:
    def __init__(self, source: str):
        self.src = source
        self.tokens: List[Tuple[str,str,Any,int,int]] = []  # (tipo, lexema, attr, line, col)
        self.symbols: Dict[str, Dict[str,Any]] = {}        # name -> {"id": "idN", "count": n}
        self.next_id = 1

        # keywords (>=20)
        self.keywords = {
            "int","float","double","char","void","if","else","while","for","return",
            "switch","case","default","break","continue","struct","union","enum",
            "typedef","const","static","extern","goto","sizeof"
        }

        # operadores agrupados (usados apenas para categorizar)
        self.operators_map = {
            "ARITH_OP": {"+","-","*","/","%"},
            "REL_OP": {"==","!=","<","<=",">",">="},
            "LOGIC_OP": {"&&","||","!"},
            "BIT_OP": {"&","|","^","~","<<",">>"},
            "ASSIGN_OP": {"=","+=","-=","*=","/=","%=","&=","|=","^=","<<=",">>="},
            "INCDEC": {"++","--"},
            "ARROW": {"->"},
            "ELLIPSIS": {"..."},
            "TERNARY": {"?",":"},
        }

        # delimiters more explicit
        self.delimiters_map = {
            "LPAREN": {"("}, "RPAREN": {")"},
            "LBRACE": {"{"}, "RBRACE": {"}"},
            "LBRACKET": {"["}, "RBRACKET": {"]"},
            "SEMICOLON": {";"},
            "COMMA": {","},
            "DOT": {"."},
        }

        # Build flattened lookup for categorize function
        self.flat_op_to_cat = {}
        for cat, s in self.operators_map.items():
            for lex in s:
                self.flat_op_to_cat[lex] = cat
        for cat, s in self.delimiters_map.items():
            for lex in s:
                self.flat_op_to_cat[lex] = cat

        # token specification (order matters)
        token_specification = [
            # PP_DIRECTIVE: only at start of line (allow leading spaces/tabs) -> match until EOL
            ("PP_DIRECTIVE", r"^[ \t]*\#.*"),

            # comments (block first, allow newlines inside)
            ("COMMENT_BLOCK", r"/\*[\s\S]*?\*/"),
            ("COMMENT_LINE", r"//.*"),

            # strings and chars (no real newline inside)
            ("STRING", r"\"(?:\\.|[^\"\\\n])*\""),
            ("CHAR",   r"'(?:\\.|[^'\\\n])'"),

            # special error patterns BEFORE numeric tokens:
            ("NUM_ID_ERROR", r"\d+[A-Za-z_][A-Za-z0-9_]*"),   # 123abc -> ERROR
            ("NUMBER_COMMA", r"\d+,\d+"),                    # 3,14 -> ERROR

            # ellipsis and multi-char op tokens first
            ("ELLIPSIS", r"\.\.\."),
            ("OP_3", r"<<=|>>="),

            # 2-char ops (order long first isn't necessary after building the alternation)
            ("OP_2", r"==|!=|<=|>=|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<|>>|&&|\|\||\+\+|--|->"),

            # single-char operators and delimiters (includes '?',':')
            ("OP_1", r"[+\-*/%<>=!&|^~?:]"),
            ("DELIM", r"[()\[\]{};,\.]"),

            # numbers (float then int)
            ("FLOAT", r"\d+\.\d+"),
            ("INT",   r"\d+"),

            # identifier
            ("ID",    r"[A-Za-z_][A-Za-z0-9_]*"),

            # whitespace/newlines
            ("NEWLINE", r"\n+"),
            ("SKIP",    r"[ \t]+"),

            # any other single char (mismatch/error)
            ("MISMATCH", r"."),
        ]

        # compile combined regex with MULTILINE so ^ works for PP_DIRECTIVE
        self.tok_regex = re.compile(
            "|".join("(?P<%s>%s)" % pair for pair in token_specification),
            re.MULTILINE
        )

    def get_line_col(self, pos: int) -> (int,int):
        # line is 1-based
        line = self.src.count('\n', 0, pos) + 1
        last_nl = self.src.rfind('\n', 0, pos)
        col = pos - last_nl
        return line, col

    def categorize_op_or_delim(self, lexeme: str) -> str:
        return self.flat_op_to_cat.get(lexeme, "UNKNOWN_OP_DELIM")

    def add_symbol(self, name: str) -> str:
        if name not in self.symbols:
            assigned = f"id{self.next_id}"
            self.symbols[name] = {"id": assigned, "count": 1}
            self.next_id += 1
            return assigned
        else:
            self.symbols[name]["count"] += 1
            return self.symbols[name]["id"]

    def tokenize(self):
        for mo in self.tok_regex.finditer(self.src):
            kind = mo.lastgroup
            lexeme = mo.group()
            start = mo.start()
            line, col = self.get_line_col(start)

            # skip comments and whitespace/newlines (but keep newline for line counting already handled)
            if kind in ("COMMENT_BLOCK","COMMENT_LINE","SKIP","NEWLINE"):
                continue

            # PP directive (keep full matched line, trim right)
            if kind == "PP_DIRECTIVE":
                self.tokens.append(("PP_DIRECTIVE", lexeme.rstrip("\r\n"), None, line, col))
                continue

            # errors from specific patterns
            if kind == "NUM_ID_ERROR":
                self.tokens.append(("ERROR", lexeme, "identificador não pode começar com número", line, col))
                continue
            if kind == "NUMBER_COMMA":
                self.tokens.append(("ERROR", lexeme, "vírgula como separador decimal (use ponto)", line, col))
                continue

            if kind == "STRING":
                # If regex matched, it's a syntactically closed string (no newline inside).
                # We could still unescape here if desired.
                content = lexeme[1:-1]
                self.tokens.append(("STRING_LITERAL", lexeme, content, line, col))
                continue

            if kind == "CHAR":
                content = lexeme[1:-1]
                self.tokens.append(("CHAR_LITERAL", lexeme, content, line, col))
                continue

            if kind == "FLOAT":
                try:
                    val = float(lexeme)
                    self.tokens.append(("FLOAT_LITERAL", lexeme, val, line, col))
                except Exception:
                    self.tokens.append(("ERROR", lexeme, "float inválido", line, col))
                continue

            if kind == "INT":
                # integers are fine
                try:
                    val = int(lexeme)
                    self.tokens.append(("INT_LITERAL", lexeme, val, line, col))
                except Exception:
                    self.tokens.append(("ERROR", lexeme, "inteiro inválido", line, col))
                continue

            if kind == "ID":
                if lexeme in self.keywords:
                    self.tokens.append(("KEYWORD", lexeme, None, line, col))
                else:
                    assigned_id = self.add_symbol(lexeme)
                    self.tokens.append(("IDENTIFIER", lexeme, assigned_id, line, col))
                continue

            # operators / delimiters
            if kind in ("ELLIPSIS","OP_3","OP_2","OP_1","DELIM"):
                # normalize lexeme (no further processing)
                cat = self.categorize_op_or_delim(lexeme)
                # if not found in maps, still put a generic category
                if cat == "UNKNOWN_OP_DELIM":
                    # try to classify single-char delimiters
                    if lexeme in {"(",")","{","}","[","]"}:
                        cat = {
                            "(": "LPAREN","}":"RBRACE","{":"LBRACE",
                            ")":"RPAREN","[":"LBRACKET","]":"RBRACKET"
                        }.get(lexeme, "DELIM")
                    else:
                        cat = "DELIM" if re.fullmatch(r"[()\[\]{};,\.]", lexeme) else "OP"
                self.tokens.append((cat, lexeme, None, line, col))
                continue

            # fallback mismatch -> error
            if kind == "MISMATCH":
                self.tokens.append(("ERROR", lexeme, "caractere inesperado", line, col))
                continue

        # append EOF token
        eof_line, eof_col = self.get_line_col(len(self.src))
        self.tokens.append(("EOF", "", None, eof_line, eof_col))
        return self.tokens, self.symbols

    def pretty_print(self):
        # tokens table
        token_rows = []
        for ttype, lex, attr, line, col in self.tokens:
            token_rows.append([f"{line}:{col}", ttype, lex, attr if attr is not None else ""])
        print("\nTabela de Tokens:")
        print(tabulate(token_rows, headers=["Pos", "Tipo", "Lexema", "Atributo"], tablefmt="grid"))

        # symbols table sorted by numeric id
        sym_rows = []
        # sort by numeric part of id
        def id_key(item):
            n = int(item[1]["id"][2:]) if item[1]["id"].startswith("id") else 0
            return n
        for name, data in sorted(self.symbols.items(), key=id_key):
            sym_rows.append([data["id"], name, data["count"]])
        print("\nTabela de Símbolos:")
        print(tabulate(sym_rows, headers=["ID", "Identificador", "Ocorrências"], tablefmt="grid"))


# ---------------- teste ----------------
if __name__ == "__main__":
    code = r'''
#include <stdio.h>
#define PI 3.14

int main() {
    // comentário de linha
    char c = '\n';
    float x = 3.14;
    int y = 42;
    y += 5;
    if (x >= 2.0 && y != 0) {
        printf("valor: %d\n", y);
    }
    // erros propositais:
    float e1 = 3,14;   // vírgula no float
    int 123abc = 10;   // id começa com número
    char bad = 'ab';   // char com >1 (regex não casa -> será 'ab' como dois tokens MISMATCH/ERRORs)
    char s[] = "texto sem fechar
    a -> b;
    a ... b;
}
'''
    lexer = Lexer(code)
    lexer.tokenize()
    lexer.pretty_print()
