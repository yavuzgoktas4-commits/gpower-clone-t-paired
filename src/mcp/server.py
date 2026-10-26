"""Thin Model Context Protocol (MCP) server exposing the 'power_analysis' tool.

Delegates all statistical computation directly to 'src.engine' without duplicating
any calculation logic, while enforcing the exact input schema and error contract
of CONTRACT.md 1.0.0 (Section 7).
"""

from __future__ import annotations

import json
import math
import sys
from typing import Any

from src import CONTRACT_VERSION, __version__
from src.engine.errors import ContractError, NoSolutionError, ValidationError
from src.engine.paired_t import calculate_t_paired

SUPPORTED_TEST = "t-paired"
MCP_PROTOCOL_VERSION = "2024-11-05"

ALLOWED_FIELDS = {
    "test",
    "mode",
    "tails",
    "dz",
    "alpha",
    "power",
    "n_total",
}

FIELD_ALIASES = {
    "n-total": "n_total",
    "n": "n_total",
}

POWER_ANALYSIS_TOOL_SCHEMA: dict[str, Any] = {
    "name": "power_analysis",
    "description": (
        "Statistical power and sample size calculation tool for K2 family: t-paired "
        "(Means: Difference between two dependent means - matched pairs), adhering to CONTRACT.md 1.0.0."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "test": {
                "type": "string",
                "description": "Statistical test family identifier (must be 't-paired').",
            },
            "mode": {
                "type": "string",
                "enum": ["a-priori", "post-hoc"],
                "description": "Analysis mode: 'a-priori' (solve for n_total) or 'post-hoc' (compute actual_power).",
            },
            "tails": {
                "type": "integer",
                "enum": [1, 2],
                "description": "Number of tails: 1 (one-tailed) or 2 (two-tailed).",
            },
            "dz": {
                "type": "number",
                "description": "Effect size dz in [-20.0, 20.0] (with |dz| >= 1e-5 in a-priori mode).",
            },
            "alpha": {
                "type": "number",
                "description": "Type I error probability alpha in [1e-7, 0.9999999].",
            },
            "power": {
                "type": "number",
                "description": "Target statistical power (1 - beta) in [1e-7, 0.9999999] for a-priori mode.",
            },
            "n_total": {
                "type": "integer",
                "description": "Total sample size N in [3, 2147483646] for post-hoc mode.",
            },
        },
        "required": ["test", "mode", "tails", "dz", "alpha"],
        "additionalProperties": False,
    },
}


def _coerce_int_strict(value: Any, field: str) -> int:
    """Validate and coerce an integer field strictly (matching CLI behavior)."""
    if isinstance(value, bool):
        raise ValidationError(
            f"Invalid integer value '{value}' for parameter '{field}'.",
            code="OUT_OF_RANGE",
            field=field,
        )
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        try:
            return int(text)
        except ValueError:
            raise ValidationError(
                f"Invalid integer value '{value}' for parameter '{field}'.",
                code="OUT_OF_RANGE",
                field=field,
            )
    raise ValidationError(
        f"Parameter '{field}' must be an integer, got '{value}'.",
        code="OUT_OF_RANGE",
        field=field,
    )


def _coerce_float_strict(value: Any, field: str) -> float:
    """Validate and coerce a float field strictly (matching CLI behavior)."""
    if isinstance(value, bool):
        raise ValidationError(
            f"Invalid numeric value '{value}' for parameter '{field}'.",
            code="OUT_OF_RANGE",
            field=field,
        )
    if isinstance(value, (int, float)):
        fval = float(value)
    elif isinstance(value, str):
        try:
            fval = float(value.strip())
        except ValueError:
            raise ValidationError(
                f"Invalid numeric value '{value}' for parameter '{field}'.",
                code="OUT_OF_RANGE",
                field=field,
            )
    else:
        raise ValidationError(
            f"Invalid numeric value '{value}' for parameter '{field}'.",
            code="OUT_OF_RANGE",
            field=field,
        )

    if math.isnan(fval) or math.isinf(fval):
        raise ValidationError(
            f"Parameter '{field}' must be a finite floating-point number.",
            code="OUT_OF_RANGE",
            field=field,
        )
    return fval


