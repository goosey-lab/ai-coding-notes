from dataclasses import dataclass


@dataclass
class Num:
    value: object


@dataclass
class BinOp:
    op: str
    left: object
    right: object
