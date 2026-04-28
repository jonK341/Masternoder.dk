"""
Agent AI profiles for role-specific behavior.
Keeps prompts and model controls centralized for all agent routes.
"""
from typing import Dict, Any


AGENT_AI_PROFILES: Dict[str, Dict[str, Any]] = {
    "manager_status": {
        "profile_name": "Manager Status Interpreter",
        "system_prompt": (
            "Interpret manager agent status and produce concise operational guidance."
        ),
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_tokens": 220,
        "allowed_actions": ["summarize_status", "recommend_next_steps"],
    },
    "manager_activate_all": {
        "profile_name": "Manager Activation Planner",
        "system_prompt": (
            "Evaluate activation outcomes and prioritize safe follow-up actions."
        ),
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_tokens": 260,
        "allowed_actions": ["analyze_activation", "prioritize_recovery", "recommend_next_steps"],
    },
    "manager_auto_fix": {
        "profile_name": "Manager Auto-Fix Advisor",
        "system_prompt": (
            "You are the Manager agent AI advisor for operational fixes. "
            "Propose practical, low-risk actions with priority order. "
            "Focus on system stability and explicit next steps."
        ),
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_tokens": 350,
        "allowed_actions": [
            "diagnose",
            "recommend_fix",
            "prioritize_tasks",
            "summarize_risk",
        ],
    },
    "manager_assign_task": {
        "profile_name": "Manager Task Assignment Advisor",
        "system_prompt": (
            "Review task assignment payloads and propose efficient execution guidance."
        ),
        "model": "gpt-4o-mini",
        "temperature": 0.25,
        "max_tokens": 240,
        "allowed_actions": ["validate_task", "recommend_execution", "flag_risks"],
    },
    "secretary_status": {
        "profile_name": "Secretary Status Interpreter",
        "system_prompt": (
            "Interpret secretary status and suggest practical next actions."
        ),
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_tokens": 220,
        "allowed_actions": ["summarize_status", "recommend_next_steps"],
    },
    "secretary_coordinate_activation": {
        "profile_name": "Secretary Coordination Advisor",
        "system_prompt": (
            "Review coordination outcomes and suggest process improvements."
        ),
        "model": "gpt-4o-mini",
        "temperature": 0.25,
        "max_tokens": 250,
        "allowed_actions": ["review_coordination", "identify_gaps", "recommend_next_steps"],
    },
    "secretary_generate_report": {
        "profile_name": "Secretary Reporting Assistant",
        "system_prompt": (
            "You are the Secretary agent AI assistant. "
            "Write concise operational summaries and recommendations from provided data. "
            "Keep language clear and useful for follow-up execution."
        ),
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 350,
        "allowed_actions": [
            "summarize",
            "highlight_issues",
            "recommend_next_steps",
        ],
    },
    "secretary_document": {
        "profile_name": "Secretary Documentation Assistant",
        "system_prompt": (
            "You are the Secretary documentation AI. "
            "Turn activity details into concise structured notes and actionable follow-ups."
        ),
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_tokens": 260,
        "allowed_actions": [
            "summarize_activity",
            "identify_followups",
        ],
    },
    "secretary_schedule_auto_fix": {
        "profile_name": "Secretary Scheduling Advisor",
        "system_prompt": (
            "Review scheduling setups and suggest robust automation cadence."
        ),
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_tokens": 220,
        "allowed_actions": ["review_schedule", "recommend_cadence", "flag_risks"],
    },
    "debugging_master_status": {
        "profile_name": "Debugging Master Status Analyst",
        "system_prompt": (
            "You are a debugging operations analyst. "
            "Summarize platform health, highlight top risks, and suggest low-risk improvements."
        ),
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_tokens": 300,
        "allowed_actions": [
            "summarize_status",
            "identify_risks",
            "propose_improvements",
        ],
    },
    "debugging_session_review": {
        "profile_name": "Debugging Session Reviewer",
        "system_prompt": (
            "You review debugging sessions and extract actionable findings. "
            "Prioritize reproducibility, root cause clues, and the next verification steps."
        ),
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_tokens": 320,
        "allowed_actions": [
            "analyze_session",
            "identify_root_cause",
            "recommend_next_steps",
        ],
    },
    "debugging_analytics_insights": {
        "profile_name": "Debugging Analytics Insights",
        "system_prompt": (
            "You analyze debugging analytics and convert patterns into concrete actions. "
            "Focus on trends, risk hotspots, and measurable follow-ups."
        ),
        "model": "gpt-4o-mini",
        "temperature": 0.25,
        "max_tokens": 320,
        "allowed_actions": [
            "analyze_trends",
            "flag_hotspots",
            "recommend_actions",
        ],
    },
    "debugging_profiles_review": {
        "profile_name": "Debugging Profile Insights",
        "system_prompt": (
            "Analyze browser profile statistics and provide concise reliability improvements."
        ),
        "model": "gpt-4o-mini",
        "temperature": 0.25,
        "max_tokens": 260,
        "allowed_actions": ["analyze_profiles", "identify_risk", "recommend_actions"],
    },
    "debugging_stats_review": {
        "profile_name": "Debugging Stats Analyst",
        "system_prompt": (
            "Interpret debugging statistics and provide a prioritized action checklist."
        ),
        "model": "gpt-4o-mini",
        "temperature": 0.25,
        "max_tokens": 260,
        "allowed_actions": ["analyze_stats", "prioritize_actions", "recommend_next_steps"],
    },
}


def get_agent_ai_profile(profile_key: str) -> Dict[str, Any]:
    """Return profile config; empty dict when unknown."""
    return AGENT_AI_PROFILES.get(profile_key, {})
