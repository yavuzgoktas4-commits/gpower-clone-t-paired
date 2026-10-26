"""Evaluation and token-cost benchmark suite for the Clinical AI Agent (src/agent/).

Runs the 10 Turkish clinical questions in 'tests/evaluation_questions.json' through
ClinicalAgent, populates 'logs/agent_calls.jsonl', verifies 100% accuracy on test
family selection, parameter extraction, and MCP engine outputs, and benchmarks
MCP text calls against G*Power GUI screenshot (Vision) token costs.
"""

from __future__ import annotations

import json
from pathlib import Path
import struct
import sys
import time
from typing import Any
import unittest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.agent.clinical_agent import (
    DEFAULT_LOG_PATH,
    ClinicalAgent,
    classify_test_family,
    extract_clinical_parameters,
)

EVAL_QUESTIONS_PATH = ROOT_DIR / "tests" / "evaluation_questions.json"


def load_evaluation_questions() -> list[dict[str, Any]]:
    with EVAL_QUESTIONS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_png_dimensions(png_path: Path) -> tuple[int, int, int]:
    """Return (width, height, file_bytes) of a PNG screenshot."""
    data = png_path.read_bytes()
    width, height = struct.unpack(">II", data[16:24])
    return width, height, len(data)


def estimate_gui_vision_tokens(png_path: Path, question: str) -> dict[str, int]:
    """Calculate multi-step GUI Vision agent token consumption for a G*Power screenshot task.

    A Vision GUI agent interacting with G*Power must:
      1. Inspect the initial GUI window screenshot (765 tiles/image tokens + UI coordinate prompt)
         to select Test family ('t tests'), Statistical test ('Matched pairs'), and Analysis mode.
      2. Inspect the final calculated G*Power window screenshot (765 image tokens + OCR prompt)
         to read Output Parameters (Noncentrality parameter, Critical t, Df, Total sample size, Actual power).
    """
    width, height, file_bytes = read_png_dimensions(png_path)
    # Standard Vision LLM token pricing: 85 base + 170 per 512x512 tile (for 752x588 -> 2x2 = 4 tiles -> 765 tokens/image)
    tiles_x = (width + 511) // 512
    tiles_y = (height + 511) // 512
    tokens_per_image = 85 + 170 * (tiles_x * tiles_y)
    # 2 GUI screenshots (setup verification + output reading) + system/UI action prompt overhead
    vision_tokens_in = (2 * tokens_per_image) + 210 + len(question.split()) * 2
    vision_tokens_out = 185  # GUI action JSON + final clinical response
    return {
        "width": width,
        "height": height,
        "file_bytes": file_bytes,
        "tokens_per_image": tokens_per_image,
        "tokens_in": vision_tokens_in,
        "tokens_out": vision_tokens_out,
        "tokens_total": vision_tokens_in + vision_tokens_out,
    }


class TestClinicalAgentEvaluation(unittest.TestCase):
    """Verify the clinical agent on the 10-question evaluation set and check logs/agent_calls.jsonl."""

    def test_10_clinical_questions_and_log_generation(self) -> None:
        questions = load_evaluation_questions()
        self.assertEqual(len(questions), 10)

        # Reset logs/agent_calls.jsonl before running the 10 evaluation questions
        if DEFAULT_LOG_PATH.exists():
            DEFAULT_LOG_PATH.unlink()

        agent = ClinicalAgent(log_path=DEFAULT_LOG_PATH)

        for item in questions:
            with self.subTest(id=item["id"]):
                resp = agent.answer_question(item["question"])
                self.assertFalse(resp.needs_clarification)
                self.assertEqual(resp.classification.label, item["expected_test"])
                self.assertGreaterEqual(resp.classification.confidence, 0.75)
                self.assertEqual(resp.tool_input, item["expected_params"])

                exp_out = item["expected_output"]
                self.assertEqual(resp.tool_output["n_total"], exp_out["n_total"])
                self.assertEqual(resp.tool_output["df"], exp_out["df"])
                self.assertAlmostEqual(resp.tool_output["ncp"], exp_out["ncp"], places=6)
                self.assertAlmostEqual(resp.tool_output["critical_t"], exp_out["critical_t"], places=6)
                self.assertAlmostEqual(resp.tool_output["actual_power"], exp_out["actual_power"], places=6)

        # Verify logs/agent_calls.jsonl has 10 valid records with required keys
        self.assertTrue(DEFAULT_LOG_PATH.exists())
        log_lines = [
            line.strip()
            for line in DEFAULT_LOG_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(log_lines), 10)
        for line in log_lines:
            rec = json.loads(line)
            self.assertEqual(
                set(rec.keys()),
                {"ts", "question", "tool_input", "tool_output", "tokens_in", "tokens_out"},
            )
            self.assertGreater(rec["tokens_in"], 0)
            self.assertGreater(rec["tokens_out"], 0)

    def test_bilingual_tr_vs_en_classification_and_extraction(self) -> None:
        """Compare Turkish and English parameter extraction and System-1 classification."""
        questions = load_evaluation_questions()
        for item in questions:
            cls_tr = classify_test_family(item["question"])
            cls_en = classify_test_family(item["question_en"])
            self.assertEqual(cls_tr.label, "t-paired")
            self.assertEqual(cls_en.label, "t-paired")

            params_tr = extract_clinical_parameters(item["question"], cls_tr.label)
            params_en = extract_clinical_parameters(item["question_en"], cls_en.label)
            self.assertEqual(params_tr, item["expected_params"])
            self.assertEqual(params_en, item["expected_params"])


