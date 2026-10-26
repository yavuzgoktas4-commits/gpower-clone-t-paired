"""CLI entry point for gpower-clone adhering strictly to CONTRACT.md 1.0.0."""

from __future__ import annotations

import json
import math
import sys
from typing import Optional, Sequence

from src import CONTRACT_VERSION, __version__
from src.engine.errors import ContractError, NoSolutionError, ValidationError
from src.engine.paired_t import calculate_t_paired

SUPPORTED_TEST = "t-paired"

KNOWN_FLAGS_MAP: dict[str, str] = {
    "--test": "test",
    "--mode": "mode",
    "--tails": "tails",
    "--dz": "dz",
    "--alpha": "alpha",
    "--power": "power",
    "--n-total": "n_total",
    "--n_total": "n_total",
    "--n": "n_total",
}


def _emit_json(payload: dict[str, object]) -> None:
    """Write a single-line JSON object to stdout."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _parse_int_strict(raw: str, field: str) -> int:
    """Parse an integer parameter strictly, rejecting floats or non-numeric strings."""
    text = raw.strip()
    try:
        val = int(text)
    except ValueError:
        try:
            fval = float(text)
            if math.isfinite(fval) and fval.is_integer():
                raise ValidationError(
                    f"Parameter '{field}' must be an integer, got '{raw}'.",
                    code="OUT_OF_RANGE",
                    field=field,
                )
        except ValueError:
            pass
        raise ValidationError(
            f"Invalid integer value '{raw}' for parameter '{field}'.",
            code="OUT_OF_RANGE",
            field=field,
        )
    return val


def _parse_float_strict(raw: str, field: str) -> float:
    """Parse a floating-point parameter strictly, rejecting NaN and Inf."""
    text = raw.strip()
    try:
        val = float(text)
    except ValueError:
        raise ValidationError(
            f"Invalid numeric value '{raw}' for parameter '{field}'.",
            code="OUT_OF_RANGE",
            field=field,
        )
    if math.isnan(val) or math.isinf(val):
        raise ValidationError(
            f"Parameter '{field}' must be a finite floating-point number.",
            code="OUT_OF_RANGE",
            field=field,
        )
    return val


def _parse_cli_tokens(argv: Sequence[str]) -> tuple[bool, dict[str, str], list[tuple[str, str]]]:
    """Tokenize CLI arguments into known fields and unknown flags.

    Returns (is_version_request, parsed_known_fields, unknown_flags).
    """
    if len(argv) == 1 and argv[0] in ("--version", "-v"):
        return True, {}, []

    if "--version" in argv or "-v" in argv:
        return True, {}, []

    known_values: dict[str, str] = {}
    unknown_flags: list[tuple[str, str]] = []

    i = 0
    n = len(argv)
    while i < n:
        token = argv[i]
        if not token.startswith("--") and not (token.startswith("-") and len(token) > 1 and not token[1].isdigit() and token[1] != "."):
            raise ValidationError(
                f"Unexpected positional argument '{token}'.",
                code="UNKNOWN_PARAM",
                field=token.lstrip("-") or "arg",
            )

        if "=" in token:
            flag, val = token.split("=", 1)
            if val == "":
                field_name = KNOWN_FLAGS_MAP.get(flag, flag.lstrip("-").replace("-", "_"))
                raise ValidationError(
                    f"Missing value for parameter '{field_name}'.",
                    code="MISSING_PARAM",
                    field=field_name,
                )
        else:
            flag = token
            if i + 1 >= n:
                field_name = KNOWN_FLAGS_MAP.get(flag, flag.lstrip("-").replace("-", "_"))
                raise ValidationError(
                    f"Missing value for parameter '{field_name}'.",
                    code="MISSING_PARAM",
                    field=field_name,
                )
            next_tok = argv[i + 1]
            # Check if next_tok is another flag (starts with '--' or non-numeric '-')
            if next_tok.startswith("--") or (
                next_tok.startswith("-")
                and len(next_tok) > 1
                and not next_tok[1].isdigit()
                and next_tok[1] != "."
            ):
                field_name = KNOWN_FLAGS_MAP.get(flag, flag.lstrip("-").replace("-", "_"))
                raise ValidationError(
                    f"Missing value for parameter '{field_name}'.",
                    code="MISSING_PARAM",
                    field=field_name,
                )
            val = next_tok
            i += 1

        if flag in KNOWN_FLAGS_MAP:
            canonical_field = KNOWN_FLAGS_MAP[flag]
            known_values[canonical_field] = val
        else:
            raw_field = flag.lstrip("-").replace("-", "_")
            unknown_flags.append((flag, raw_field))

        i += 1

    return False, known_values, unknown_flags


def run_cli(argv: Optional[Sequence[str]] = None) -> int:
    """Execute the CLI logic and return the process exit code (0, 1, or 2)."""
    args = list(sys.argv[1:] if argv is None else argv)

    try:
        is_version, known, unknown_flags = _parse_cli_tokens(args)
        if is_version:
            _emit_json(
                {
                    "name": "gpower-clone",
                    "version": __version__,
                    "contract_version": CONTRACT_VERSION,
                    "test": SUPPORTED_TEST,
                    "supported_tests": [SUPPORTED_TEST],
                }
            )
            return 0

        # 1. Validate --test first so unsupported test families always report UNSUPPORTED
        if "test" not in known:
            raise ValidationError(
                "Missing required parameter 'test'.",
                code="MISSING_PARAM",
                field="test",
            )

        test_family = known["test"].strip()
        if test_family != SUPPORTED_TEST:
            raise ValidationError(
                f"Unsupported test family '{test_family}'. This build supports only '{SUPPORTED_TEST}'.",
                code="UNSUPPORTED",
                field="test",
            )

        # 2. Check for any unknown parameters for t-paired
        if unknown_flags:
            flag_str, raw_field = unknown_flags[0]
            raise ValidationError(
                f"Unknown parameter '{flag_str}' for test family '{SUPPORTED_TEST}'.",
                code="UNKNOWN_PARAM",
                field=raw_field,
            )

        # 3. Validate --mode presence and supported values
        if "mode" not in known:
            raise ValidationError(
                "Missing required parameter 'mode'.",
                code="MISSING_PARAM",
                field="mode",
            )

        raw_mode = known["mode"].strip()
        normalized_mode = raw_mode.lower().replace("_", "-")
        if normalized_mode not in ("a-priori", "post-hoc"):
            raise ValidationError(
                f"Unsupported mode '{raw_mode}'. Supported modes are 'a-priori' and 'post-hoc'.",
                code="UNSUPPORTED",
                field="mode",
            )

        # 4. Check mode-incompatible parameters before missing parameters
        if normalized_mode == "a-priori" and "n_total" in known:
            raise ValidationError(
                "Parameter 'n_total' is not allowed in 'a-priori' mode.",
                code="INCONSISTENT",
                field="n_total",
            )
        if normalized_mode == "post-hoc" and "power" in known:
            raise ValidationError(
                "Parameter 'power' is not allowed in 'post-hoc' mode.",
                code="INCONSISTENT",
                field="power",
            )

        # 5. Check required common parameters
        for req_field in ("tails", "dz", "alpha"):
            if req_field not in known:
                raise ValidationError(
                    f"Missing required parameter '{req_field}'.",
                    code="MISSING_PARAM",
                    field=req_field,
                )

        # 6. Check required mode-specific parameter
        if normalized_mode == "a-priori" and "power" not in known:
            raise ValidationError(
                "Missing required parameter 'power' for 'a-priori' mode.",
                code="MISSING_PARAM",
                field="power",
            )
        if normalized_mode == "post-hoc" and "n_total" not in known:
            raise ValidationError(
                "Missing required parameter 'n_total' for 'post-hoc' mode.",
                code="MISSING_PARAM",
                field="n_total",
            )

        # 7. Parse numeric values
        tails = _parse_int_strict(known["tails"], "tails")
        dz = _parse_float_strict(known["dz"], "dz")
        alpha = _parse_float_strict(known["alpha"], "alpha")
        power = _parse_float_strict(known["power"], "power") if "power" in known else None
        n_total = _parse_int_strict(known["n_total"], "n_total") if "n_total" in known else None

        # 8. Execute statistical engine
        result = calculate_t_paired(
            mode=normalized_mode,
            tails=tails,
            dz=dz,
            alpha=alpha,
            power=power,
            n_total=n_total,
        )
        _emit_json(result.to_dict())
        return 0

    except ContractError as exc:
        _emit_json(exc.to_dict())
        return exc.exit_code
    except Exception as exc:  # Defensive catch-all for unexpected numerical failure
        err = NoSolutionError(f"Numerical calculation error: {exc}", field="n_total")
        _emit_json(err.to_dict())
        return err.exit_code


def main() -> None:
    """Console script entry point."""
    sys.exit(run_cli())


if __name__ == "__main__":
    main()
