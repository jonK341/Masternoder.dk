"""Generate data/aggregators_catalog.json with 75 AI/agent aggregators."""
from __future__ import annotations

import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "aggregators_catalog.json")

SEEDS = [
    ("intelligence", "Research Pulse", "LLM + arXiv RSS", "research_agent", "Summarize papers for lab", "/api/aggregators/intelligence/research", "/lab"),
    ("intelligence", "News Wire", "Multi-source fetch", "news_agent", "Platform news digest", "/api/aggregators/intelligence/news", "/news"),
    ("intelligence", "Trend Scanner", "Topic clustering", "trend_agent", "Spot rising topics", "/api/aggregators/intelligence/trending", "/aggregator?tab=top25"),
    ("intelligence", "Weather Context", "Open-Meteo API", "context_agent", "Content weather overlay", "/api/aggregators/intelligence/weather", "/generator"),
    ("intelligence", "Source Health", "API key monitor", "ops_agent", "Intel source status", "/api/aggregators/intelligence/sources", "/debugger"),
    ("ai_agents", "Content Generator", "GPT pipeline", "content_generator_agent", "Video script drafts", "/api/generator/create", "/generator"),
    ("ai_agents", "Battle Advisor", "RPS predictor", "battle_agent", "Holodeck duel hints", "/api/battle/quick", "/battle"),
    ("ai_agents", "Lab Researcher", "Science cron", "lab_research_agent", "Daily science levels", "/api/lab/progression", "/lab"),
    ("ai_agents", "Customer Scout", "CRM matcher", "customer_agent", "Find buyer leads", "/api/customers", "/customers"),
    ("ai_agents", "Camgirl Companion", "Persona chat", "camgirl_agent_nova", "Performer AI chat", "/api/camgirls/chat", "/camgirls"),
    ("crypto_mn2", "MN2 Balance Sync", "Ledger read", "wallet_agent", "Wallet HUD tiles", "/api/mn2/balance", "/profile?tab=wallet"),
    ("crypto_mn2", "Staking Monitor", "Pool stats", "staking_agent", "APY + pool size", "/api/mn2/staking/stats", "/staking-monitor"),
    ("crypto_mn2", "Market P2P", "Order book", "market_agent", "MN2 marketplace", "/api/market/listings", "/market"),
    ("crypto_mn2", "Engagement MN2", "Micro-rewards", "engagement_agent", "Session MN2 drip", "/api/aggregators/engagement/award", "/aggregator"),
    ("crypto_mn2", "Proof Reserves", "On-chain audit", "audit_agent", "Transparency feed", "/api/mn2/proof-of-reserves", "/proof-of-reserves"),
    ("lab_science", "Magnet Tech Lab", "EM research", "magnet_agent", "Electric magnet R&D", "/api/lab/chapter2-research", "/lab?tab=magnet"),
    ("lab_science", "Co-tech Lifecycle", "Draft pipeline", "cotech_agent", "Accept/archive drafts", "/api/lab/idea-board", "/lab"),
    ("lab_science", "Roundtable", "Discussion sync", "roundtable_agent", "Lab chat room", "/api/lab/roundtable/messages", "/lab#discussion"),
    ("lab_science", "Systems Check", "Health matrix", "systems_agent", "Lab systems table", "/api/lab/systems-check", "/lab"),
    ("game_battle", "Hunter Nexus", "Campaign XP", "hunter_agent", "Campaign progress", "/api/game/hunters/status", "/game"),
    ("game_battle", "Battlegrounds", "Zone MN2", "bg_agent", "Mass PvP rewards", "/api/battlegrounds/status", "/battlegrounds"),
    ("game_battle", "Trophy Sync", "Unlock wiring", "trophy_agent", "Trophy definitions", "/api/trophies/list", "/trophies"),
    ("game_battle", "Quest Board", "Daily quests", "quest_agent", "Quest MN2", "/api/quests/list", "/quests"),
    ("generator_media", "Video Queue", "Job pipeline", "generator_agent", "Render queue status", "/api/generator/queue-status", "/generator"),
    ("generator_media", "AI Clips", "Short-form", "clips_agent", "Clip generation", "/api/generator/ai-clips", "/generator"),
    ("generator_media", "Theme Timeline", "Template rotator", "theme_agent", "Ever-changing templates", "/api/generator/history", "/generator"),
    ("customer_fulfillment", "Lead Capture", "Form → CRM", "lead_agent", "Attract new customers", "/customers", "/customers"),
    ("customer_fulfillment", "Shop Fulfillment", "Order bridge", "shop_agent", "MN2 + PayPal checkout", "/api/shop/catalog", "/shop"),
    ("customer_fulfillment", "Onboarding", "User journey", "onboard_agent", "First-session flow", "/api/user/onboarding", "/profile"),
    ("social_monetization", "Social Tips", "MN2 tips", "social_agent", "Creator tips", "/api/social/tips", "/social"),
    ("social_monetization", "Monetization 25", "Lever assign", "monetization_agent", "Revenue levers", "/api/monetization/levers", "/monetization"),
    ("data_pipeline", "Register Intel", "404 audit", "register_agent", "Route gap scan", "/api/register-intelligence/audit", "/debugger"),
    ("data_pipeline", "Unified Points", "Cross-domain sync", "points_agent", "All point types", "/api/points/all", "/profile?tab=points"),
]

