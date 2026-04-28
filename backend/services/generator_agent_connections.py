"""
Generator–Agent Connections
Defines 20 integration points between agents and the video generator.
Used by the generator UI and by agents that request or react to video generation.
"""
from typing import List, Dict, Any, Optional

# 20 agent–generator connections: id, agent, type, description, endpoint or action
CONNECTIONS: List[Dict[str, Any]] = [
    {"id": 1,  "agent": "Points",           "type": "reward",      "description": "Awards points when a documentary completes", "endpoint": "/api/points/trigger", "link": "/vidgenerator/stats"},
    {"id": 2,  "agent": "Trophies",         "type": "reward",      "description": "Unlocks trophies for first video and milestones", "endpoint": "/api/trophies", "link": "/vidgenerator/trophies"},
    {"id": 3,  "agent": "Battle",            "type": "trigger",     "description": "Battle can request a victory or intro video from generator", "endpoint": "/api/battle", "link": "/vidgenerator/battle"},
    {"id": 4,  "agent": "Gallery",           "type": "display",     "description": "Lists and plays generator output videos", "endpoint": "/api/gallery/videos", "link": "/vidgenerator/gallery"},
    {"id": 5,  "agent": "Chat",              "type": "suggest",    "description": "Chat suggests 'Generate a video' and can pass prompt to generator", "endpoint": "/api/chat", "link": "/vidgenerator/chat"},
    {"id": 6,  "agent": "Shop",              "type": "unlock",     "description": "Shop can unlock premium generator themes or duration", "endpoint": "/api/shop", "link": "/vidgenerator/shop"},
    {"id": 7,  "agent": "Debugger",          "type": "trigger",    "description": "Debugger can run generator E2E and unit tests", "endpoint": "/api/debug/hard-test-generator", "link": "/vidgenerator/debugger"},
    {"id": 8,  "agent": "Master Fix Agent",   "type": "orchestrate", "description": "Orchestrates fixes; can request demo video for a mission", "endpoint": "/api/master-fix", "link": "/vidgenerator/debugger"},
    {"id": 9,  "agent": "AI Enhanced",       "type": "enhance",    "description": "Enhances prompts before generator create", "endpoint": "/api/ai-enhanced", "link": "/vidgenerator"},
    {"id": 10, "agent": "Agent Tracker",     "type": "track",      "description": "Tracks generator API calls and success rate", "endpoint": "/api/agent/tracker", "link": "/vidgenerator"},
    {"id": 11, "agent": "Agent Activity",     "type": "track",      "description": "Logs user activity on generator page", "endpoint": "/api/agent/activity", "link": "/vidgenerator"},
    {"id": 12, "agent": "User Profile",       "type": "store",      "description": "Stores last_documentary_id and generator preferences", "endpoint": "/api/user/profile", "link": "/vidgenerator/profile"},
    {"id": 13, "agent": "Health",            "type": "monitor",    "description": "Health check includes generator pipeline availability", "endpoint": "/api/health", "link": "/vidgenerator"},
    {"id": 14, "agent": "Monitoring",        "type": "monitor",    "description": "Monitors generator job queue and completion times", "endpoint": "/api/monitoring", "link": "/vidgenerator"},
    {"id": 15, "agent": "Error Logging",     "type": "track",      "description": "Logs generator failures and error_message", "endpoint": "/api/error-logging", "link": "/vidgenerator/debugger"},
    {"id": 16, "agent": "Agent Workflow",    "type": "orchestrate", "description": "Workflow can include step: generate documentary", "endpoint": "/api/agent/workflow", "link": "/vidgenerator"},
    {"id": 17, "agent": "Agent Decision Maker", "type": "decide", "description": "Can decide to suggest video generation to user", "endpoint": "/api/agent/decision", "link": "/vidgenerator"},
    {"id": 18, "agent": "Hunters Game",      "type": "trigger",   "description": "Game events can trigger a short clip from generator", "endpoint": "/api/hunters", "link": "/vidgenerator"},
    {"id": 19, "agent": "Star Map",          "type": "display",   "description": "Star map can show 'video created' as a node", "endpoint": "/api/star-map", "link": "/vidgenerator"},
    {"id": 20, "agent": "Unified Points",    "type": "reward",    "description": "Unified points trigger on documentary completion", "endpoint": "/api/unified-points", "link": "/vidgenerator/stats"},
]


def get_connections() -> List[Dict[str, Any]]:
    """Return all 20 agent–generator connections."""
    return list(CONNECTIONS)


def get_connection_by_agent(agent: str) -> Optional[Dict[str, Any]]:
    """Return connection for an agent name (case-insensitive)."""
    a = agent.strip().lower()
    for c in CONNECTIONS:
        if c.get("agent", "").lower() == a:
            return dict(c)
    return None
