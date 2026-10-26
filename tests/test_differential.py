"""Differential test harness comparing gpower-clone CLI against G*Power 3.1.9.7 oracle vectors.

Executes the CLI via subprocess for every vector in:
  - oracle/ground_truth.csv (30 screenshot-backed oracle vectors)
  - oracle/public_vectors.jsonl (25 public reference vectors)

Enforces:
  - Exact integer equality (|diff| == 0) on 'n_total' and 'df'
  - Absolute or relative error <= 1e-6 on 'ncp', 'critical_t', and 'actual_power'
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
import sys
from typing import Any
import unittest

try:
    import pytest  # type: ignore
except ImportError:
    pytest = None

ROOT_DIR = Path(__file__).resolve().parent.parent
GROUND_TRUTH_CSV = ROOT_DIR / "oracle" / "ground_truth.csv"
PUBLIC_VECTORS_JSONL = ROOT_DIR / "oracle" / "public_vectors.jsonl"
FLOAT_TOL = 1e-6


def load_csv_vectors(csv_path: Path = GROUND_TRUTH_CSV) -> list[dict[str, Any]]:
    """Load and normalize oracle test vectors from oracle/ground_truth.csv."""
    vectors: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vectors.append(
                {
                    "id": row["id"].strip(),
                    "mode": row["mode"].strip().replace("_", "-"),
                    "tails": int(row["tails"]),
                    "dz": float(row["dz"]),
                    "alpha": float(row["alpha"]),
                    "power_input": float(row["power_input"]) if row["power_input"].strip() else None,
                    "n_total_input": int(row["n_total_input"]) if row["n_total_input"].strip() else None,
                    "expected_ncp": float(row["expected_ncp"]),
                    "expected_critical_t": float(row["expected_critical_t"]),
                    "expected_df": int(row["expected_df"]),
                    "expected_n_total": int(row["expected_n_total"]),
                    "expected_actual_power": float(row["expected_actual_power"]),
                }
            )
    return vectors


def load_jsonl_vectors(jsonl_path: Path = PUBLIC_VECTORS_JSONL) -> list[dict[str, Any]]:
    """Load and normalize public reference vectors from oracle/public_vectors.jsonl."""
    vectors: list[dict[str, Any]] = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            vectors.append(
                {
                    "id": str(item["id"]).strip(),
                    "mode": str(item["mode"]).strip().replace("_", "-"),
                    "tails": int(item["tails"]),
                    "dz": float(item["dz"]),
                    "alpha": float(item["alpha"]),
                    "power_input": float(item["power_input"]) if item.get("power_input") is not None else None,
                    "n_total_input": int(item["n_total_input"]) if item.get("n_total_input") is not None else None,
                    "expected_ncp": float(item["expected_ncp"]),
                    "expected_critical_t": float(item["expected_critical_t"]),
                    "expected_df": int(item["expected_df"]),
                    "expected_n_total": int(item["expected_n_total"]),
                    "expected_actual_power": float(item["expected_actual_power"]),
                }
            )
    return vectors


def build_cli_cmd(vec: dict[str, Any]) -> list[str]:
    """Construct the CLI command argument list for a single oracle vector."""
    cmd = [
        sys.executable,
        "-m",
        "src.cli.main",
        "--test",
        "t-paired",
        "--mode",
        vec["mode"],
        "--tails",
        str(vec["tails"]),
        "--dz",
        str(vec["dz"]),
        "--alpha",
        str(vec["alpha"]),
    ]
    if vec["mode"] == "a-priori":
        cmd.extend(["--power", str(vec["power_input"])])
    else:
        cmd.extend(["--n-total", str(vec["n_total_input"])])
    return cmd


def invoke_cli_vector(vec: dict[str, Any]) -> tuple[int, dict[str, Any], str]:
    """Execute the CLI command via subprocess and parse single-line JSON stdout."""
    cmd = build_cli_cmd(vec)
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    stdout_lines = proc.stdout.strip().splitlines()
    assert len(stdout_lines) == 1, (
        f"[{vec['id']}] Expected exactly 1 line on stdout, got {len(stdout_lines)}: "
        f"stdout={proc.stdout!r}, stderr={proc.stderr!r}"
    )
    payload = json.loads(stdout_lines[0])
    return proc.returncode, payload, stdout_lines[0]


def within_float_tol(actual: float, expected: float, tol: float = FLOAT_TOL) -> tuple[bool, float, float]:
    """Check |actual - expected| <= tol or relative error <= tol."""
    abs_err = abs(actual - expected)
    denom = max(abs(expected), 1e-15)
    rel_err = abs_err / denom
    ok = (abs_err <= tol) or (rel_err <= tol)
    return ok, abs_err, rel_err


def evaluate_vector(vec: dict[str, Any]) -> dict[str, Any]:
    """Run CLI via subprocess on a vector and compute exact/tolerance match metrics."""
    returncode, out, raw_json = invoke_cli_vector(vec)
    assert returncode == 0, f"[{vec['id']}] CLI exited with {returncode}: {raw_json}"

    # Verify integer types in JSON output
    assert isinstance(out["n_total"], int) and not isinstance(out["n_total"], bool)
    assert isinstance(out["df"], int) and not isinstance(out["df"], bool)
    assert isinstance(out["ncp"], float)
    assert isinstance(out["critical_t"], float)
    assert isinstance(out["actual_power"], float)

    n_diff = abs(out["n_total"] - vec["expected_n_total"])
    df_diff = abs(out["df"] - vec["expected_df"])
    n_exact = n_diff == 0
    df_exact = df_diff == 0

    ncp_ok, ncp_abs, ncp_rel = within_float_tol(out["ncp"], vec["expected_ncp"])
    ct_ok, ct_abs, ct_rel = within_float_tol(out["critical_t"], vec["expected_critical_t"])
    ap_ok, ap_abs, ap_rel = within_float_tol(out["actual_power"], vec["expected_actual_power"])

    all_passed = n_exact and df_exact and ncp_ok and ct_ok and ap_ok
    return {
        "id": vec["id"],
        "mode": vec["mode"],
        "passed": all_passed,
        "n_exact": n_exact,
        "df_exact": df_exact,
        "n_diff": n_diff,
        "df_diff": df_diff,
        "ncp_ok": ncp_ok,
        "ncp_abs_err": ncp_abs,
        "ncp_rel_err": ncp_rel,
        "critical_t_ok": ct_ok,
        "critical_t_abs_err": ct_abs,
        "critical_t_rel_err": ct_rel,
        "actual_power_ok": ap_ok,
        "actual_power_abs_err": ap_abs,
        "actual_power_rel_err": ap_rel,
        "actual": out,
        "expected": {
            "n_total": vec["expected_n_total"],
            "df": vec["expected_df"],
            "ncp": vec["expected_ncp"],
            "critical_t": vec["expected_critical_t"],
            "actual_power": vec["expected_actual_power"],
        },
    }


CSV_VECTORS = load_csv_vectors()
JSONL_VECTORS = load_jsonl_vectors()


class TestDifferentialOracle(unittest.TestCase):
    """Standard library unittest suite running subprocess CLI differential tests."""

    def test_ground_truth_csv_vectors(self) -> None:
        """Verify all 30 vectors in oracle/ground_truth.csv via CLI subprocess."""
        for vec in CSV_VECTORS:
            with self.subTest(id=vec["id"], source="ground_truth.csv"):
                report = evaluate_vector(vec)
                self.assertEqual(
                    report["n_diff"],
                    0,
                    f"[{vec['id']}] n_total mismatch: got {report['actual']['n_total']}, "
                    f"expected {report['expected']['n_total']}",
                )
                self.assertEqual(
                    report["df_diff"],
                    0,
                    f"[{vec['id']}] df mismatch: got {report['actual']['df']}, "
                    f"expected {report['expected']['df']}",
                )
                self.assertTrue(
                    report["ncp_ok"],
                    f"[{vec['id']}] ncp error {report['ncp_abs_err']:.2e} > {FLOAT_TOL}",
                )
                self.assertTrue(
                    report["critical_t_ok"],
                    f"[{vec['id']}] critical_t error {report['critical_t_abs_err']:.2e} > {FLOAT_TOL}",
                )
                self.assertTrue(
                    report["actual_power_ok"],
                    f"[{vec['id']}] actual_power error {report['actual_power_abs_err']:.2e} > {FLOAT_TOL}",
                )

    def test_public_vectors_jsonl(self) -> None:
        """Verify all 25 vectors in oracle/public_vectors.jsonl via CLI subprocess."""
        for vec in JSONL_VECTORS:
            with self.subTest(id=vec["id"], source="public_vectors.jsonl"):
                report = evaluate_vector(vec)
                self.assertEqual(report["n_diff"], 0)
                self.assertEqual(report["df_diff"], 0)
                self.assertTrue(report["ncp_ok"])
                self.assertTrue(report["critical_t_ok"])
                self.assertTrue(report["actual_power_ok"])


def run_suite_report(name: str, vectors: list[dict[str, Any]]) -> tuple[int, int, float]:
    """Run all vectors in a dataset via subprocess and print a differential test report."""
    print(f"\n{'=' * 92}")
    print(f"DIFFERENTIAL TEST SUITE: {name} ({len(vectors)} vectors)")
    print(f"{'=' * 92}")
    print(
        f"{'ID':<11} {'Mode':<10} {'N (ours/ref)':<14} {'df (ours/ref)':<14} "
        f"{'|d_ncp|':<11} {'|d_crit_t|':<11} {'|d_power|':<11} {'Status'}"
    )
    print("-" * 92)

    exact_n_count = 0
    full_pass_count = 0
    max_float_err = 0.0

    for vec in vectors:
        rep = evaluate_vector(vec)
        if rep["n_exact"] and rep["df_exact"]:
            exact_n_count += 1
        if rep["passed"]:
            full_pass_count += 1

        max_float_err = max(
            max_float_err,
            rep["ncp_abs_err"],
            rep["critical_t_abs_err"],
            rep["actual_power_abs_err"],
        )
        n_str = f"{rep['actual']['n_total']}/{rep['expected']['n_total']}"
        df_str = f"{rep['actual']['df']}/{rep['expected']['df']}"
        status_str = "PASS" if rep["passed"] else "FAIL"
        print(
            f"{rep['id']:<11} {rep['mode']:<10} {n_str:<14} {df_str:<14} "
            f"{rep['ncp_abs_err']:<11.2e} {rep['critical_t_abs_err']:<11.2e} "
            f"{rep['actual_power_abs_err']:<11.2e} {status_str}"
        )

    exact_rate = (exact_n_count / len(vectors)) * 100.0 if vectors else 0.0
    pass_rate = (full_pass_count / len(vectors)) * 100.0 if vectors else 0.0
    print("-" * 92)
    print(
        f"Summary ({name}): "
        f"N & df Exact Match = {exact_n_count}/{len(vectors)} ({exact_rate:.2f}%), "
        f"Full Tolerance Match (<= 1e-6) = {full_pass_count}/{len(vectors)} ({pass_rate:.2f}%), "
        f"Max Float Abs Diff = {max_float_err:.2e}"
    )
    return exact_n_count, full_pass_count, max_float_err


if __name__ == "__main__":
    csv_exact, csv_pass, _ = run_suite_report("oracle/ground_truth.csv", CSV_VECTORS)
    jsonl_exact, jsonl_pass, _ = run_suite_report("oracle/public_vectors.jsonl", JSONL_VECTORS)
    if csv_pass != len(CSV_VECTORS) or jsonl_pass != len(JSONL_VECTORS):
        sys.exit(1)
    sys.exit(0)