TECH_EXTRAS = [
    "Vector embeddings", "RAG retrieval", "Cron scheduler", "WebSocket push",
    "Edge cache ETag", "SQLite mirror", "Agent skill graph", "MN2 micro-pay",
    "Multi-agent orchestration", "Prompt chaining", "Tool-use API", "Fine-tuned LoRA",
]

CATEGORIES = [
    "intelligence", "ai_agents", "crypto_mn2", "lab_science", "game_battle",
    "generator_media", "customer_fulfillment", "social_monetization", "data_pipeline",
]

def main():
    items = []
    idx = 0
    for cat, name, tech, agent, use, api, href in SEEDS:
        idx += 1
        items.append({
            "id": f"agg_{idx:03d}",
            "name": name,
            "category": cat,
            "tech": tech,
            "technologies": [tech, "Flask API", "Agent bridge"],
            "agent_id": agent,
            "ai_enabled": True,
            "use": use,
            "function": use,
            "api": api,
            "href": href,
            "status": "active",
            "score": max(50, 100 - (idx % 40)),
        })
    # Expand to 75 with numbered variants
    variant_names = {
        "intelligence": "Intel Node",
        "ai_agents": "Agent Module",
        "crypto_mn2": "MN2 Bridge",
        "lab_science": "Lab Sensor",
        "game_battle": "Game Link",
        "generator_media": "Media Pipe",
        "customer_fulfillment": "Fulfillment Hub",
        "social_monetization": "Social Relay",
        "data_pipeline": "Data Stream",
    }
    while len(items) < 75:
        cat = CATEGORIES[len(items) % len(CATEGORIES)]
        n = len(items) + 1
        extra = TECH_EXTRAS[len(items) % len(TECH_EXTRAS)]
        items.append({
            "id": f"agg_{n:03d}",
            "name": f"{variant_names[cat]} {n}",
            "category": cat,
            "tech": extra,
            "technologies": [extra, "AI agent", "Aggregator v2"],
            "agent_id": f"{cat}_agent_{n % 12}",
            "ai_enabled": True,
            "use": f"Automate {cat.replace('_', ' ')} workflow #{n}",
            "function": f"Route data through {extra.lower()}",
            "api": "/api/aggregators/catalog",
            "href": "/aggregator?tab=catalog",
            "status": "active" if n % 7 else "beta",
            "score": 40 + (n * 3) % 55,
        })
    # Sort top scores for reference
    top25 = sorted(items, key=lambda x: -x["score"])[:25]
    payload = {
        "version": "2.0",
        "count": len(items),
        "aggregators": items,
        "top25_ids": [x["id"] for x in top25],
        "categories": CATEGORIES,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {len(items)} aggregators to {OUT}")

if __name__ == "__main__":
    main()
