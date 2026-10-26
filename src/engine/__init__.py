"""Statistical calculation engine package."""

from src.engine.errors import ContractError, NoSolutionError, ValidationError
from src.engine.paired_t import (
    PairedTResult,
    calculate_post_hoc,
    calculate_t_paired,
    compute_critical_t,
    compute_df,
    compute_ncp,
    round_sample_size,
    solve_a_priori,
    validate_inputs,
)

__all__ = [
    "ContractError",
    "NoSolutionError",
    "PairedTResult",
    "ValidationError",
    "calculate_post_hoc",
    "calculate_t_paired",
    "compute_critical_t",
    "compute_df",
    "compute_ncp",
    "round_sample_size",
    "solve_a_priori",
    "validate_inputs",
]
