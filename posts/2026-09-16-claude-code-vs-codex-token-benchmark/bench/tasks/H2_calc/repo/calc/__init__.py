"""A small arithmetic expression calculator."""
from .errors import CalcError
from .evaluator import evaluate_node
from .parser import parse


def evaluate(text):
    """Evaluate an arithmetic expression such as ``"2 * (3 + 4)"``."""
    return evaluate_node(parse(text))


__all__ = ["CalcError", "evaluate"]
