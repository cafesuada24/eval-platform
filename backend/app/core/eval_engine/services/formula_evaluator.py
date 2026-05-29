"""Formula evaluator service."""

import ast
import math
import operator
from typing import Final

type Formula = str
type Numeric = int | float
type VarBindings = dict[str, Numeric]


# --- FORMULA EVALUATOR SRV ---


SAFE_GLOBALS: Final = {
    'pi': math.pi,
    'e': math.e,
    'sin': math.sin,
    'cos': math.cos,
    'sqrt': math.sqrt,
    'abs': abs,
    'min': min,
    'max': max,
}

BIN_OPS: Final = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}


UNARY_OPS: Final = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class FormulaEvaluatorService:
    """A formula evaluator."""

    def get_required_variables(
        self,
        formula: Formula,
    ) -> list[str]:
        """Get required variables from a formula."""
        tree = ast.parse(
            formula,
            mode='eval',
        )

        variables: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id not in SAFE_GLOBALS:
                variables.add(node.id)

        return sorted(variables)

    def evaluate_formula(
        self,
        formula: Formula,
        var_bind: VarBindings,
    ) -> float:
        """Evaluate a formula."""
        tree = ast.parse(
            formula,
            mode='eval',
        )

        evaluator = _Evaluator(var_bind)

        result = evaluator.visit(tree)

        return float(result)


class _Evaluator(ast.NodeVisitor):
    def __init__(
        self,
        variables: VarBindings,
    ) -> None:
        self.variables = variables

    def visit_Expression(
        self,
        node: ast.Expression,
    ) -> Numeric:
        return self.visit(node.body)

    def visit_Constant(
        self,
        node: ast.Constant,
    ) -> Numeric:
        if isinstance(
            node.value,
            (int, float),
        ):
            return node.value

        raise TypeError('Invalid constant')

    def visit_Name(
        self,
        node: ast.Name,
    ) -> Numeric:
        if node.id in self.variables:
            return self.variables[node.id]

        if node.id in SAFE_GLOBALS:
            value = SAFE_GLOBALS[node.id]

            if isinstance(
                value,
                (int, float),
            ):
                return value

        raise NameError(node.id)

    def visit_BinOp(
        self,
        node: ast.BinOp,
    ) -> Numeric:
        op = BIN_OPS[type(node.op)]

        return op(
            self.visit(node.left),
            self.visit(node.right),
        )

    def visit_UnaryOp(
        self,
        node: ast.UnaryOp,
    ) -> Numeric:
        op = UNARY_OPS[type(node.op)]

        return op(self.visit(node.operand))

    def visit_Call(
        self,
        node: ast.Call,
    ) -> Numeric:
        if not isinstance(
            node.func,
            ast.Name,
        ):
            raise TypeError('Invalid function call')

        func = SAFE_GLOBALS.get(node.func.id)

        if not callable(func):
            raise NameError(node.func.id)

        args = [self.visit(arg) for arg in node.args]

        return func(*args)

    def generic_visit(
        self,
        node: ast.AST,
    ):
        raise TypeError(f'Unsupported syntax: {type(node).__name__}')





