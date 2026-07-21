"""P4 ops/deploy upgrades — static verification (items 161–190)."""
import os


ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def _read(*parts):
    path = os.path.join(ROOT, *parts)
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_p4_173_nginx_cache_example():
    cfg = _read("config", "nginx", "mn2-explorer-cache.conf.example")
    assert "network-overview" in cfg
    assert "explorer/stream" in cfg


def test_p4_174_network_snapshot_cron():
    assert os.path.isfile(os.path.join(ROOT, "cron", "mn2_network_snapshot.sh"))
    cron = _read("cron", "masternoder-mn2-network-snapshot.cron.d")
    assert "mn2_network_snapshot.sh" in cron


def test_p4_175_probe_alert_script():
    js = _read("scripts", "mn2_explorer_probe_alert.py")
    assert "DISCORD_WEBHOOK_URL" in js
    assert "explorer/status" in js


def test_p4_176_grafana_dashboard():
    path = os.path.join(ROOT, "ops", "grafana", "mn2-network-history-dashboard.json")
    assert os.path.isfile(path)
    assert "mn2-network-history" in _read("ops", "grafana", "mn2-network-history-dashboard.json")


def test_p4_177_smoke_deploy_script():
    smoke = _read("scripts", "smoke_explorer_deploy.py")
    assert "network-overview" in smoke
    assert "recent-blocks" in smoke
    assert "/api/mn2/services" in smoke


def test_p4_180_gitignore_history():
    gi = _read(".gitignore")
    assert "mn2_network_history.jsonl" in gi


def test_p4_181_mongo_backup_script():
    sh = _read("scripts", "backup_eiquidus_mongo.sh")
    assert "mongodump" in sh


def test_p4_182_health_explorer_probe():
    health = _read("backend", "routes", "health_routes.py")
    break_check = _read("scripts", "_health_break_check.py")
    assert "explorer_probe" in health
    assert "explorer/status" in break_check


def test_p4_183_deploy_cdn_note():
    deploy = _read("scripts", "deploy.py")
    assert "CDN cache" in deploy or "edge cache" in deploy


def test_p4_184_185_ops_docs():
    doc = _read("docs", "EXPLORER_OPS_P4.md")
    assert "Blue/green" in doc
    assert "Staging mirror" in doc


def test_p4_186_sse_load_test():
    lt = _read("scripts", "load_test_explorer_sse.py")
    assert "explorer/stream" in lt
    assert "clients" in lt


def test_p4_187_explorer_metrics():
    py = _read("backend", "services", "mn2_explorer_metrics.py")
    routes = _read("backend", "routes", "mn2_staking_routes.py")
    assert "record_api_call" in py
    assert "_explorer_metrics_after" in routes


def test_p4_188_189_feature_flags():
    flags = _read("backend", "services", "mn2_explorer_flags.py")
    routes = _read("backend", "routes", "mn2_staking_routes.py")
    assert "EXPLORER_HUB_V2" in flags
    assert "CANARY_PERCENT" in flags
    assert "hub_v2_enabled" in routes


def test_p4_190_pr_template():
    tpl = _read(".github", "PULL_REQUEST_TEMPLATE.md")
    assert "smoke_explorer_deploy" in tpl
    assert "Post-deploy" in tpl


def test_p4_172_rich_list_index_synced():
    py = _read("backend", "services", "mn2_explorer_data.py")
    assert "index_synced" in py


def test_p4_deploy_manifest_includes_ops_scripts():
    deploy = _read("scripts", "deploy.py")
    assert "smoke_explorer_deploy.py" in deploy
    assert "mn2_explorer_probe_alert.py" in deploy
