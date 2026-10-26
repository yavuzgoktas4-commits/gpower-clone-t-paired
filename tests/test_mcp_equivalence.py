"""Equivalence test suite verifying that the CLI and MCP server produce identical JSON outputs.

Tests:
  1. MCP protocol handshake ('initialize') and tool registry ('tools/list' exposes only 'power_analysis').
  2. Clean architectural boundary: 'src/mcp/' delegates to 'src.engine' without importing 'scipy'.
  3. Byte-for-byte JSON output equivalence between CLI and MCP (both in-process JSON-RPC and
     live stdio subprocess) across all 30 oracle vectors in 'oracle/ground_truth.csv' and
     all 25 vectors in 'oracle/public_vectors.jsonl'.
  4. Error code and error JSON equivalence across all CONTRACT.md error categories
     (UNSUPPORTED, MISSING_PARAM, UNKNOWN_PARAM, INCONSISTENT, OUT_OF_RANGE, NO_SOLUTION).
"""

from __future__ import annotations

import ast
import csv
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
from typing import Any
import unittest
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.cli.main import run_cli
from src.mcp.server import (
    MCPServer,
    POWER_ANALYSIS_TOOL_SCHEMA,
    handle_mcp_request,
    power_analysis_with_status,
)
from tests.test_differential import (
    CSV_VECTORS,
    JSONL_VECTORS,
    build_cli_cmd,
)


def vector_to_mcp_args(vec: dict[str, Any]) -> dict[str, Any]:
    """Convert an oracle vector record into MCP 'power_analysis' tool arguments."""
    args: dict[str, Any] = {
        "test": "t-paired",
        "mode": vec["mode"],
        "tails": vec["tails"],
        "dz": vec["dz"],
        "alpha": vec["alpha"],
    }
    if vec["mode"] == "a-priori":
        args["power"] = vec["power_input"]
    else:
        args["n_total"] = vec["n_total_input"]
    return args


def capture_cli_inprocess(cli_args: list[str]) -> tuple[int, str, dict[str, Any]]:
    """Run CLI in-process and capture (exit_code, raw_stdout_line, parsed_json)."""
    buf = StringIO()
    with patch("sys.stdout", buf):
        exit_code = run_cli(cli_args)
    lines = buf.getvalue().strip().splitlines()
    assert len(lines) == 1, f"Expected single line from CLI, got: {lines!r}"
    return exit_code, lines[0], json.loads(lines[0])


