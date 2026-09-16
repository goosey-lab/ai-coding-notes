from dataclasses import dataclass

from .errors import CalcError


@dataclass
class Token:
    kind: str  # NUMBER, OP, LPAREN, RPAREN or END
    value: object


def tokenize(text):
    tokens = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            i += 1
        elif ch.isdigit():
            j = i
            while j < len(text) and text[j].isdigit():
                j += 1
            tokens.append(Token("NUMBER", int(text[i:j])))
            i = j
        elif ch in "+-*/":
            tokens.append(Token("OP", ch))
            i += 1
        elif ch == "(":
            tokens.append(Token("LPAREN", ch))
            i += 1
        elif ch == ")":
            tokens.append(Token("RPAREN", ch))
            i += 1
        else:
            raise CalcError(f"unexpected character {ch!r}")
    tokens.append(Token("END", None))
    return tokens
