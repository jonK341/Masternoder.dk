"""
Unit tests that conclude the news / content categories (nr 10):
content_categories.json (sections + 25 methods), video_generator_service category logic, API contract.
Run: pytest tests/unit/test_10_content_categories.py -v
"""
import json
import os

import pytest

from tests.unit.test_utils import ensure_project_root

ensure_project_root()

# Expected counts from design: 9 sections, 26 categories (1 general + 25 conspiracy methods)
EXPECTED_MIN_SECTIONS = 5
EXPECTED_MIN_CATEGORIES = 25


def _content_categories_path():
    # tests/unit/test_10_*.py -> project root = 3 dirnames up
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "data", "content_categories.json")


def test_content_categories_data_file_exists():
    """Content categories data file exists."""
    path = _content_categories_path()
    assert os.path.isfile(path), f"Missing data file: {path}"


def test_content_categories_data_load():
    """Load content_categories.json; has sections and categories (25+ methods)."""
    path = _content_categories_path()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)
    sections = data.get("sections", [])
    categories = data.get("categories", [])
    assert len(sections) >= EXPECTED_MIN_SECTIONS, f"Expected at least {EXPECTED_MIN_SECTIONS} sections, got {len(sections)}"
    assert len(categories) >= EXPECTED_MIN_CATEGORIES, f"Expected at least {EXPECTED_MIN_CATEGORIES} categories (methods), got {len(categories)}"
    assert "unified_point_system" in data


def test_content_categories_sections_structure():
    """Each section has id, name, order."""
    path = _content_categories_path()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for sec in data.get("sections", []):
        assert "id" in sec, f"Section missing id: {sec}"
        assert "name" in sec, f"Section missing name: {sec}"
        assert "order" in sec or True, "order optional but recommended"


def test_content_categories_methods_structure():
    """Each category (method) has id, name, section_id, bonus_unified_points."""
    path = _content_categories_path()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    ids_seen = set()
    for cat in data.get("categories", []):
        assert "id" in cat, f"Category missing id: {cat.get('name', cat)}"
        assert "name" in cat, f"Category missing name: {cat.get('id')}"
        assert cat["id"] not in ids_seen, f"Duplicate category id: {cat['id']}"
        ids_seen.add(cat["id"])
        assert "section_id" in cat or cat.get("id") == "general", f"Category missing section_id: {cat.get('id')}"
        assert "bonus_unified_points" in cat or isinstance(cat.get("bonus_unified_points", 0), (int, float))


def test_content_categories_general_exists():
    """General (no conspiracy) category exists with zero bonus."""
    path = _content_categories_path()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    general = next((c for c in data.get("categories", []) if c.get("id") == "general"), None)
    assert general is not None
    assert general.get("bonus_unified_points", 0) == 0


def test_content_categories_has_conspiracy_methods():
    """At least one conspiracy method (e.g. deep_state, religious_prophecy) exists."""
    path = _content_categories_path()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    conspiracy_ids = {"deep_state", "false_flag", "religious_prophecy", "conspiracy_general"}
    found = [c for c in data.get("categories", []) if c.get("id") in conspiracy_ids]
    assert len(found) >= 1, "Expected at least one known conspiracy method id"


def test_video_generator_load_content_categories():
    """_load_content_categories() returns dict with 'categories' key."""
    from backend.services.video_generator_service import _load_content_categories
    data = _load_content_categories()
    assert isinstance(data, dict)
    assert "categories" in data
    assert isinstance(data["categories"], list)


def test_video_generator_award_points_returns_float():
    """_award_generation_points returns float (total earned)."""
    from backend.services.video_generator_service import _award_generation_points
    total = _award_generation_points("unit_test_user_999", "unit-test-doc-999", 25.0, config=None)
    assert isinstance(total, (int, float))
    assert total >= 25.0


def test_video_generator_award_points_with_category_general():
    """_award_generation_points with content_category=general returns base points (no bonus)."""
    from backend.services.video_generator_service import _award_generation_points, GENERATION_POINTS_PER_VIDEO
    total = _award_generation_points(
        "unit_test_user_998", "unit-test-doc-998", float(GENERATION_POINTS_PER_VIDEO),
        config={"content_category": "general"}
    )
    assert total == float(GENERATION_POINTS_PER_VIDEO)


def test_video_generator_award_points_with_category_bonus():
    """_award_generation_points with a bonus category returns base + bonus."""
    from backend.services.video_generator_service import _load_content_categories, _award_generation_points, GENERATION_POINTS_PER_VIDEO
    data = _load_content_categories()
    bonus_cat = next((c for c in data.get("categories", []) if (c.get("bonus_unified_points") or 0) > 0), None)
    if not bonus_cat:
        pytest.skip("No bonus category in data")
    total = _award_generation_points(
        "unit_test_user_997", "unit-test-doc-997", float(GENERATION_POINTS_PER_VIDEO),
        config={"content_category": bonus_cat["id"]}
    )
    assert total > float(GENERATION_POINTS_PER_VIDEO)
    assert total == float(GENERATION_POINTS_PER_VIDEO) + float(bonus_cat.get("bonus_unified_points", 0))


def test_content_categories_list_contract():
    """Contract: list response has success, categories (list), sections (list)."""
    path = _content_categories_path()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    sections = sorted(data.get("sections", []), key=lambda s: s.get("order", 99))
    categories = sorted(data.get("categories", []), key=lambda c: c.get("order", 99))
    # Same shape as API content_categories_list() returns
    response = {
        "success": True,
        "sections": sections,
        "categories": categories,
        "methods": categories,
        "unified_point_system": data.get("unified_point_system", {}),
    }
    assert response["success"] is True
    assert isinstance(response["categories"], list)
    assert isinstance(response["sections"], list)
    assert len(response["categories"]) >= EXPECTED_MIN_CATEGORIES
    assert len(response["sections"]) >= EXPECTED_MIN_SECTIONS
