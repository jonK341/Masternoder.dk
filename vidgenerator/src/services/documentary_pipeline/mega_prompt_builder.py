"""
Mega Prompt Builder
Builds comprehensive prompts from all gathered data sources
"""
from typing import Dict, Any, Optional


def build_mega_prompt(gathered_data: Dict[str, Any], original_prompt: str, title: str) -> str:
    """
    Build a mega prompt from all gathered data sources
    
    Args:
        gathered_data: Dictionary containing all gathered data (web, stats, behavior, xp, etc.)
        original_prompt: Original user prompt
        title: Documentary title
    
    Returns:
        Comprehensive mega prompt string
    """
    parts = []
    
    # 1. Original prompt/topic
    parts.append(f"TOPIC: {title}")
    parts.append(f"ORIGINAL PROMPT: {original_prompt}")
    parts.append("")
    
    # 2. Wikipedia content
    if gathered_data.get('web', {}).get('wikipedia'):
        wiki = gathered_data['web']['wikipedia']
        parts.append("WIKIPEDIA CONTENT:")
        parts.append(f"Title: {wiki.get('title', '')}")
        parts.append(f"Content: {wiki.get('content', '')}")
        parts.append("")
    
    # 3. Images context
    if gathered_data.get('web', {}).get('images'):
        images = gathered_data['web']['images']
        if len(images) > 0:
            parts.append(f"VISUAL CONTEXT ({len(images)} images):")
            for idx, img in enumerate(images[:10], 1):
                parts.append(f"  Image {idx}: {img.get('title', img.get('description', 'Visual element'))}")
            parts.append("")
    
    # 4. News context
    if gathered_data.get('web', {}).get('news'):
        news = gathered_data['web']['news']
        if len(news) > 0:
            parts.append(f"NEWS CONTEXT ({len(news)} articles):")
            for idx, article in enumerate(news[:5], 1):
                parts.append(f"  Article {idx}: {article.get('title', '')}")
                if article.get('description'):
                    parts.append(f"    {article.get('description', '')}")
            parts.append("")
    
    # 5. Search results
    if gathered_data.get('search', {}).get('searches'):
        searches = gathered_data['search']['searches']
        if len(searches) > 0:
            parts.append("SEARCH RESULTS:")
            for search in searches:
                parts.append(f"  Search: \"{search.get('term', '')}\" - {search.get('count', 0)} results")
            parts.append("")
    
    # 6. Behavioral preferences
    if gathered_data.get('behavior', {}).get('preferences'):
        prefs = gathered_data['behavior']['preferences']
        if prefs:
            parts.append("USER PREFERENCES:")
            parts.append(_format_dict(prefs))
            parts.append("")
    
    # 7. XP and achievements
    if gathered_data.get('xp'):
        xp = gathered_data['xp']
        parts.append("USER LEVEL & ACHIEVEMENTS:")
        parts.append(f"  Level: {xp.get('level', 1)}")
        parts.append(f"  Total XP: {xp.get('total_xp', 0)}")
        if xp.get('achievements'):
            parts.append(f"  Achievements: {', '.join(xp['achievements'])}")
        parts.append("")
    
    # 8. Psychological profile
    if gathered_data.get('psychological', {}).get('traits'):
        traits = gathered_data['psychological']['traits']
        if traits:
            parts.append("PSYCHOLOGICAL PROFILE:")
            parts.append(_format_dict(traits))
            parts.append("")
    
    # 9. Emotion context
    if gathered_data.get('emotion', {}).get('profile'):
        emotion = gathered_data['emotion']['profile']
        if emotion:
            parts.append("EMOTION CONTEXT:")
            parts.append(_format_dict(emotion))
            if gathered_data.get('emotion', {}).get('triggers'):
                parts.append(f"  Active Triggers: {len(gathered_data['emotion']['triggers'])}")
            parts.append("")
    
    # 10. Matrix system path
    if gathered_data.get('matrix', {}).get('optimal_path'):
        path = gathered_data['matrix']['optimal_path']
        if path:
            parts.append("OPTIMAL GENERATION PATH:")
            parts.append(_format_list(path))
            parts.append("")
    
    # 11. Stats and quality metrics
    if gathered_data.get('stats', {}).get('quality_scores'):
        scores = gathered_data['stats']['quality_scores']
        if scores:
            parts.append("QUALITY METRICS:")
            parts.append(_format_dict(scores))
            parts.append("")
    
    # 12. Generation instructions
    parts.append("GENERATION INSTRUCTIONS:")
    parts.append("Create engaging video clips that:")
    parts.append("- Tell a compelling story about the topic")
    parts.append("- Use visual elements from gathered images")
    parts.append("- Incorporate recent news and developments")
    parts.append("- Match user preferences and psychological profile")
    parts.append("- Follow optimal generation path from matrix system")
    parts.append("- Apply emotion triggers for enhanced engagement")
    parts.append("- Maintain quality standards from previous generations")
    
    return "\n".join(parts)


def _format_dict(d: Dict[str, Any], indent: int = 2) -> str:
    """Format dictionary as readable string"""
    lines = []
    for key, value in d.items():
        if isinstance(value, dict):
            lines.append(f"{' ' * indent}{key}:")
            lines.append(_format_dict(value, indent + 2))
        elif isinstance(value, list):
            lines.append(f"{' ' * indent}{key}: {', '.join(str(v) for v in value[:5])}")
        else:
            lines.append(f"{' ' * indent}{key}: {value}")
    return "\n".join(lines)


def _format_list(l: list, indent: int = 2) -> str:
    """Format list as readable string"""
    lines = []
    for idx, item in enumerate(l[:10], 1):  # Limit to 10 items
        if isinstance(item, dict):
            lines.append(f"{' ' * indent}Step {idx}:")
            lines.append(_format_dict(item, indent + 2))
        else:
            lines.append(f"{' ' * indent}Step {idx}: {item}")
    return "\n".join(lines)

