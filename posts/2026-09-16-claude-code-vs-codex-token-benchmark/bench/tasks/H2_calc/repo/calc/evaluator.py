from .errors import CalcError
from .nodes import BinOp, Num


def evaluate_node(node):
    if isinstance(node, Num):
        return node.value
    if isinstance(node, BinOp):
        left = evaluate_node(node.left)
        right = evaluate_node(node.right)
        if node.op == "+":
            return left + right
        if node.op == "-":
            return left - right
        if node.op == "*":
            return left * right
        if node.op == "/":
            if right == 0:
                raise CalcError("division by zero")
            return left / right
    raise CalcError(f"cannot evaluate {node!r}")