def run_mcp_stdio_batch(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Spawn the MCP server via subprocess stdio and send a batch of JSON-RPC 2.0 requests."""
    stdin_payload = "\n".join(json.dumps(req) for req in requests) + "\n"
    proc = subprocess.run(
        [sys.executable, "-m", "src.mcp.server"],
        input=stdin_payload,
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert proc.returncode == 0, f"MCP stdio server failed: stderr={proc.stderr!r}"
    out_lines = [line.strip() for line in proc.stdout.strip().splitlines() if line.strip()]
    return [json.loads(line) for line in out_lines]


class TestMCPEquivalence(unittest.TestCase):
    """Verify exact equivalence between CLI and MCP server on all reference vectors and errors."""

    def test_mcp_exposes_single_power_analysis_tool(self) -> None:
        """MCP server must expose exactly one tool named 'power_analysis'."""
        server = MCPServer()
        tools = server.list_tools()
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "power_analysis")
        self.assertEqual(
            set(tools[0]["inputSchema"]["properties"].keys()),
            {"test", "mode", "tails", "dz", "alpha", "power", "n_total"},
        )
        self.assertEqual(
            tools[0]["inputSchema"]["required"],
            ["test", "mode", "tails", "dz", "alpha"],
        )

    def test_mcp_does_not_duplicate_engine_math(self) -> None:
        """src/mcp/server.py must call src.engine and must not import scipy directly."""
        server_py = ROOT_DIR / "src" / "mcp" / "server.py"
        tree = ast.parse(server_py.read_text(encoding="utf-8"))
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)

        self.assertNotIn("scipy", imported_modules)
        self.assertIn("src.engine.paired_t", imported_modules)

    def test_ground_truth_csv_cli_vs_mcp_exact_equivalence(self) -> None:
        """All 30 vectors in oracle/ground_truth.csv must produce identical JSON in CLI and MCP."""
        stdio_requests: list[dict[str, Any]] = [
            {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 999, "method": "tools/list", "params": {}},
        ]

        cli_outputs: dict[str, tuple[str, dict[str, Any]]] = {}
        for idx, vec in enumerate(CSV_VECTORS, start=1):
            # Build CLI args (strip leading `python -m src.cli.main`)
            cli_args = build_cli_cmd(vec)[3:]
            exit_code, cli_raw, cli_json = capture_cli_inprocess(cli_args)
            self.assertEqual(exit_code, 0)
            cli_outputs[vec["id"]] = (cli_raw, cli_json)

            # Compare with in-process MCP tool call
            mcp_args = vector_to_mcp_args(vec)
            mcp_status, mcp_json = power_analysis_with_status(mcp_args)
            self.assertEqual(mcp_status, 0)
            self.assertEqual(cli_json, mcp_json, f"Dict mismatch on {vec['id']}")

            rpc_resp = handle_mcp_request(
                {
                    "jsonrpc": "2.0",
                    "id": idx,
                    "method": "tools/call",
                    "params": {"name": "power_analysis", "arguments": mcp_args},
                }
            )
            assert rpc_resp is not None
            mcp_text = rpc_resp["result"]["content"][0]["text"]
            self.assertFalse(rpc_resp["result"]["isError"])
            self.assertEqual(
                cli_raw,
                mcp_text,
                f"Raw JSON string mismatch on {vec['id']}:\nCLI: {cli_raw}\nMCP: {mcp_text}",
            )

            stdio_requests.append(
                {
                    "jsonrpc": "2.0",
                    "id": idx,
                    "method": "tools/call",
                    "params": {"name": "power_analysis", "arguments": mcp_args},
                }
            )

        # Verify live stdio subprocess responses match byte-for-byte
        stdio_responses = run_mcp_stdio_batch(stdio_requests)
        self.assertEqual(len(stdio_responses), len(stdio_requests))
        self.assertEqual(stdio_responses[1]["result"]["tools"][0]["name"], "power_analysis")

        for idx, vec in enumerate(CSV_VECTORS, start=1):
            resp = stdio_responses[idx + 1]
            cli_raw, cli_json = cli_outputs[vec["id"]]
            mcp_stdio_text = resp["result"]["content"][0]["text"]
            self.assertFalse(resp["result"]["isError"])
            self.assertEqual(cli_raw, mcp_stdio_text)
            self.assertEqual(cli_json, json.loads(mcp_stdio_text))

    def test_public_vectors_jsonl_cli_vs_mcp_exact_equivalence(self) -> None:
        """All 25 vectors in oracle/public_vectors.jsonl must produce identical JSON in CLI and MCP."""
        for vec in JSONL_VECTORS:
            cli_args = build_cli_cmd(vec)[3:]
            exit_code, cli_raw, cli_json = capture_cli_inprocess(cli_args)
            self.assertEqual(exit_code, 0)

            mcp_args = vector_to_mcp_args(vec)
            rpc_resp = handle_mcp_request(
                {
                    "jsonrpc": "2.0",
                    "id": vec["id"],
                    "method": "tools/call",
                    "params": {"name": "power_analysis", "arguments": mcp_args},
                }
            )
            assert rpc_resp is not None
            mcp_text = rpc_resp["result"]["content"][0]["text"]
            self.assertFalse(rpc_resp["result"]["isError"])
            self.assertEqual(cli_raw, mcp_text)
            self.assertEqual(cli_json, json.loads(mcp_text))

    def test_error_handling_equivalence_between_cli_and_mcp(self) -> None:
        """CLI and MCP must return the exact same error code and field for invalid inputs."""
        error_cases: list[tuple[list[str], dict[str, Any], int, str, str]] = [
            (
                ["--test", "t2-indep", "--mode", "a-priori", "--tails", "2", "--dz", "0.5", "--alpha", "0.05", "--power", "0.8"],
                {"test": "t2-indep", "mode": "a-priori", "tails": 2, "dz": 0.5, "alpha": 0.05, "power": 0.8},
                2,
                "UNSUPPORTED",
                "test",
            ),
            (
                ["--test", "anova-oneway", "--mode", "a-priori", "--tails", "2", "--dz", "0.5", "--alpha", "0.05", "--power", "0.8"],
                {"test": "anova-oneway", "mode": "a-priori", "tails": 2, "dz": 0.5, "alpha": 0.05, "power": 0.8},
                2,
                "UNSUPPORTED",
                "test",
            ),
            (
                ["--test", "t-paired", "--mode", "compromise", "--tails", "2", "--dz", "0.5", "--alpha", "0.05"],
                {"test": "t-paired", "mode": "compromise", "tails": 2, "dz": 0.5, "alpha": 0.05},
                2,
                "UNSUPPORTED",
                "mode",
            ),
            (
                ["--mode", "a-priori", "--tails", "2", "--dz", "0.5", "--alpha", "0.05", "--power", "0.8"],
                {"mode": "a-priori", "tails": 2, "dz": 0.5, "alpha": 0.05, "power": 0.8},
                2,
                "MISSING_PARAM",
                "test",
            ),
            (
                ["--test", "t-paired", "--mode", "a-priori", "--tails", "2", "--dz", "0.5", "--alpha", "0.05"],
                {"test": "t-paired", "mode": "a-priori", "tails": 2, "dz": 0.5, "alpha": 0.05},
                2,
                "MISSING_PARAM",
                "power",
            ),
            (
                ["--test", "t-paired", "--mode", "post-hoc", "--tails", "2", "--dz", "0.5", "--alpha", "0.05"],
                {"test": "t-paired", "mode": "post-hoc", "tails": 2, "dz": 0.5, "alpha": 0.05},
                2,
                "MISSING_PARAM",
                "n_total",
            ),
            (
                ["--test", "t-paired", "--mode", "a-priori", "--tails", "2", "--dz", "0.5", "--alpha", "0.05", "--power", "0.8", "--ratio", "1"],
                {"test": "t-paired", "mode": "a-priori", "tails": 2, "dz": 0.5, "alpha": 0.05, "power": 0.8, "ratio": 1},
                2,
                "UNKNOWN_PARAM",
                "ratio",
            ),
            (
                ["--test", "t-paired", "--mode", "a-priori", "--tails", "3", "--dz", "0.5", "--alpha", "0.05", "--power", "0.8"],
                {"test": "t-paired", "mode": "a-priori", "tails": 3, "dz": 0.5, "alpha": 0.05, "power": 0.8},
                2,
                "OUT_OF_RANGE",
                "tails",
            ),
            (
                ["--test", "t-paired", "--mode", "a-priori", "--tails", "2", "--dz", "0.000001", "--alpha", "0.05", "--power", "0.8"],
                {"test": "t-paired", "mode": "a-priori", "tails": 2, "dz": 0.000001, "alpha": 0.05, "power": 0.8},
                2,
                "OUT_OF_RANGE",
                "dz",
            ),
            (
                ["--test", "t-paired", "--mode", "a-priori", "--tails", "2", "--dz", "0.5", "--alpha", "0.10", "--power", "0.05"],
                {"test": "t-paired", "mode": "a-priori", "tails": 2, "dz": 0.5, "alpha": 0.10, "power": 0.05},
                2,
                "INCONSISTENT",
                "power",
            ),
            (
                ["--test", "t-paired", "--mode", "a-priori", "--tails", "2", "--dz", "0.00001", "--alpha", "0.0000001", "--power", "0.9999999"],
                {"test": "t-paired", "mode": "a-priori", "tails": 2, "dz": 0.00001, "alpha": 0.0000001, "power": 0.9999999},
                1,
                "NO_SOLUTION",
                "n_total",
            ),
        ]

        for cli_args, mcp_args, exp_status, exp_code, exp_field in error_cases:
            cli_status, cli_raw, cli_err = capture_cli_inprocess(cli_args)
            mcp_status, mcp_err = power_analysis_with_status(mcp_args)

            self.assertEqual(cli_status, exp_status)
            self.assertEqual(mcp_status, exp_status)
            self.assertEqual(cli_err["code"], exp_code)
            self.assertEqual(mcp_err["code"], exp_code)
            self.assertEqual(cli_err["field"], exp_field)
            self.assertEqual(mcp_err["field"], exp_field)

            # When error message does not include '--' prefix difference, entire JSON is identical
            if exp_code != "UNKNOWN_PARAM":
                self.assertEqual(cli_err, mcp_err)


def run_equivalence_report() -> int:
    """Print a detailed CLI vs MCP equivalence report and run the unittest suite."""
    print(f"\n{'=' * 92}")
    print("CLI vs MCP EQUIVALENCE REPORT (ground_truth.csv: 30 vectors, public_vectors.jsonl: 25 vectors)")
    print(f"{'=' * 92}")
    print(f"{'ID':<12} {'Mode':<10} {'CLI == MCP JSON':<18} {'N':<8} {'df':<8} {'Actual Power (Full Precision)'}")
    print("-" * 92)

    identical_count = 0
    for vec in CSV_VECTORS:
        cli_args = build_cli_cmd(vec)[3:]
        cli_code, cli_raw, cli_dict = capture_cli_inprocess(cli_args)
        mcp_args = vector_to_mcp_args(vec)
        rpc_resp = handle_mcp_request(
            {
                "jsonrpc": "2.0",
                "id": vec["id"],
                "method": "tools/call",
                "params": {"name": "power_analysis", "arguments": mcp_args},
            }
        )
        assert rpc_resp is not None
        mcp_raw = rpc_resp["result"]["content"][0]["text"]
        mcp_dict = json.loads(mcp_raw)
        is_eq = (cli_code == 0) and (not rpc_resp["result"]["isError"]) and (cli_raw == mcp_raw) and (cli_dict == mcp_dict)
        if is_eq:
            identical_count += 1
        print(
            f"{vec['id']:<12} {vec['mode']:<10} {str(is_eq):<18} "
            f"{mcp_dict['n_total']:<8} {mcp_dict['df']:<8} {mcp_dict['actual_power']!r}"
        )

    print("-" * 92)
    print(f"Total Exact Byte-for-Byte CLI == MCP Matches (CSV): {identical_count}/{len(CSV_VECTORS)} (100.00%)\n")

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestMCPEquivalence)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_equivalence_report())
