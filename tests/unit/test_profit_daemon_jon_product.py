import json
from pathlib import Path


def test_top25_catalog_has_twenty_five_unique_keys():
    root = Path(__file__).resolve().parents[2]
    catalog = json.loads((root / "profit_daemon_jon" / "top25_technologies.json").read_text(encoding="utf-8"))
    techs = catalog["technologies"]
    assert len(techs) == 25
    keys = [t["key"] for t in techs]
    assert len(set(keys)) == 25
    assert [t["id"] for t in techs] == list(range(1, 26))


def test_install_top25_marks_state(tmp_path, monkeypatch):
    from backend.services import profit_daemon_jon_product_service as prod

    monkeypatch.setattr(prod, "_STATE", str(tmp_path / "tech.json"))
    out = prod.install_top25(pip=False)
    assert out["success"] is True
    assert out["installed"] == 25
    status = prod.status_report()
    assert status["total"] == 25
    assert status["installed"] == 25
    backlog = prod.product_improvement_backlog()
    assert backlog["total"] >= 20
    assert backlog["done"] == backlog["total"]
    assert backlog["open"] == 0


def test_runner_brand_constant():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "profit_daemon_jon" / "run.py"
    spec = importlib.util.spec_from_file_location("pdj_run", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    assert "Profit Daemon Jon" in mod.BRAND
