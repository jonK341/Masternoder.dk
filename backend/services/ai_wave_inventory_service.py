"""Phase 13 AI / monetization wave inventory — status of core 25 + monetization waves.

This is the durable map of what is live in-repo vs deferred. Request routes only
read this inventory; model work stays off-request (cron/workers).
"""
from __future__ import annotations

from typing import Any, Dict, List

# status: live | partial | deferred
CORE_WAVES: List[Dict[str, Any]] = [
    {"id": 1, "name": "MN2 Market-Maker Brain", "status": "live", "anchors": ["agent_trader_service", "p2p_market_service"]},
    {"id": 2, "name": "Price Oracle Forecaster", "status": "partial", "anchors": ["mn2_chainz", "mn2_network_history"]},
    {"id": 3, "name": "Agent Risk Governor", "status": "partial", "anchors": ["agent_kill_switch", "agent_admin_routes"]},
    {"id": 4, "name": "Liquidity Gap Detector", "status": "partial", "anchors": ["agent_trader_service", "agent_cron_service"]},
    {"id": 5, "name": "Agent Strategy Evolution", "status": "deferred", "anchors": ["agent_skillset", "agent_trader_service"]},
    {"id": 6, "name": "Adaptive Hunter Opponents", "status": "partial", "anchors": ["hunters_game", "game_mn2_rewards"]},
    {"id": 7, "name": "StarMap Tactical AI", "status": "partial", "anchors": ["star_map_routes"]},
    {"id": 8, "name": "Casino Responsible Odds Guard", "status": "partial", "anchors": ["casino_service", "account_security_service"]},
    {"id": 9, "name": "Dynamic Quest Crafter", "status": "partial", "anchors": ["quest_routes"]},
    {"id": 10, "name": "Cross-Game Combo Engine", "status": "live", "anchors": ["game_mn2_rewards.record_game_activity"]},
    {"id": 11, "name": "Prompt Refinement Agent", "status": "partial", "anchors": ["video_ai_bridge", "generator"]},
    {"id": 12, "name": "Auto Theme Unlocker", "status": "partial", "anchors": ["themes"]},
    {"id": 13, "name": "Smart Encode Queue", "status": "partial", "anchors": ["generator_shared", "run_generator_job"]},
    {"id": 14, "name": "Provider Selection Brain", "status": "partial", "anchors": ["llm_service", "ai_providers_routes"]},
    {"id": 15, "name": "Proof-of-Creation AI Packager", "status": "deferred", "anchors": ["video_generator_service", "mn2_ledger"]},
    {"id": 16, "name": "Withdrawal Risk Scorer", "status": "live", "anchors": ["mn2_withdrawal_risk", "security_cron"]},
    {"id": 17, "name": "Sybil Graph Detector", "status": "live", "anchors": ["mn2_sybil_graph"]},
    {"id": 18, "name": "Ledger Drift Alarm", "status": "live", "anchors": ["points_drift_service", "mn2_conservation_gate"]},
    {"id": 19, "name": "Agent Wallet Reconciler", "status": "live", "anchors": ["agent_admin_service.reconcile_treasury_pool"]},
    {"id": 20, "name": "Market Manipulation Detector", "status": "deferred", "anchors": ["p2p_market_service"]},
    {"id": 21, "name": "Support Copilot RAG", "status": "partial", "anchors": ["support_faq_service", "discord"]},
    {"id": 22, "name": "Ops Digest LLM", "status": "live", "anchors": ["platform_news_digest", "discord_digest"]},
    {"id": 23, "name": "Debugger Challenge Generator", "status": "partial", "anchors": ["debugger_agent_tasks_routes"]},
    {"id": 24, "name": "Blueprint Route Fixer Agent", "status": "live", "anchors": ["agent_skillset_ops_service"]},
    {"id": 25, "name": "Health / Gate Hub Brain", "status": "live", "anchors": ["health_routes", "mn2_services_hub"]},
]

