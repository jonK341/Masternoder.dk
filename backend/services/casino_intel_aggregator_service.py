"""
Casino intelligence hub — calculators, prognoses, house income for aggregator pages.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.services import casino_calculator_service as calc
from backend.services import casino_prognosis_service as prognosis
from backend.services.house_income_aggregator import summarize as house_income_summarize


def build_hub(
    *,
    since_hours: int = 24,
    game_id: Optional[str] = None,
    user_id: Optional[str] = None,
    bet: float = 10,
    balance: float = 1000,
) -> Dict[str, Any]:
    gid = (game_id or "coin_flip").strip().lower()
    calculators = calc.list_calculator_functions()
    sample = calc.calculate_for_game(gid, bet=bet, balance=balance)
    prog = prognosis.build_prognosis_hub(user_id=user_id)
    income = house_income_summarize(since_hours=since_hours, venue="casino")
    return {
        "success": True,
        "hub": "casino_intel",
        "calculators": calculators,
        "sample_game": sample,
        "prognosis": prog,
        "house_income": income,
        "links": [
            {"label": "Game guides", "href": "/api/casino/guides"},
            {"label": "Run calculator", "href": f"/api/casino/calculators/calculate_for_game?game_id={gid}"},
            {"label": "Prognosis", "href": "/api/casino/prognosis"},
            {"label": "Agent bot models", "href": "/api/agent/casino/models"},
        ],
    }


def run_calculator(calc_id: str, **kwargs) -> Dict[str, Any]:
    return calc.run_calculator(calc_id, **kwargs)
