from .errors import CalcError
from .nodes import BinOp, Num
from .tokenizer import tokenize


class Parser:
    """Recursive-descent parser.

    expr   := term (('+' | '-') term)*
    term   := factor (('*' | '/') factor)*
    factor := NUMBER | '(' expr ')'
    """

    def __init__(self, text):
        self.tokens = tokenize(text)
        self.index = 0

    def peek(self):
        return self.tokens[self.index]

    def advance(self):
        token = self.tokens[self.index]
        self.index += 1
        return token

    def parse(self):
        node = self.expr()
        if self.peek().kind != "END":
            raise CalcError(f"unexpected token {self.peek().value!r}")
        return node

    def expr(self):
        node = self.term()
        while self.peek().kind == "OP" and self.peek().value in "+-":
            op = self.advance().value
            node = BinOp(op, node, self.term())
        return node

    def term(self):
        node = self.factor()
        while self.peek().kind == "OP" and self.peek().value in "*/":
            op = self.advance().value
            node = BinOp(op, node, self.factor())
        return node

    def factor(self):
        token = self.advance()
        if token.kind == "NUMBER":
            return Num(token.value)
        if token.kind == "LPAREN":
            node = self.expr()
            if self.advance().kind != "RPAREN":
                raise CalcError("expected ')'")
            return node
        raise CalcError(f"unexpected token {token.value!r}")


def parse(text):
    return Parser(text).parse()
