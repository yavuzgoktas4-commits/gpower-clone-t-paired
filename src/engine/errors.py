"""Contract-compliant exception definitions for the statistical engine and CLI."""

from __future__ import annotations


class ContractError(Exception):
    """Structured error adhering to CONTRACT.md 1.0.0."""

    def __init__(self, message: str, code: str, field: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.field = field
        self.exit_code = exit_code

    def to_dict(self) -> dict[str, str]:
        return {
            "error": self.message,
            "code": self.code,
            "field": self.field,
        }


class ValidationError(ContractError):
    """Input validation error (Exit Code 2)."""

    def __init__(self, message: str, code: str, field: str) -> None:
        super().__init__(message=message, code=code, field=field, exit_code=2)


class NoSolutionError(ContractError):
    """Numerical convergence or unsolvable root error (Exit Code 1)."""

    def __init__(self, message: str, field: str = "n_total") -> None:
        super().__init__(message=message, code="NO_SOLUTION", field=field, exit_code=1)