MONETIZATION_WAVES: List[Dict[str, Any]] = [
    {"id": 26, "name": "Creator Tipping Router", "status": "partial", "anchors": ["shop", "generator"]},
    {"id": 27, "name": "AI Spread & Fee Optimizer", "status": "deferred", "anchors": ["p2p_market_service"]},
    {"id": 28, "name": "SCR Self-Serve Deposits", "status": "live", "anchors": ["scr_checkout_service", "monetization_expansion_routes"]},
    {"id": 29, "name": "Promo / Affiliate Rotator", "status": "live", "anchors": ["discord_m8_streams", "shop_checkout_promo_service"]},
    {"id": 30, "name": "B2B Ledger / Invoicing", "status": "partial", "anchors": ["monetization_expansion_routes"]},
    {"id": 31, "name": "AI Upsell Orchestrator", "status": "deferred", "anchors": ["casino_service", "shop_routes"]},
    {"id": 32, "name": "Watch-to-Earn", "status": "live", "anchors": ["game_mn2_rewards.watch_to_earn"]},
    {"id": 33, "name": "Subscription Bindings", "status": "partial", "anchors": ["monetization_subscription_service"]},
    {"id": 34, "name": "Casino Playthrough Rebate", "status": "live", "anchors": ["game_mn2_rewards.casino_playthrough_rebate"]},
    {"id": 35, "name": "Compendium Completion MN2", "status": "live", "anchors": ["compendium_milestone_service"]},
    {"id": 36, "name": "Masternode Hosting Checkout", "status": "live", "anchors": ["mn2_masternode_routes"]},
    {"id": 37, "name": "On-ramp / P2P Rails", "status": "live", "anchors": ["mn2_onramp", "mn2_p2p"]},
    {"id": 38, "name": "Wrapped/Bridge Opportunity Analyzer", "status": "deferred", "anchors": ["docs"]},
    {"id": 39, "name": "Affiliate Offer Matcher", "status": "partial", "anchors": ["customer_aggregator", "platform_news"]},
    {"id": 40, "name": "Exchange Arb / Treasury Pipeline", "status": "partial", "anchors": ["exchange_treasury_liquidity_service"]},
    {"id": 41, "name": "Agent-as-a-Service Signals", "status": "deferred", "anchors": ["agent_trader_service"]},
    {"id": 42, "name": "Shop Digital Downloads / PoR SKU", "status": "live", "anchors": ["shop", "mn2_proof_of_reserves_service"]},
    {"id": 43, "name": "Agent-as-a-Service for Other Markets", "status": "deferred", "anchors": ["agent_trader_service"]},
    {"id": 44, "name": "Discord Role Gating", "status": "partial", "anchors": ["discord_service", "M8"]},
    {"id": 45, "name": "Discord-Exclusive Promo Codes", "status": "live", "anchors": ["discord_m8_streams"]},
    {"id": 46, "name": "Discord Alert Funnel", "status": "live", "anchors": ["market_discord_fanout"]},
    {"id": 47, "name": "Discord Partner Spotlight", "status": "live", "anchors": ["discord_m8_streams.publish_partner_spotlight"]},
    {"id": 48, "name": "Discord Daily Digest", "status": "live", "anchors": ["platform_news_digest", "cron/discord_digest.sh"]},
    {"id": 49, "name": "Discord Quest Bot", "status": "partial", "anchors": ["game_mn2_rewards", "discord"]},
    {"id": 50, "name": "Discord Affiliate Link Rotator", "status": "live", "anchors": ["discord_m8_streams"]},
]


def _counts(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    out = {"live": 0, "partial": 0, "deferred": 0}
    for r in rows:
        st = str(r.get("status") or "deferred")
        out[st] = out.get(st, 0) + 1
    return out


def wave_inventory() -> Dict[str, Any]:
    core = list(CORE_WAVES)
    mon = list(MONETIZATION_WAVES)
    return {
        "success": True,
        "phase": 13,
        "policy": "Off-request AI only; money moves require Gate S + deterministic validation",
        "core_25": core,
        "monetization_waves": mon,
        "counts": {
            "core": _counts(core),
            "monetization": _counts(mon),
            "total": _counts(core + mon),
        },
        "next_deferred": [
            r for r in (core + mon) if r.get("status") == "deferred"
        ][:10],
    }