def power_analysis_with_status(
    arguments: dict[str, Any] | None = None,
    **kwargs: Any,
) -> tuple[int, dict[str, Any]]:
    """Execute the 'power_analysis' tool and return (exit_code, response_dict).

    exit_code matches the CLI contract:
      0: Success
      1: NO_SOLUTION
      2: Validation error (OUT_OF_RANGE, INCONSISTENT, MISSING_PARAM, UNKNOWN_PARAM, UNSUPPORTED)
    """
    raw_params: dict[str, Any] = {}
    if arguments is not None:
        if not isinstance(arguments, dict):
            err = ValidationError("Arguments must be a JSON object.", code="UNKNOWN_PARAM", field="arguments")
            return err.exit_code, err.to_dict()
        raw_params.update(arguments)
    if kwargs:
        raw_params.update(kwargs)

    try:
        normalized_params: dict[str, Any] = {}
        unknown_fields: list[str] = []

        for key, val in raw_params.items():
            if val is None:
                continue
            canonical = FIELD_ALIASES.get(key, key)
            if canonical in ALLOWED_FIELDS:
                normalized_params[canonical] = val
            else:
                unknown_fields.append(key.lstrip("-").replace("-", "_"))

        # 1. Check 'test' first so unsupported test families always report UNSUPPORTED
        if "test" not in normalized_params or str(normalized_params["test"]).strip() == "":
            raise ValidationError(
                "Missing required parameter 'test'.",
                code="MISSING_PARAM",
                field="test",
            )

        test_family = str(normalized_params["test"]).strip()
        if test_family != SUPPORTED_TEST:
            raise ValidationError(
                f"Unsupported test family '{test_family}'. This build supports only '{SUPPORTED_TEST}'.",
                code="UNSUPPORTED",
                field="test",
            )

        # 2. Check unknown parameters
        if unknown_fields:
            bad_field = unknown_fields[0]
            raise ValidationError(
                f"Unknown parameter '{bad_field}' for test family '{SUPPORTED_TEST}'.",
                code="UNKNOWN_PARAM",
                field=bad_field,
            )

        # 3. Check 'mode'
        if "mode" not in normalized_params or str(normalized_params["mode"]).strip() == "":
            raise ValidationError(
                "Missing required parameter 'mode'.",
                code="MISSING_PARAM",
                field="mode",
            )

        raw_mode = str(normalized_params["mode"]).strip()
        normalized_mode = raw_mode.lower().replace("_", "-")
        if normalized_mode not in ("a-priori", "post-hoc"):
            raise ValidationError(
                f"Unsupported mode '{raw_mode}'. Supported modes are 'a-priori' and 'post-hoc'.",
                code="UNSUPPORTED",
                field="mode",
            )

        # 4. Check mode-incompatible parameters
        if normalized_mode == "a-priori" and "n_total" in normalized_params:
            raise ValidationError(
                "Parameter 'n_total' is not allowed in 'a-priori' mode.",
                code="INCONSISTENT",
                field="n_total",
            )
        if normalized_mode == "post-hoc" and "power" in normalized_params:
            raise ValidationError(
                "Parameter 'power' is not allowed in 'post-hoc' mode.",
                code="INCONSISTENT",
                field="power",
            )

        # 5. Check required common parameters
        for req_field in ("tails", "dz", "alpha"):
            if req_field not in normalized_params or normalized_params[req_field] == "":
                raise ValidationError(
                    f"Missing required parameter '{req_field}'.",
                    code="MISSING_PARAM",
                    field=req_field,
                )

        # 6. Check required mode-specific parameter
        if normalized_mode == "a-priori" and (
            "power" not in normalized_params or normalized_params["power"] == ""
        ):
            raise ValidationError(
                "Missing required parameter 'power' for 'a-priori' mode.",
                code="MISSING_PARAM",
                field="power",
            )
        if normalized_mode == "post-hoc" and (
            "n_total" not in normalized_params or normalized_params["n_total"] == ""
        ):
            raise ValidationError(
                "Missing required parameter 'n_total' for 'post-hoc' mode.",
                code="MISSING_PARAM",
                field="n_total",
            )

        # 7. Parse numeric types
        tails = _coerce_int_strict(normalized_params["tails"], "tails")
        dz = _coerce_float_strict(normalized_params["dz"], "dz")
        alpha = _coerce_float_strict(normalized_params["alpha"], "alpha")
        power = (
            _coerce_float_strict(normalized_params["power"], "power")
            if "power" in normalized_params
            else None
        )
        n_total = (
            _coerce_int_strict(normalized_params["n_total"], "n_total")
            if "n_total" in normalized_params
            else None
        )

        # 8. Delegate calculation directly to src.engine
        result = calculate_t_paired(
            mode=normalized_mode,
            tails=tails,
            dz=dz,
            alpha=alpha,
            power=power,
            n_total=n_total,
        )
        return 0, result.to_dict()

    except ContractError as exc:
        return exc.exit_code, exc.to_dict()
    except Exception as exc:
        err = NoSolutionError(f"Numerical calculation error: {exc}", field="n_total")
        return err.exit_code, err.to_dict()


