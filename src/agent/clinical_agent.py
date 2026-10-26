"""Clinical AI Agent layer translating Turkish/English physician queries into MCP tool calls.

Adheres strictly to CONTRACT.md Section 8:
  - Never performs statistical calculations itself; all numbers come from the MCP
    'power_analysis' tool backed by 'src.engine'.
  - Includes a System-1 test family classifier over the constrained label set:
    {'t2-indep', 't-paired', 'anova-oneway', 'chi2-contingency', 'multireg-r2', 'ambiguous', 'unsupported'}.
  - Logs every MCP tool invocation to 'logs/agent_calls.jsonl' in the required schema:
    {"ts": "...", "question": "...", "tool_input": {...}, "tool_output": {...}, "tokens_in": ..., "tokens_out": ...}
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any, Optional

from src.mcp.server import MCPServer

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_LOG_PATH = ROOT_DIR / "logs" / "agent_calls.jsonl"

VALID_FAMILY_LABELS = (
    "t2-indep",
    "t-paired",
    "anova-oneway",
    "chi2-contingency",
    "multireg-r2",
    "ambiguous",
    "unsupported",
)

CONFIDENCE_THRESHOLD = 0.75


@dataclass(frozen=True)
class ClassificationResult:
    """System-1 test family classification output with confidence score."""

    label: str
    confidence: float
    rationale: str


@dataclass(frozen=True)
class AgentResponse:
    """Complete clinical agent response including MCP tool I/O and token accounting."""

    question: str
    classification: ClassificationResult
    tool_input: dict[str, Any]
    tool_output: dict[str, Any]
    answer_tr: str
    tokens_in: int
    tokens_out: int
    needs_clarification: bool = False


def estimate_tokens(text: str) -> int:
    """Estimate BPE token count deterministically (~1.35 tokens per whitespace word + punctuation)."""
    if not text:
        return 0
    words = re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE)
    return max(1, int(round(len(words) * 1.15)))


def classify_test_family(question: str) -> ClassificationResult:
    """System-1 fast classifier mapping clinical study descriptions to test family labels."""
    q_lower = question.lower()

    paired_keywords = [
        "önce ve sonra",
        "öncesi ve sonrası",
        "tedavi öncesi",
        "tedavi sonrası",
        "ameliyat öncesi",
        "ameliyat sonrası",
        "eşleştirilmiş",
        "bağımlı iki",
        "aynı hasta",
        "aynı olgu",
        "aynı birey",
        "tekrarlı ölçüm",
        "paired",
        "matched pairs",
        "before and after",
        "pre- and post-",
        "pre and post",
        "within-subject",
        "dependent means",
        "dz",
    ]
    indep_keywords = [
        "iki bağımsız",
        "bağımsız grup",
        "ilaç ve plasebo",
        "deney ve kontrol",
        "vaka ve kontrol",
        "two independent",
        "independent groups",
        "drug vs placebo",
        "allocation ratio",
    ]
    anova_keywords = [
        "üç tedavi kolu",
        "üç grup",
        "dört grup",
        "tek yönlü anova",
        "anova",
        "one-way",
        "three groups",
        "four groups",
    ]
    chi2_keywords = [
        "olumsallık tablosu",
        "ki-kare",
        "chi-square",
        "contingency table",
        "kategorik yanıt oran",
    ]
    reg_keywords = [
        "çoklu regresyon",
        "multiple regression",
        "r2",
        "r²",
        "prediktör",
        "predictors",
    ]

    paired_hits = sum(1 for kw in paired_keywords if kw in q_lower)
    indep_hits = sum(1 for kw in indep_keywords if kw in q_lower)
    anova_hits = sum(1 for kw in anova_keywords if kw in q_lower)
    chi2_hits = sum(1 for kw in chi2_keywords if kw in q_lower)
    reg_hits = sum(1 for kw in reg_keywords if kw in q_lower)

    scores = {
        "t-paired": paired_hits,
        "t2-indep": indep_hits,
        "anova-oneway": anova_hits,
        "chi2-contingency": chi2_hits,
        "multireg-r2": reg_hits,
    }
    best_label = max(scores, key=lambda k: scores[k])
    best_score = scores[best_label]
    total_hits = sum(scores.values())

    if best_score == 0:
        return ClassificationResult(
            label="ambiguous",
            confidence=0.40,
            rationale="Soruda çalışma tasarımını (eşleştirilmiş/bağımsız/ANOVA) belirten açık anahtar ifade bulunamadı.",
        )

    if total_hits > best_score and (best_score / total_hits) < 0.65:
        return ClassificationResult(
            label="ambiguous",
            confidence=0.55,
            rationale="Soruda birden fazla test ailesine işaret eden çelişkili ifadeler bulundu.",
        )

    confidence = min(0.98, 0.78 + 0.06 * best_score)
    return ClassificationResult(
        label=best_label,
        confidence=round(confidence, 2),
        rationale=f"Klinik tasarım anahtar ifadeleri '{best_label}' ailesiyle eşleşti (eşleşme skoru: {best_score}).",
    )


def _normalize_num_str(s: str) -> float:
    return float(s.replace(",", "."))


def extract_clinical_parameters(question: str, family_label: str = "t-paired") -> dict[str, Any]:
    """Extract MCP tool parameters from a natural-language Turkish or English clinical question."""
    q_lower = question.lower()

    # 1. Determine mode: 'post-hoc' vs 'a-priori'
    is_post_hoc = any(
        kw in q_lower
        for kw in [
            "post-hoc",
            "post hoc",
            "gerçekleşen güç",
            "elde edilen güç",
            "istatistiksel gücü nedir",
            "gücü kaçtır",
            "güç nedir",
            "achieved power",
            "what is the power",
            "what statistical power",
        ]
    )
    mode = "post-hoc" if is_post_hoc else "a-priori"

    # 2. Determine tails: 1 vs 2
    is_one_tailed = any(
        kw in q_lower
        for kw in [
            "tek yönlü",
            "tek kuyruklu",
            "1 kuyruklu",
            "1-kuyruklu",
            "tails=1",
            "tails = 1",
            "one-tailed",
            "one tailed",
            "yalnızca düşüş",
            "yalnızca azalma",
            "yalnızca artış",
        ]
    )
    is_two_tailed = any(
        kw in q_lower
        for kw in [
            "çift yönlü",
            "iki yönlü",
            "çift kuyruklu",
            "iki kuyruklu",
            "2 kuyruklu",
            "2-kuyruklu",
            "tails=2",
            "tails = 2",
            "two-tailed",
            "two tailed",
        ]
    )
    tails = 1 if (is_one_tailed and not is_two_tailed) else 2

    # 3. Extract effect size dz
    dz_val: Optional[float] = None
    dz_patterns = [
        r"d_?z\s*(?:=|:|değeri|etki büyüklüğü)?\s*([-+]?\d+(?:[.,]\d+)?)",
        r"etki büyüklüğü\s*(?:\(d_?z\))?\s*(?:=|:)?\s*([-+]?\d+(?:[.,]\d+)?)",
        r"effect size\s*(?:\(d_?z\))?\s*(?:=|:|of)?\s*([-+]?\d+(?:[.,]\d+)?)",
    ]
    for pat in dz_patterns:
        m = re.search(pat, q_lower)
        if m:
            dz_val = _normalize_num_str(m.group(1))
            break

    # 4. Extract alpha
    alpha_val: Optional[float] = None
    alpha_patterns = [
        r"(?:alfa|alpha|α|anlamlılık düzeyi|yanılma payı|tip i hata)\s*(?:\(\s*(?:alfa|alpha|α)\s*\))?\s*(?:=|:|düzeyi|olarak)?\s*(0[.,]\d+)",
        r"(?:alfa|alpha|α)\s*=\s*(0[.,]\d+)",
    ]
    for pat in alpha_patterns:
        m = re.search(pat, q_lower)
        if m:
            alpha_val = _normalize_num_str(m.group(1))
            break
    if alpha_val is None:
        m_pct = re.search(r"%\s*(\d+(?:[.,]\d+)?)\s*(?:anlamlılık|alfa|alpha)", q_lower)
        if m_pct:
            alpha_val = _normalize_num_str(m_pct.group(1)) / 100.0

    # 5. Extract power (for a-priori) or n_total (for post-hoc)
    power_val: Optional[float] = None
    n_total_val: Optional[int] = None

    if mode == "a-priori":
        power_patterns = [
            r"(?:güç|power|1\s*-\s*beta|1\s*-\s*β)\s*(?:\([^)]*\))?\s*(?:=|:|düzeyi|oranı|değeri)?\s*(0[.,]\d+)",
            r"%\s*(\d+(?:[.,]\d+)?)\s*(?:istatistiksel\s+)?güç",
            r"(?:güç|power)\s*%\s*(\d+(?:[.,]\d+)?)",
            r"(\d+(?:[.,]\d+)?)\s*%\s*(?:statistical\s+)?power",
        ]
        for idx, pat in enumerate(power_patterns):
            m = re.search(pat, q_lower)
            if m:
                raw_v = _normalize_num_str(m.group(1))
                power_val = raw_v / 100.0 if idx >= 1 or raw_v > 1.0 else raw_v
                break
    else:
        n_patterns = [
            r"(?:n_total|n|toplam örneklem|hasta sayısı|olgu sayısı|çift sayısı|katılımcı sayısı)\s*(?:=|:)?\s*(\d+)",
            r"(\d+)\s*(?:hastada|hastalık|olguda|çiftte|katılımcıda|kişide|matched pairs|patients|subjects)",
        ]
        for pat in n_patterns:
            m = re.search(pat, q_lower)
            if m:
                n_total_val = int(m.group(1))
                break

    params: dict[str, Any] = {
        "test": family_label,
        "mode": mode,
        "tails": tails,
    }
    if dz_val is not None:
        params["dz"] = dz_val
    if alpha_val is not None:
        params["alpha"] = alpha_val
    if mode == "a-priori" and power_val is not None:
        params["power"] = power_val
    if mode == "post-hoc" and n_total_val is not None:
        params["n_total"] = n_total_val

    return params


def format_clinical_explanation(
    question: str,
    tool_input: dict[str, Any],
    tool_output: dict[str, Any],
) -> str:
    """Format a clear Turkish explanation for the physician using ONLY engine outputs."""
    _ = question
    if "error" in tool_output:
        return (
            f"Hesaplama yapılamadı [{tool_output.get('code')} - alan: {tool_output.get('field')}]: "
            f"{tool_output.get('error')}"
        )

    tails_str = "tek kuyruklu (one-tailed)" if tool_input.get("tails") == 1 else "çift kuyruklu (two-tailed)"
    if tool_input.get("mode") == "a-priori":
        return (
            f"Eşleştirilmiş t-testi (t-paired, {tails_str}) A-priori örneklem büyüklüğü analizi sonucuna göre; "
            f"dz = {tool_input['dz']}, α = {tool_input['alpha']} ve hedef güç = {tool_input['power']} "
            f"parametreleri için çalışmaya alınması gereken minimum toplam hasta (çift) sayısı "
            f"N = {tool_output['n_total']} olarak bulunmuştur (serbestlik derecesi df = {tool_output['df']}, "
            f"kritik t = {tool_output['critical_t']:.7f}, merkezilikten uzaklık parametresi "
            f"δ = {tool_output['ncp']:.7f}, gerçekleşen güç = {tool_output['actual_power']:.7f})."
        )
    return (
        f"Eşleştirilmiş t-testi (t-paired, {tails_str}) Post-hoc güç analizi sonucuna göre; "
        f"N = {tool_output['n_total']} hasta (çift), dz = {tool_input['dz']} ve α = {tool_input['alpha']} "
        f"parametreleri ile elde edilen gerçekleşen istatistiksel güç (1-β) = "
        f"{tool_output['actual_power']:.7f} olarak hesaplanmıştır (serbestlik derecesi df = {tool_output['df']}, "
        f"kritik t = {tool_output['critical_t']:.7f}, merkezilikten uzaklık parametresi "
        f"δ = {tool_output['ncp']:.7f})."
    )


class ClinicalAgent:
    """Clinical AI Agent backed by the MCP 'power_analysis' server."""

    def __init__(
        self,
        mcp_server: Optional[MCPServer] = None,
        log_path: Path = DEFAULT_LOG_PATH,
    ) -> None:
        self.mcp_server = mcp_server or MCPServer()
        self.log_path = log_path

    def _append_log(
        self,
        question: str,
        tool_input: dict[str, Any],
        tool_output: dict[str, Any],
        tokens_in: int,
        tokens_out: int,
    ) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "question": question,
            "tool_input": tool_input,
            "tool_output": tool_output,
            "tokens_in": int(tokens_in),
            "tokens_out": int(tokens_out),
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def answer_question(self, question: str) -> AgentResponse:
        """Classify clinical question, extract parameters, invoke MCP tool, and log call."""
        classification = classify_test_family(question)

        if (
            classification.confidence < CONFIDENCE_THRESHOLD
            or classification.label in ("ambiguous", "unsupported")
        ):
            tool_in: dict[str, Any] = {"test": classification.label}
            tool_out: dict[str, Any] = {
                "error": (
                    f"Çalışma tasarımı güven eşiğinin ({CONFIDENCE_THRESHOLD}) altında "
                    f"({classification.confidence}) veya belirsiz ('{classification.label}'). "
                    "Lütfen ölçümlerin aynı hastalarda (eşleştirilmiş) mı yoksa bağımsız gruplarda mı "
                    "yapıldığını netleştirin."
                ),
                "code": "UNSUPPORTED",
                "field": "test",
            }
            ans = tool_out["error"]
            tok_in = estimate_tokens(question) + estimate_tokens(json.dumps(tool_in, ensure_ascii=False))
            tok_out = estimate_tokens(json.dumps(tool_out, ensure_ascii=False)) + estimate_tokens(ans)
            self._append_log(question, tool_in, tool_out, tok_in, tok_out)
            return AgentResponse(
                question=question,
                classification=classification,
                tool_input=tool_in,
                tool_output=tool_out,
                answer_tr=ans,
                tokens_in=tok_in,
                tokens_out=tok_out,
                needs_clarification=True,
            )

        tool_input = extract_clinical_parameters(question, family_label=classification.label)
        mcp_result = self.mcp_server.call_tool("power_analysis", tool_input)
        tool_output = json.loads(mcp_result["content"][0]["text"])
        explanation = format_clinical_explanation(question, tool_input, tool_output)

        # Token accounting: question + MCP tool call input vs MCP tool output + clinical answer
        tokens_in = estimate_tokens(question) + estimate_tokens(
            json.dumps(tool_input, ensure_ascii=False)
        )
        tokens_out = estimate_tokens(
            json.dumps(tool_output, ensure_ascii=False)
        ) + estimate_tokens(explanation)

        self._append_log(
            question=question,
            tool_input=tool_input,
            tool_output=tool_output,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )

        return AgentResponse(
            question=question,
            classification=classification,
            tool_input=tool_input,
            tool_output=tool_output,
            answer_tr=explanation,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            needs_clarification=False,
        )


def main() -> None:
    """CLI runner for the clinical agent."""
    if len(sys.argv) < 2:
        print("Kullanım: python -m src.agent.clinical_agent \"<klinik soru>\"")
        sys.exit(2)
    question = " ".join(sys.argv[1:])
    agent = ClinicalAgent()
    resp = agent.answer_question(question)
    print(resp.answer_tr)


if __name__ == "__main__":
    main()
