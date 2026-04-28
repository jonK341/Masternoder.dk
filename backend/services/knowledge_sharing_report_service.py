"""
Knowledge-sharing report ingredients for reporter_agent (broadcast / cron).
Builds structured snippets from agent knowledge, themes, and platform paths for compendium/news flows.
"""
import os
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _safe_read_json(path: str) -> Any:
    try:
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return None


def build_knowledge_ingredients() -> Dict[str, Any]:
    """Return news-report ingredients for knowledge sharing (rulebooks, compendium, agent knowledge)."""
    now = datetime.now(timezone.utc).isoformat()
    kb_path = os.path.join(BASE_DIR, 'data', 'agent_learning_knowledge.json')
    kb = _safe_read_json(kb_path) or {}
    entries: List[Dict] = list(kb.get('entries') or [])
    ingredients: List[Dict[str, str]] = []
    for e in entries[:50]:
        ingredients.append({
            'id': str(e.get('id', '')),
            'title': str(e.get('title', ''))[:200],
            'snippet': str(e.get('text', ''))[:400],
            'rulebook_ref': ','.join(e.get('rulebook_ref') or []) if isinstance(e.get('rulebook_ref'), list) else '',
        })

    themes_path = os.path.join(BASE_DIR, 'backend', 'services', 'themes_list.py')
    theme_hint = 'themes_list (generator themes)'
    if os.path.isfile(themes_path):
        theme_hint = 'themes_list.py present (theme registry)'

    skills_dir = os.path.join(BASE_DIR, 'logs', 'user_agent_skills')
    n_skill_files = 0
    try:
        n_skill_files = len([f for f in os.listdir(skills_dir) if f.endswith('.json')])
    except Exception:
        pass

    return {
        'generated_at': now,
        'agent_id': 'reporter_agent',
        'skills': ['broadcast', 'news_report_ingredients'],
        'knowledge_base': {
            'path': kb_path,
            'updated_at': kb.get('updated_at'),
            'entry_count': len(entries),
        },
        'ingredients': ingredients,
        'platform_hints': {
            'user_agent_skills_files': n_skill_files,
            'themes_registry': theme_hint,
            'broadcast_targets': ['/aggregator', '/compendium', '/agents', '/gallery'],
        },
    }


def append_ingredients_log(payload: Dict[str, Any]) -> str:
    """Append one JSON line to logs for audit (cron / reporter)."""
    log_dir = os.path.join(BASE_DIR, 'logs', 'knowledge_sharing')
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, 'ingredients.jsonl')
    line = json.dumps(payload, ensure_ascii=False) + '\n'
    with open(path, 'a', encoding='utf-8') as f:
        f.write(line)
    return path
