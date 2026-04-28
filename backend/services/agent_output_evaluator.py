"""
Automated evaluation for AI outputs (criticism / judge path) — quality gates before gallery or publish.
Uses a short LLM rubric when keys exist; otherwise heuristic pass.
"""
import json
import os
import re
from typing import Any, Dict, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _heuristic_score(text: str) -> tuple[float, List[str]]:
    """Cheap checks when LLM judge is unavailable."""
    issues: List[str] = []
    t = (text or "").strip()
    if len(t) < 8:
        issues.append("too_short")
    if re.search(r"ignore (previous|above) instructions", t, re.I):
        issues.append("injection_phrase")
    score = 85.0
    if len(t) < 20:
        score -= 25
    if issues:
        score -= 15 * len(issues)
    return max(0.0, min(100.0, score)), issues


def evaluate_content(
    text: str,
    content_type: str = "general",
    title: str = "",
    strict: bool = False,
) -> Dict[str, Any]:
    """
    Returns { passed, score, issues, method }.
    strict=True or GALLERY_QUALITY_EVAL_STRICT=1 requires score >= threshold.
    """
    threshold = float(os.environ.get("GALLERY_QUALITY_MIN_SCORE", "55"))
    if strict:
        threshold = max(threshold, float(os.environ.get("GALLERY_QUALITY_STRICT_MIN", "65")))

    text = text or ""
    # Try LLM judge
    try:
        from backend.services.llm_service import chat

        prompt = (
            f"Rate this {content_type} for a public gallery (0-100). Title: {title!r}\n\n"
            f"Content:\n{text[:8000]}\n\n"
            "Reply JSON only: {\"score\":N,\"passed\":true/false,\"issues\":[\"...\"]}"
        )
        r = chat(
            [{"role": "user", "content": prompt}],
            task_type="speed",
            max_tokens=300,
            temperature=0.2,
        )
        if r.success and r.content:
            raw = r.content.strip()
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                data = json.loads(m.group())
                score = float(data.get("score", 70))
                passed = bool(data.get("passed", score >= threshold))
                issues = data.get("issues") or []
                if isinstance(issues, str):
                    issues = [issues]
                return {
                    "passed": passed and score >= threshold,
                    "score": score,
                    "issues": issues,
                    "method": "llm_judge",
                    "provider": r.provider,
                }
    except Exception:
        pass

    score, issues = _heuristic_score(text)
    passed = score >= threshold
    return {
        "passed": passed,
        "score": score,
        "issues": issues,
        "method": "heuristic",
        "provider": None,
    }