def power_analysis(arguments: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Invoke the 'power_analysis' MCP tool and return its JSON-serializable payload dict."""
    _, payload = power_analysis_with_status(arguments=arguments, **kwargs)
    return payload


def handle_mcp_request(request: dict[str, Any]) -> dict[str, Any] | None:
    """Process a single JSON-RPC 2.0 MCP message and return a response dict (or None for notifications)."""
    method = request.get("method")
    req_id = request.get("id")
    params = request.get("params") or {}

    # Notifications have no 'id'
    if req_id is None:
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False},
                },
                "serverInfo": {
                    "name": "gpower-clone-mcp",
                    "version": __version__,
                    "contract_version": CONTRACT_VERSION,
                },
            },
        }

    if method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {},
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [POWER_ANALYSIS_TOOL_SCHEMA],
            },
        }

    if method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments") or {}

        if tool_name != "power_analysis":
            err_payload = {
                "error": f"Unknown MCP tool '{tool_name}'. Only 'power_analysis' is supported.",
                "code": "UNKNOWN_PARAM",
                "field": str(tool_name or "name"),
            }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(err_payload, ensure_ascii=False),
                        }
                    ],
                    "structuredContent": err_payload,
                    "isError": True,
                },
            }

        status_code, payload = power_analysis_with_status(tool_args)
        json_text = json.dumps(payload, ensure_ascii=False)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json_text,
                    }
                ],
                "structuredContent": payload,
                "isError": status_code != 0,
            },
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}",
        },
    }


class MCPServer:
    """Standard-library JSON-RPC 2.0 stdio MCP server hosting 'power_analysis'."""

    def list_tools(self) -> list[dict[str, Any]]:
        return [POWER_ANALYSIS_TOOL_SCHEMA]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        resp = handle_mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        assert resp is not None
        return resp["result"]

    def serve_stdio(self) -> int:
        """Run the JSON-RPC 2.0 line-delimited stdio loop."""
        for raw_line in sys.stdin:
            line = raw_line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError as exc:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {exc}"},
                }
                sys.stdout.write(json.dumps(err_resp, ensure_ascii=False) + "\n")
                sys.stdout.flush()
                continue

            resp = handle_mcp_request(req)
            if resp is not None:
                sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        return 0


def main() -> None:
    """Entry point for running the MCP server over stdio (python -m src.mcp.server)."""
    server = MCPServer()
    sys.exit(server.serve_stdio())


if __name__ == "__main__":
    main()
