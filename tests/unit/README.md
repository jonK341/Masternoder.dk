# Unit tests (ordered 1–10)

Reusable unit testing for backend services. Same pattern for each feature: **tables_exist** returns bool, and each public function is called and checked for safe return types (no unhandled exceptions).

## Order (matches migration strategy)

| Nr | Feature  | Service module              | Test file                    |
|----|----------|-----------------------------|------------------------------|
| 1  | Generator| generator_db_service, video_generator_service; save reject, background start, _row_to_job edge cases | test_01_generator.py |
| 2  | Battle   | battle_db_service           | test_02_battle.py            |
| 3  | Trophies | trophies_db_service         | test_03_trophies.py          |
| 4  | Chat     | chat_db_service             | test_04_chat.py              |
| 5  | Gallery  | gallery_db_service          | test_05_gallery.py           |
| 6  | Points   | points_db_service           | test_06_points.py            |
| 7  | Shop     | shop_db_service             | test_07_shop.py              |
| 8  | Migrations | generator_migration (idempotent) | test_08_migrations.py |
| 9  | Solutions | response shapes, contracts | test_09_solutions.py         |
| 10 | Content categories / news | content_categories.json (sections + 25 methods), award points, API contract | test_10_content_categories.py |

## Reusable pieces

- **tests/conftest.py** – Pytest: project root on `sys.path`, cwd set.
- **tests/unit/test_utils.py** – Helpers: `ensure_project_root()`, `assert_tables_exist_returns_bool(module, tables_exist_func_name)`, `assert_returns_safe_or_typed(module, func_name, *args, return_type=..., **kwargs)`.

Use these in new test modules: import `test_utils`, call `ensure_project_root()`, then use the assert helpers for `*_tables_exist()` and for each public function (return type or safe fallback).

## How to run

From project root:

```bash
# All unit tests in order (pytest)
pytest tests/unit/ -v

# Or use the runner script
python tests/run_unit_in_order.py

# Without pytest (plain Python)
python tests/run_unit_in_order.py --no-pytest
```

## Adding tests for a new feature

1. Add `tests/unit/test_08_<feature>.py`.
2. In the file: `ensure_project_root()`, then one `test_<feature>_tables_exist()` and one `test_<feature>_<func_name>()` per public function in the service.
3. Add the module to `UNIT_MODULES` in `tests/run_unit_in_order.py`.