def run_benchmark_and_tests() -> int:
    questions = load_evaluation_questions()
    if DEFAULT_LOG_PATH.exists():
        DEFAULT_LOG_PATH.unlink()

    agent = ClinicalAgent(log_path=DEFAULT_LOG_PATH)

    print(f"\n{'=' * 100}")
    print("CLINICAL AGENT EVALUATION & MCP vs GUI VISION BENCHMARK (10 QUESTIONS)")
    print(f"{'=' * 100}")
    print(
        f"{'ID':<6} {'Domain':<32} {'Test':<10} {'N (ours/exp)':<14} "
        f"{'MCP Tok':<10} {'GUI Tok':<10} {'Saving':<10} {'MCP ms'}"
    )
    print("-" * 100)

    total_mcp_in = 0
    total_mcp_out = 0
    total_gui_in = 0
    total_gui_out = 0
    total_mcp_ms = 0.0
    correct_count = 0

    for item in questions:
        t0 = time.perf_counter()
        resp = agent.answer_question(item["question"])
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        total_mcp_ms += elapsed_ms

        mcp_total = resp.tokens_in + resp.tokens_out
        total_mcp_in += resp.tokens_in
        total_mcp_out += resp.tokens_out

        gui_stats = estimate_gui_vision_tokens(ROOT_DIR / item["screenshot"], item["question"])
        total_gui_in += gui_stats["tokens_in"]
        total_gui_out += gui_stats["tokens_out"]

        exp_n = item["expected_output"]["n_total"]
        got_n = resp.tool_output["n_total"]
        is_ok = (
            resp.classification.label == item["expected_test"]
            and resp.tool_input == item["expected_params"]
            and got_n == exp_n
        )
        if is_ok:
            correct_count += 1

        saving_pct = (1.0 - (mcp_total / gui_stats["tokens_total"])) * 100.0
        domain_short = item["clinical_domain"][:30]
        n_str = f"{got_n}/{exp_n}"
        print(
            f"{item['id']:<6} {domain_short:<32} {resp.classification.label:<10} {n_str:<14} "
            f"{mcp_total:<10} {gui_stats['tokens_total']:<10} {saving_pct:>6.1f}%   {elapsed_ms:>6.2f}"
        )

    total_mcp = total_mcp_in + total_mcp_out
    total_gui = total_gui_in + total_gui_out
    overall_saving = (1.0 - (total_mcp / total_gui)) * 100.0
    print("-" * 100)
    print(
        f"TOTAL / ACCURACY: {correct_count}/10 ({correct_count * 10:.1f}%) | "
        f"MCP Tokens = {total_mcp} (in={total_mcp_in}, out={total_mcp_out}) | "
        f"GUI Vision Tokens = {total_gui} (in={total_gui_in}, out={total_gui_out}) | "
        f"Token Reduction = {overall_saving:.2f}% ({total_gui / total_mcp:.1f}x cheaper) | "
        f"Total MCP Time = {total_mcp_ms:.2f} ms"
    )
    return 0 if correct_count == 10 else 1


if __name__ == "__main__":
    rc = run_benchmark_and_tests()
    sys.exit(rc)
