"""Core Calculator logic module."""

from typing import List, Dict, Any


class Calculator:
    """Performs arithmetic calculations and maintains computation history."""

    def __init__(self):
        self.history: List[Dict[str, Any]] = []

    def add(self, a: float, b: float) -> float:
        """Adds two numbers and records history."""
        result = a + b
        self._record("add", a, b, result)
        return result

    def subtract(self, a: float, b: float) -> float:
        """Subtracts b from a."""
        result = a - b
        self._record("subtract", a, b, result)
        return result

    def multiply(self, a: float, b: float) -> float:
        """Multiplies two numbers."""
        result = a * b
        self._record("multiply", a, b, result)
        return result

    def divide(self, a: float, b: float) -> float:
        """Divides a by b. Raises ValueError if b == 0."""
        if b == 0:
            raise ValueError("Division by zero is not allowed.")
        result = a / b
        self._record("divide", a, b, result)
        return result

    def power(self, base: float, exponent: float) -> float:
        """Raises base to the power of exponent."""
        result = base ** exponent
        self._record("power", base, exponent, result)
        return result

    def get_history(self) -> List[Dict[str, Any]]:
        """Returns the calculation history."""
        return list(self.history)

    def clear_history(self) -> None:
        """Clears all calculation history."""
        self.history.clear()

    def _record(self, op: str, a: float, b: float, res: float) -> None:
        self.history.append({"operation": op, "a": a, "b": b, "result": res})

