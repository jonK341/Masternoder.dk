"""MasterNoder crypto exchange API — 25 assets, swap, limit orders, tax, bonuses."""
import os
import urllib.parse

from flask import Blueprint, jsonify, request

from backend.services.account_resolution_service import resolve_user_id
from backend.services import crypto_exchange_service as ex

crypto_exchange_bp = Blueprint("crypto_exchange", __name__)


def _uid(from_body: bool = False) -> str:
    if from_body:
        data = request.get_json(silent=True) or {}
        if data.get("user_id"):
            return str(data["user_id"]).strip()
    return resolve_user_id(from_body=from_body, from_query=True)


def _base_url() -> str:
    base = (os.environ.get("BASE_URL") or "").strip().rstrip("/")
    if base.endswith("/vidgenerator"):
        base = base.rsplit("/vidgenerator", 1)[0]
    return base or request.url_root.rstrip("/")


def _mn2_paypal_pack(pack_id: str):
    from backend.routes.shop_routes import get_mn2_pack_map

    pack = get_mn2_pack_map().get((pack_id or "").strip())
    if not pack:
        return None
    rails = [str(r).lower() for r in (pack.get("payment_rails") or pack.get("rails") or [])]
    if rails and "paypal" not in rails:
        return None
    if float(pack.get("price_usd") or 0) <= 0 or float(pack.get("mn2_granted") or 0) <= 0:
        return None
    return pack


@crypto_exchange_bp.route("/api/exchange/health", methods=["GET"])
def exchange_health():
    return jsonify(ex.health()), 200


@crypto_exchange_bp.route("/api/exchange/catalog", methods=["GET"])
def exchange_catalog():
    return jsonify(ex.get_catalog())


@crypto_exchange_bp.route("/api/exchange/tickers", methods=["GET"])
def exchange_tickers():
    return jsonify(ex.get_all_tickers())


@crypto_exchange_bp.route("/api/exchange/ticker/<symbol>", methods=["GET"])
def exchange_ticker(symbol):
    result = ex.get_ticker(symbol)
    code = 200 if result.get("success") else 404
    return jsonify(result), code


@crypto_exchange_bp.route("/api/exchange/wallet", methods=["GET"])
def exchange_wallet():
    return jsonify(ex.get_wallet(_uid()))


@crypto_exchange_bp.route("/api/exchange/quote", methods=["POST"])
def exchange_quote():
    data = request.get_json(silent=True) or {}
    return jsonify(ex.quote_swap(
        _uid(from_body=True),
        data.get("symbol"),
        data.get("side"),
        float(data.get("amount") or 0),
        data.get("quote") or "MN2",
    ))


@crypto_exchange_bp.route("/api/exchange/swap", methods=["POST"])
def exchange_swap():
    data = request.get_json(silent=True) or {}
    return jsonify(ex.execute_swap(
        _uid(from_body=True),
        data.get("quote_id") or "",
        data.get("symbol"),
        data.get("side"),
        float(data.get("amount") or 0),
        data.get("quote") or "MN2",
    ))


@crypto_exchange_bp.route("/api/exchange/orders", methods=["GET"])
def exchange_orders_list():
    symbol = request.args.get("symbol")
    side = request.args.get("side")
    limit = int(request.args.get("limit") or 50)
    return jsonify(ex.list_orders(symbol=symbol, side=side, limit=limit))


@crypto_exchange_bp.route("/api/exchange/orders", methods=["POST"])
def exchange_orders_create():
    data = request.get_json(silent=True) or {}
    return jsonify(ex.create_limit_order(
        _uid(from_body=True),
        data.get("symbol"),
        data.get("side"),
        float(data.get("amount") or 0),
        float(data.get("limit_price") or 0),
        data.get("quote") or "MN2",
    ))


@crypto_exchange_bp.route("/api/exchange/orders/cancel", methods=["POST"])
def exchange_orders_cancel():
    data = request.get_json(silent=True) or {}
    return jsonify(ex.cancel_order(_uid(from_body=True), data.get("order_id")))


@crypto_exchange_bp.route("/api/exchange/trades", methods=["GET"])
def exchange_trades():
    limit = int(request.args.get("limit") or 30)
    return jsonify(ex.list_trades(limit=limit))


@crypto_exchange_bp.route("/api/exchange/bonus/claim", methods=["POST"])
def exchange_bonus_claim():
    data = request.get_json(silent=True) or {}
    return jsonify(ex.claim_welcome_bonus(
        _uid(from_body=True),
        data.get("terms_version") or "",
        bool(data.get("accepted")),
    ))


@crypto_exchange_bp.route("/api/exchange/staking/claim", methods=["POST"])
def exchange_staking_claim():
    data = request.get_json(silent=True) or {}
    return jsonify(ex.claim_staking_rewards(_uid(from_body=True), data.get("symbol")))


@crypto_exchange_bp.route("/api/exchange/tax-report", methods=["GET"])
def exchange_tax_report():
    year = request.args.get("year")
    return jsonify(ex.get_tax_report(_uid(), int(year) if year else None))


@crypto_exchange_bp.route("/api/exchange/rewards", methods=["GET"])
def exchange_rewards():
    return jsonify(ex.get_rewards_status(_uid()))


@crypto_exchange_bp.route("/api/exchange/user-progress", methods=["GET"])
def exchange_user_progress():
    return jsonify(ex.get_user_progress_report(_uid()))


@crypto_exchange_bp.route("/api/exchange/profit-agent", methods=["GET"])
def exchange_profit_agent():
    from backend.services.crypto_exchange_profit_agent_service import build_profit_report

    return jsonify(build_profit_report(_uid()))


@crypto_exchange_bp.route("/api/exchange/gateway/status", methods=["GET"])
def exchange_gateway_status():
    from backend.services.crypto_exchange_gateway_service import gateway_status

    return jsonify(gateway_status())


def _admin_authorized() -> bool:
    secret = (
        os.environ.get("EXCHANGE_ADMIN_KEY")
        or os.environ.get("COGS_ADMIN_REPORT_KEY")
        or ""
    ).strip()
    if not secret:
        return False
    got = (
        request.headers.get("X-Exchange-Admin-Key")
        or request.headers.get("X-Admin-Key")
        or request.args.get("admin_key")
        or ""
    ).strip()
    return bool(got) and got == secret


@crypto_exchange_bp.route("/api/exchange/admin/board", methods=["GET"])
def exchange_admin_board():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.crypto_exchange_admin_service import admin_board

    return jsonify(admin_board())


@crypto_exchange_bp.route("/api/exchange/admin/audit", methods=["GET"])
def exchange_admin_audit():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    limit = int(request.args.get("limit") or 50)
    tail = ex.get_audit_tail(limit=limit)
    tail["chain"] = ex.verify_audit_chain()
    return jsonify(tail)


@crypto_exchange_bp.route("/api/exchange/arbitrage/venues", methods=["GET"])
def exchange_arbitrage_venues():
    from backend.services.external_exchange_connector_service import list_venues

    return jsonify(list_venues())


@crypto_exchange_bp.route("/api/exchange/arbitrage/overview", methods=["GET"])
def exchange_arbitrage_overview():
    from backend.services.exchange_arbitrage_service import arbitrage_overview

    return jsonify(arbitrage_overview())


@crypto_exchange_bp.route("/api/exchange/arbitrage/scan", methods=["GET"])
def exchange_arbitrage_scan():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_arbitrage_service import scan_opportunities

    syms = request.args.get("symbols")
    symbols = [s.strip().upper() for s in syms.split(",")] if syms else None
    return jsonify(scan_opportunities(symbols))


@crypto_exchange_bp.route("/api/exchange/arbitrage/run", methods=["POST"])
def exchange_arbitrage_run():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_arbitrage_service import run_paper_tick

    return jsonify(run_paper_tick())


@crypto_exchange_bp.route("/api/exchange/arbitrage/accounts", methods=["GET"])
def exchange_arbitrage_accounts():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_arbitrage_service import agent_accounts

    return jsonify(agent_accounts())


@crypto_exchange_bp.route("/api/exchange/arbitrage/vault/status", methods=["GET"])
def exchange_arbitrage_vault_status():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_secrets_vault_service import vault_status, list_secret_names

    status = vault_status()
    status["secret_names"] = list_secret_names()
    return jsonify(status)


@crypto_exchange_bp.route("/api/exchange/arbitrage/vault/secret", methods=["POST"])
def exchange_arbitrage_vault_set_secret():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_secrets_vault_service import set_secret

    data = request.get_json(silent=True) or {}
    return jsonify(set_secret(data.get("name"), data.get("value")))


@crypto_exchange_bp.route("/api/exchange/arbitrage/wallets", methods=["GET"])
def exchange_arbitrage_wallets():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_secrets_vault_service import list_wallets

    return jsonify({"success": True, "wallets": list_wallets()})


@crypto_exchange_bp.route("/api/exchange/arbitrage/wallets", methods=["POST"])
def exchange_arbitrage_wallet_register():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_secrets_vault_service import register_wallet

    data = request.get_json(silent=True) or {}
    return jsonify(register_wallet(
        data.get("label"),
        data.get("address"),
        venue=data.get("venue", ""),
        asset=data.get("asset", ""),
        note=data.get("note", ""),
    ))


@crypto_exchange_bp.route("/api/exchange/ai-trading/status", methods=["GET"])
def exchange_ai_trading_status():
    from backend.services.exchange_ai_trading_service import ai_trading_status

    return jsonify(ai_trading_status())


@crypto_exchange_bp.route("/api/exchange/ai-trading/analyze", methods=["GET"])
def exchange_ai_trading_analyze():
    from backend.services.exchange_ai_trading_service import analyze_market

    syms = request.args.get("symbols")
    symbols = [s.strip().upper() for s in syms.split(",")] if syms else None
    probe = request.args.get("probe", "0").strip() == "1"
    return jsonify(analyze_market(symbols=symbols, probe_venues=probe))


@crypto_exchange_bp.route("/api/exchange/ai-trading/run", methods=["POST"])
def exchange_ai_trading_run():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_ai_trading_service import run_ai_tick

    return jsonify(run_ai_tick())


@crypto_exchange_bp.route("/api/exchange/ai-trading/venues", methods=["GET"])
def exchange_ai_trading_venues():
    from backend.services import exchange_venue_api_service as vapi

    return jsonify(vapi.list_venue_capabilities())


@crypto_exchange_bp.route("/api/exchange/ai-trading/probe", methods=["POST"])
def exchange_ai_trading_probe():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services import exchange_venue_api_service as vapi

    return jsonify(vapi.probe_all_venues())


@crypto_exchange_bp.route("/api/exchange/treasury/status", methods=["GET"])
def exchange_treasury_status():
    from backend.services.exchange_treasury_service import treasury_status
    mode = (request.args.get("mode") or "").strip() or None
    return jsonify(treasury_status(mode=mode))


@crypto_exchange_bp.route("/api/exchange/treasury/liquidity/run", methods=["POST"])
def exchange_treasury_liquidity_run():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_treasury_liquidity_service import run_liquidity_tick

    return jsonify(run_liquidity_tick())


@crypto_exchange_bp.route("/api/exchange/venues/credentials", methods=["POST"])
def exchange_venues_credentials_onboard():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services import exchange_venue_api_service as vapi

    data = request.get_json(silent=True) or {}
    return jsonify(vapi.onboard_venue_credentials(
        str(data.get("venue_id") or ""),
        api_key=data.get("api_key"),
        api_secret=data.get("api_secret"),
        passphrase=data.get("passphrase"),
    ))


@crypto_exchange_bp.route("/api/exchange/arbitrage/rebalance/run", methods=["POST"])
def exchange_arbitrage_rebalance_run():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_arbitrage_service import run_rebalance_tick

    return jsonify(run_rebalance_tick())


@crypto_exchange_bp.route("/api/exchange/sales-pool/status", methods=["GET"])
def exchange_sales_pool_status():
    from backend.services.exchange_sales_pool_service import sales_pool_status

    return jsonify(sales_pool_status())


@crypto_exchange_bp.route("/api/exchange/sales-pool/transfer", methods=["POST"])
def exchange_sales_pool_transfer():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_sales_pool_service import transfer_to_sales_pool

    data = request.get_json(silent=True) or {}
    return jsonify(transfer_to_sales_pool(force=bool(data.get("force"))))


@crypto_exchange_bp.route("/api/exchange/live/readiness", methods=["GET"])
def exchange_live_readiness():
    from backend.services.exchange_live_execution_service import live_readiness
    return jsonify(live_readiness())


@crypto_exchange_bp.route("/api/exchange/daemon-mesh/run", methods=["POST"])
def exchange_daemon_mesh_run():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_daemon_matcher_service import run_mesh_tick
    return jsonify(run_mesh_tick())


@crypto_exchange_bp.route("/api/exchange/control-board/overview", methods=["GET"])
def exchange_control_board_overview():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.trading_bots_control_service import business_overview

    return jsonify(business_overview())


@crypto_exchange_bp.route("/api/exchange/control-board/run", methods=["POST"])
def exchange_control_board_run():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.trading_bots_control_service import run_all_bots

    data = request.get_json(silent=True) or {}
    return jsonify(run_all_bots(force=bool(data.get("force"))))


@crypto_exchange_bp.route("/api/exchange/control-board/bot", methods=["POST"])
def exchange_control_board_bot():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.trading_bots_control_service import set_bot_enabled

    data = request.get_json(silent=True) or {}
    return jsonify(set_bot_enabled(data.get("bot_id"), bool(data.get("enabled"))))


@crypto_exchange_bp.route("/api/exchange/control-board/supervisor", methods=["POST"])
def exchange_control_board_supervisor():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.trading_bots_control_service import set_supervisor_enabled

    data = request.get_json(silent=True) or {}
    return jsonify(set_supervisor_enabled(data.get("supervisor_id"), bool(data.get("enabled"))))


@crypto_exchange_bp.route("/api/exchange/control-board/kill-switch", methods=["POST"])
def exchange_control_board_kill_switch():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.trading_bots_control_service import set_kill_switch

    data = request.get_json(silent=True) or {}
    return jsonify(set_kill_switch(bool(data.get("on"))))


@crypto_exchange_bp.route("/api/exchange/bot-skills", methods=["GET"])
def exchange_bot_skills():
    from backend.services.exchange_bot_skills_service import list_skills

    return jsonify(list_skills())


@crypto_exchange_bp.route("/api/exchange/calculator/cross-trade", methods=["POST"])
def exchange_calculator_cross_trade():
    from backend.services.exchange_profit_calculator_service import cross_trade_projection

    data = request.get_json(silent=True) or {}
    skill_ids = data.get("skills") or []
    if isinstance(skill_ids, str):
        skill_ids = [s.strip() for s in skill_ids.split(",") if s.strip()]
    return jsonify(cross_trade_projection(
        float(data.get("capital_usd") or 0),
        skill_ids,
        volatility=float(data.get("volatility") or 0.35),
        cycles_per_day=float(data.get("cycles_per_day") or 24),
        risk_level=str(data.get("risk_level") or "medium"),
    ))


@crypto_exchange_bp.route("/api/exchange/marketplace/catalog", methods=["GET"])
def exchange_marketplace_catalog():
    from backend.services.agent_marketplace_service import get_catalog

    return jsonify(get_catalog())


@crypto_exchange_bp.route("/api/exchange/marketplace/purchase", methods=["POST"])
def exchange_marketplace_purchase():
    from backend.services.agent_marketplace_service import purchase_agent

    data = request.get_json(silent=True) or {}
    return jsonify(purchase_agent(_uid(from_body=True), data.get("template_id")))


@crypto_exchange_bp.route("/api/exchange/marketplace/my-agents", methods=["GET"])
def exchange_marketplace_my_agents():
    from backend.services.agent_marketplace_service import list_user_agents

    return jsonify(list_user_agents(_uid()))


@crypto_exchange_bp.route("/api/exchange/marketplace/run", methods=["POST"])
def exchange_marketplace_run():
    from backend.services.agent_marketplace_service import run_user_agent_tick, run_all_user_agents

    data = request.get_json(silent=True) or {}
    uid = _uid(from_body=True)
    agent_id = (data.get("agent_id") or "").strip()
    if agent_id:
        return jsonify(run_user_agent_tick(uid, agent_id))
    out = run_all_user_agents(uid)
    try:
        from backend.services.exchange_user_daemon_service import get_config, run_user_daemon
        cfg = get_config(uid).get("config") or {}
        if cfg.get("auto_run_with_marketplace", True) and cfg.get("enabled", True):
            out["daemon"] = run_user_daemon(uid)
    except Exception as exc:
        out["daemon"] = {"success": False, "error": str(exc)}
    return jsonify(out)


@crypto_exchange_bp.route("/api/exchange/daemon/config", methods=["GET"])
def exchange_daemon_config_get():
    from backend.services.exchange_user_daemon_service import get_config
    return jsonify(get_config(_uid()))


@crypto_exchange_bp.route("/api/exchange/daemon/config", methods=["POST"])
def exchange_daemon_config_post():
    from backend.services.exchange_user_daemon_service import save_config
    data = request.get_json(silent=True) or {}
    return jsonify(save_config(_uid(from_body=True), data))


@crypto_exchange_bp.route("/api/exchange/daemon/preview", methods=["GET", "POST"])
def exchange_daemon_preview():
    from backend.services.exchange_user_daemon_service import preview_farm
    data = request.get_json(silent=True) or {}
    venues = data.get("venues") or request.args.getlist("venues") or None
    symbols = data.get("symbols") or request.args.getlist("symbols") or None
    notional = data.get("notional_usd") or request.args.get("notional_usd")
    return jsonify(preview_farm(
        _uid(from_body=(request.method == "POST")),
        venues=venues,
        symbols=symbols,
        notional_usd=float(notional) if notional is not None else None,
    ))


@crypto_exchange_bp.route("/api/exchange/daemon/run", methods=["POST"])
def exchange_daemon_run():
    from backend.services.exchange_user_daemon_service import run_user_daemon
    data = request.get_json(silent=True) or {}
    vol = data.get("volatility")
    return jsonify(run_user_daemon(_uid(from_body=True), volatility=float(vol) if vol is not None else None))


@crypto_exchange_bp.route("/api/exchange/marketplace/portfolio", methods=["GET"])
def exchange_marketplace_portfolio():
    from backend.services.agent_marketplace_service import user_portfolio

    return jsonify(user_portfolio(_uid()))


@crypto_exchange_bp.route("/api/exchange/marketplace/claim-profit", methods=["POST"])
def exchange_marketplace_claim_profit():
    from backend.services.agent_marketplace_service import claim_profit
    data = request.get_json(silent=True) or {}
    return jsonify(claim_profit(_uid(from_body=True), (data.get("agent_id") or "").strip() or None))


@crypto_exchange_bp.route("/api/exchange/prediction", methods=["GET"])
def exchange_prediction():
    from backend.services.exchange_prediction_service import predict_symbol
    from backend.services.external_exchange_connector_service import fetch_prices

    symbol = (request.args.get("symbol") or "BTC").strip().upper()
    prices = fetch_prices([symbol]).get("prices") or {}
    return jsonify({"success": True, **predict_symbol(symbol, prices)})


@crypto_exchange_bp.route("/api/exchange/prediction/batch", methods=["GET"])
def exchange_prediction_batch():
    from backend.services.exchange_prediction_service import predict_batch
    from backend.services.external_exchange_connector_service import fetch_prices

    syms = request.args.get("symbols")
    symbols = [s.strip().upper() for s in syms.split(",")] if syms else None
    prices = fetch_prices(symbols).get("prices") or {}
    return jsonify(predict_batch(symbols, prices))


@crypto_exchange_bp.route("/api/exchange/profit-tools/radar", methods=["GET"])
def exchange_profit_tools_radar():
    from backend.services.exchange_profit_tools_service import opportunity_radar

    syms = request.args.get("symbols")
    symbols = [s.strip().upper() for s in syms.split(",")] if syms else None
    return jsonify(opportunity_radar(symbols, limit=int(request.args.get("limit") or 10)))


@crypto_exchange_bp.route("/api/exchange/profit-tools/compounding", methods=["POST"])
def exchange_profit_tools_compounding():
    from backend.services.exchange_profit_tools_service import compounding_plan

    data = request.get_json(silent=True) or {}
    return jsonify(compounding_plan(
        float(data.get("capital_usd") or 0),
        float(data.get("daily_profit_usd") or 0),
        float(data.get("target_usd") or 0),
        reinvest_pct=float(data.get("reinvest_pct") or 100),
    ))


@crypto_exchange_bp.route("/api/exchange/profit-tools/simulate", methods=["POST"])
def exchange_profit_tools_simulate():
    from backend.services.exchange_profit_tools_service import simulate_strategy

    data = request.get_json(silent=True) or {}
    return jsonify(simulate_strategy(
        float(data.get("capital_usd") or 0),
        float(data.get("edge_bps") or 0),
        cycles=int(data.get("cycles") or 100),
        volatility=float(data.get("volatility") or 0.35),
        risk_level=str(data.get("risk_level") or "medium"),
        runs=int(data.get("runs") or 500),
    ))


@crypto_exchange_bp.route("/api/exchange/premium/features", methods=["GET"])
def exchange_premium_features():
    from backend.services.exchange_premium_service import premium_features

    return jsonify(premium_features())


@crypto_exchange_bp.route("/api/exchange/profit-tools/boost", methods=["POST"])
def exchange_profit_tools_boost():
    from backend.services.exchange_profit_tools_service import boost_scenarios

    data = request.get_json(silent=True) or {}
    skill_ids = data.get("skills") or ["spatial_arbitrage", "triangular_arbitrage"]
    if isinstance(skill_ids, str):
        skill_ids = [s.strip() for s in skill_ids.split(",") if s.strip()]
    return jsonify(boost_scenarios(
        float(data.get("capital_usd") or 0),
        skill_ids,
        base_cycles=float(data.get("base_cycles") or 24),
    ))


@crypto_exchange_bp.route("/api/exchange/monitor/live", methods=["GET"])
def exchange_monitor_live():
    from backend.services.exchange_trading_monitor_service import live_monitor

    return jsonify(live_monitor(_uid(), feed_limit=int(request.args.get("limit") or 40)))


@crypto_exchange_bp.route("/api/exchange/trust/me", methods=["GET"])
def exchange_trust_me():
    from backend.services.exchange_trust_service import user_trust_profile

    return jsonify(user_trust_profile(_uid()))


@crypto_exchange_bp.route("/api/exchange/trust/controls", methods=["POST"])
def exchange_trust_controls():
    from backend.services.exchange_trust_service import set_user_controls

    data = request.get_json(silent=True) or {}
    return jsonify(set_user_controls(_uid(from_body=True), **{
        k: data[k] for k in ("global_auto_run", "trust_alerts") if k in data
    }))


@crypto_exchange_bp.route("/api/exchange/trust/agent/activate", methods=["POST"])
def exchange_trust_agent_activate():
    from backend.services.exchange_trust_service import set_agent_activation

    data = request.get_json(silent=True) or {}
    return jsonify(set_agent_activation(
        _uid(from_body=True),
        (data.get("agent_id") or "").strip(),
        (data.get("activation") or "active").strip(),
    ))


@crypto_exchange_bp.route("/api/exchange/live-watch", methods=["GET"])
def exchange_live_watch_user():
    from backend.services.exchange_live_watch_service import user_live_watch

    return jsonify(user_live_watch(_uid(), feed_limit=int(request.args.get("limit") or 50)))


@crypto_exchange_bp.route("/api/exchange/rental/catalog", methods=["GET"])
def exchange_rental_catalog():
    from backend.services.exchange_rental_service import rental_catalog

    return jsonify(rental_catalog())


@crypto_exchange_bp.route("/api/exchange/rental/mine", methods=["GET"])
def exchange_rental_mine():
    from backend.services.exchange_rental_service import list_user_rentals

    return jsonify(list_user_rentals(_uid()))


@crypto_exchange_bp.route("/api/exchange/rental/rent", methods=["POST"])
def exchange_rental_rent():
    from backend.services.exchange_rental_service import rent_agent

    data = request.get_json(silent=True) or {}
    return jsonify(rent_agent(
        _uid(from_body=True),
        (data.get("rental_id") or "").strip(),
        auto_renew=bool(data.get("auto_renew")),
    ))


@crypto_exchange_bp.route("/api/exchange/rental/add-skill", methods=["POST"])
def exchange_rental_add_skill():
    from backend.services.exchange_rental_service import add_skill_addon

    data = request.get_json(silent=True) or {}
    return jsonify(add_skill_addon(
        _uid(from_body=True),
        (data.get("agent_id") or "").strip(),
        (data.get("addon_id") or "").strip(),
    ))


@crypto_exchange_bp.route("/api/exchange/rental/claim-reward", methods=["POST"])
def exchange_rental_claim_reward():
    from backend.services.exchange_rental_service import claim_rental_reward

    data = request.get_json(silent=True) or {}
    return jsonify(claim_rental_reward(_uid(from_body=True), (data.get("agent_id") or "").strip()))


@crypto_exchange_bp.route("/api/exchange/rental/auto-renew", methods=["POST"])
def exchange_rental_auto_renew():
    from backend.services.exchange_rental_service import set_auto_renew

    data = request.get_json(silent=True) or {}
    return jsonify(set_auto_renew(
        _uid(from_body=True),
        (data.get("agent_id") or "").strip(),
        bool(data.get("enabled")),
    ))


@crypto_exchange_bp.route("/api/exchange/rental/convert-to-purchase", methods=["POST"])
def exchange_rental_convert_to_purchase():
    from backend.services.exchange_rental_service import convert_rental_to_purchase

    data = request.get_json(silent=True) or {}
    return jsonify(convert_rental_to_purchase(
        _uid(from_body=True),
        (data.get("agent_id") or "").strip(),
    ))


@crypto_exchange_bp.route("/api/exchange/controller/hub", methods=["GET"])
def exchange_controller_hub():
    from backend.services.exchange_user_controller_service import hub_state

    return jsonify(hub_state(_uid()))


@crypto_exchange_bp.route("/api/exchange/casino-bridge/quests", methods=["GET"])
def exchange_casino_bridge_quests():
    from backend.services.exchange_casino_quest_service import quest_status

    return jsonify(quest_status(_uid()))


@crypto_exchange_bp.route("/api/exchange/casino-bridge/leaderboard", methods=["GET"])
def exchange_casino_bridge_leaderboard():
    from backend.services.exchange_casino_leaderboard_service import weekly_leaderboard

    return jsonify(weekly_leaderboard(
        limit=int(request.args.get("limit") or 15),
        user_id=_uid(),
    ))


@crypto_exchange_bp.route("/api/exchange/controller/catalog", methods=["GET"])
def exchange_controller_catalog():
    from backend.services.exchange_user_controller_service import catalog_for_controller

    return jsonify(catalog_for_controller())


@crypto_exchange_bp.route("/api/exchange/controller/quote", methods=["POST"])
def exchange_controller_quote():
    from backend.services.exchange_user_controller_service import quote_purchase

    data = request.get_json(silent=True) or {}
    return jsonify(quote_purchase(
        _uid(from_body=True),
        (data.get("action") or "").strip(),
        (data.get("target_id") or "").strip(),
    ))


@crypto_exchange_bp.route("/api/exchange/controller/checkout", methods=["POST"])
def exchange_controller_checkout():
    from backend.services.exchange_user_controller_service import checkout

    data = request.get_json(silent=True) or {}
    return jsonify(checkout(
        _uid(from_body=True),
        (data.get("action") or "").strip(),
        (data.get("target_id") or "").strip(),
        payment_method=(data.get("payment_method") or "mn2").strip(),
        agent_id=(data.get("agent_id") or "").strip() or None,
        auto_renew=bool(data.get("auto_renew")),
    ))


@crypto_exchange_bp.route("/api/exchange/controller/cash-out", methods=["POST"])
def exchange_controller_cash_out():
    from backend.services.exchange_user_controller_service import cash_out_profit

    data = request.get_json(silent=True) or {}
    return jsonify(cash_out_profit(
        _uid(from_body=True),
        float(data.get("amount_usd") or 0),
        destination=(data.get("destination") or "mn2").strip(),
    ))


@crypto_exchange_bp.route("/api/exchange/controller/paypal/create", methods=["POST"])
def exchange_controller_paypal_create():
    from backend.services.exchange_user_controller_service import (
        quote_purchase, record_paypal_order,
    )

    data = request.get_json(silent=True) or {}
    user_id = _uid(from_body=True)
    if not user_id or str(user_id).strip().lower() == "default_user":
        return jsonify({"success": False, "error": "Create an account first", "code": "ACCOUNT_REQUIRED"}), 400

    action = (data.get("action") or "").strip()
    target_id = (data.get("target_id") or "").strip()
    q = quote_purchase(user_id, action, target_id)
    if not q.get("success"):
        return jsonify(q), 400

    try:
        from backend.services.crypto_exchange_risk_service import check_fiat_buy

        risk = check_fiat_buy(user_id, float(q.get("price_usd") or 0))
        if not risk.get("ok"):
            ex._audit("risk_denied", user_id=user_id, amount_usd=float(q.get("price_usd") or 0),
                      kind="controller", reason=risk.get("error"))
            return jsonify({"success": False, "error": risk.get("error", "risk_blocked"), "risk": risk}), 429
    except Exception:
        pass

    payload = {
        "action": action,
        "target_id": target_id,
        "agent_id": (data.get("agent_id") or "").strip() or None,
        "auto_renew": bool(data.get("auto_renew")),
        "price_usd": float(q.get("price_usd") or 0),
        "name": q.get("name"),
    }
    try:
        from backend.services.paypal_service import create_order

        base = _base_url()
        return_url = (
            f"{base}/exchange?controller_paypal=success"
            f"&action={urllib.parse.quote(action)}"
            f"&target_id={urllib.parse.quote(target_id)}"
            f"&user_id={urllib.parse.quote(user_id)}"
        )
        cancel_url = f"{base}/exchange?controller_paypal=cancel"
        result = create_order(
            amount=float(q.get("price_usd") or 0),
            currency="USD",
            item_name=q.get("name") or "Exchange agent purchase",
            return_url=return_url,
            cancel_url=cancel_url,
            metadata={"source": "exchange_controller", "user_id": user_id, **payload},
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    if not result.get("success"):
        return jsonify({"success": False, "error": result.get("error", "PayPal order failed")}), 500

    record_paypal_order(result.get("order_id"), user_id, payload, approve_url=result.get("approve_url") or "")
    return jsonify({
        "success": True,
        "order_id": result.get("order_id"),
        "approve_url": result.get("approve_url"),
        "quote": q,
    })


@crypto_exchange_bp.route("/api/exchange/controller/paypal/capture", methods=["POST"])
def exchange_controller_paypal_capture():
    from backend.services.exchange_user_controller_service import fulfill_paypal_order

    data = request.get_json(silent=True) or {}
    order_id = (data.get("order_id") or request.args.get("token") or "").strip()
    user_id = _uid(from_body=True)
    if not order_id:
        return jsonify({"success": False, "error": "order_id required"}), 400
    try:
        from backend.services.paypal_service import capture_order

        capture = capture_order(order_id)
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    result = fulfill_paypal_order(user_id, order_id, capture)
    return jsonify(result), (200 if result.get("success") else 400)


@crypto_exchange_bp.route("/api/exchange/shop/catalog", methods=["GET"])
def exchange_shop_catalog_route():
    from backend.services.exchange_shop_service import shop_catalog

    return jsonify(shop_catalog())


@crypto_exchange_bp.route("/api/exchange/shop/state", methods=["GET"])
def exchange_shop_state():
    from backend.services.exchange_shop_service import user_shop_state

    return jsonify(user_shop_state(_uid()))


@crypto_exchange_bp.route("/api/exchange/shop/purchase", methods=["POST"])
def exchange_shop_purchase():
    from backend.services.exchange_shop_service import purchase_item

    data = request.get_json(silent=True) or {}
    return jsonify(purchase_item(
        _uid(from_body=True),
        (data.get("item_id") or "").strip(),
        agent_id=(data.get("agent_id") or "").strip() or None,
    ))


@crypto_exchange_bp.route("/api/exchange/live-watch/owner", methods=["GET"])
def exchange_live_watch_owner():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_live_watch_service import owner_live_watch

    return jsonify(owner_live_watch(feed_limit=int(request.args.get("limit") or 80)))


@crypto_exchange_bp.route("/api/exchange/trust/policy", methods=["GET", "POST"])
def exchange_trust_policy():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_trust_service import owner_set_policy, _policy

    if request.method == "GET":
        return jsonify({"success": True, "policy": _policy()})
    data = request.get_json(silent=True) or {}
    return jsonify(owner_set_policy(**data))


@crypto_exchange_bp.route("/api/exchange/leveling/me", methods=["GET"])
def exchange_leveling_me():
    from backend.services.exchange_leveling_service import user_progress

    return jsonify(user_progress(_uid()))


@crypto_exchange_bp.route("/api/exchange/leveling/claim", methods=["POST"])
def exchange_leveling_claim():
    from backend.services.exchange_leveling_service import claim_level_reward

    data = request.get_json(silent=True) or {}
    return jsonify(claim_level_reward(_uid(from_body=True), int(data.get("level") or 0)))


@crypto_exchange_bp.route("/api/exchange/leveling/daily", methods=["POST"])
def exchange_leveling_daily():
    from backend.services.exchange_leveling_service import record_daily_login

    return jsonify(record_daily_login(_uid(from_body=True)))


@crypto_exchange_bp.route("/api/exchange/payout/status", methods=["GET"])
def exchange_payout_status():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_payout_service import payout_status

    return jsonify(payout_status())


@crypto_exchange_bp.route("/api/exchange/payout/binance-preflight", methods=["GET"])
def exchange_payout_binance_preflight():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_payout_service import binance_preflight_status

    amt = request.args.get("amount_usdt")
    return jsonify(binance_preflight_status(
        float(amt) if amt is not None and str(amt).strip() != "" else None,
    ))


@crypto_exchange_bp.route("/api/exchange/payout/configure-binance", methods=["POST"])
def exchange_payout_configure_binance():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_payout_service import configure_binance

    data = request.get_json(silent=True) or {}
    max_day = data.get("max_withdraw_per_day")
    w_enabled = data.get("withdraw_enabled")
    return jsonify(configure_binance(
        (data.get("api_key") or "").strip(),
        (data.get("api_secret") or "").strip(),
        deposit_addresses=data.get("deposit_addresses") or {},
        account_label=(data.get("account_label") or "primary").strip(),
        withdraw_address=(data.get("withdraw_address") or data.get("address") or "").strip(),
        network=(data.get("network") or data.get("withdraw_network") or "").strip(),
        withdraw_enabled=bool(w_enabled) if w_enabled is not None else None,
        max_withdraw_per_day=float(max_day) if max_day is not None else None,
    ))


@crypto_exchange_bp.route("/api/exchange/payout/withdraw-binance", methods=["POST"])
def exchange_payout_withdraw_binance():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_payout_service import withdraw_binance

    data = request.get_json(silent=True) or {}
    amt = data.get("amount_usdt")
    mn = data.get("min_amount")
    return jsonify(withdraw_binance(
        float(amt) if amt is not None else None,
        min_amount=float(mn) if mn is not None else None,
    ))


@crypto_exchange_bp.route("/api/exchange/payout/configure-paypal", methods=["POST"])
def exchange_payout_configure_paypal():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_payout_service import configure_paypal

    data = request.get_json(silent=True) or {}
    share = data.get("share_pct")
    return jsonify(configure_paypal(
        (data.get("email") or "").strip(),
        share_pct=float(share) if share is not None else None,
    ))


@crypto_exchange_bp.route("/api/exchange/payout/plan", methods=["POST"])
def exchange_payout_plan():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_payout_service import plan_sweep

    data = request.get_json(silent=True) or {}
    mn = data.get("min_sweep_usd")
    return jsonify(plan_sweep(float(mn) if mn is not None else None))


@crypto_exchange_bp.route("/api/exchange/payout/sweep", methods=["POST"])
def exchange_payout_sweep():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_payout_service import execute_sweep

    data = request.get_json(silent=True) or {}
    mn = data.get("min_sweep_usd")
    return jsonify(execute_sweep(float(mn) if mn is not None else None))


@crypto_exchange_bp.route("/api/exchange/payout/history", methods=["GET"])
def exchange_payout_history():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.exchange_payout_service import sweep_history

    return jsonify(sweep_history(limit=int(request.args.get("limit") or 20)))


@crypto_exchange_bp.route("/api/exchange/paypal/crypto-quote", methods=["POST"])
def exchange_paypal_crypto_quote():
    data = request.get_json(silent=True) or {}
    return jsonify(ex.quote_paypal_crypto(
        data.get("symbol"),
        float(data.get("usd_amount") or 0),
        user_id=_uid(from_body=True),
    ))


@crypto_exchange_bp.route("/api/exchange/paypal/create-crypto-order", methods=["POST"])
def exchange_paypal_create_crypto_order():
    data = request.get_json(silent=True) or {}
    user_id = _uid(from_body=True)
    if not user_id or str(user_id).strip().lower() == "default_user":
        return jsonify({
            "success": False,
            "error": "Create an account first",
            "code": "ACCOUNT_REQUIRED",
        }), 400

    quote = ex.quote_paypal_crypto(
        data.get("symbol"),
        float(data.get("usd_amount") or 0),
        user_id=user_id,
    )
    if not quote.get("success"):
        return jsonify(quote), 400

    try:
        from backend.services.paypal_service import create_order

        base = _base_url()
        symbol = quote.get("symbol")
        return_url = (
            f"{base}/exchange?crypto_paypal=success"
            f"&symbol={urllib.parse.quote(symbol)}"
            f"&user_id={urllib.parse.quote(user_id)}"
        )
        cancel_url = f"{base}/exchange?crypto_paypal=cancel"
        result = create_order(
            amount=float(quote.get("usd_amount") or 0),
            currency="USD",
            item_name=f"Buy {symbol} on MasterNoder Exchange",
            return_url=return_url,
            cancel_url=cancel_url,
            metadata={"item_id": f"crypto:{symbol}", "user_id": user_id, "source": "exchange_crypto"},
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    if not result.get("success"):
        return jsonify({"success": False, "error": result.get("error", "PayPal order failed")}), 500
    ex.record_paypal_crypto_order(
        result.get("order_id"),
        quote,
        approve_url=result.get("approve_url") or "",
    )
    return jsonify({
        "success": True,
        "order_id": result.get("order_id"),
        "approve_url": result.get("approve_url"),
        "quote": quote,
    })


@crypto_exchange_bp.route("/api/exchange/paypal/capture-crypto-order", methods=["POST"])
def exchange_paypal_capture_crypto_order():
    data = request.get_json(silent=True) or {}
    order_id = (data.get("order_id") or request.args.get("token") or "").strip()
    user_id = _uid(from_body=True)
    if not order_id:
        return jsonify({"success": False, "error": "order_id required"}), 400
    try:
        from backend.services.paypal_service import capture_order

        capture = capture_order(order_id)
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    result = ex.fulfill_paypal_crypto_order(user_id, order_id, capture)
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@crypto_exchange_bp.route("/api/exchange/agents", methods=["GET"])
def exchange_agents():
    from backend.services.crypto_exchange_agent_service import list_agents

    return jsonify(list_agents())


@crypto_exchange_bp.route("/api/exchange/agents/tick", methods=["POST"])
def exchange_agents_tick():
    secret = (os.environ.get("EXCHANGE_AGENT_SECRET") or "").strip()
    if not secret:
        return jsonify({"success": False, "error": "EXCHANGE_AGENT_SECRET not configured"}), 403
    got = (request.headers.get("X-Exchange-Agent-Secret") or request.args.get("token") or "").strip()
    if got != secret:
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.crypto_exchange_agent_service import tick

    data = request.get_json(silent=True) or {}
    return jsonify(tick(force=bool(data.get("force"))))


@crypto_exchange_bp.route("/api/exchange/paypal/mn2-packs", methods=["GET"])
def exchange_paypal_mn2_packs():
    from backend.routes.shop_routes import get_mn2_packs

    packs = []
    for pack in get_mn2_packs():
        rails = [str(r).lower() for r in (pack.get("payment_rails") or pack.get("rails") or [])]
        if rails and "paypal" not in rails:
            continue
        if float(pack.get("price_usd") or 0) <= 0 or float(pack.get("mn2_granted") or 0) <= 0:
            continue
        packs.append({
            "id": pack.get("id"),
            "name": pack.get("name") or pack.get("label") or pack.get("id"),
            "price_usd": float(pack.get("price_usd") or 0),
            "mn2_granted": float(pack.get("mn2_granted") or 0),
            "description": pack.get("description") or "Buy MN2 with PayPal and receive it in your platform wallet.",
        })
    return jsonify({
        "success": True,
        "enabled": True,
        "currency": "USD",
        "packs": packs,
        "settlement_note": "PayPal settles to the configured PayPal business account; MN2 is credited after capture.",
    })


@crypto_exchange_bp.route("/api/exchange/paypal/create-mn2-order", methods=["POST"])
def exchange_paypal_create_mn2_order():
    data = request.get_json(silent=True) or {}
    user_id = _uid(from_body=True)
    if not user_id or str(user_id).strip().lower() == "default_user":
        return jsonify({
            "success": False,
            "error": "Create an account first",
            "code": "ACCOUNT_REQUIRED",
        }), 400

    pack = _mn2_paypal_pack(data.get("pack_id"))
    if not pack:
        return jsonify({"success": False, "error": "Unknown PayPal MN2 pack"}), 404

    try:
        from backend.services.crypto_exchange_risk_service import check_fiat_buy

        risk = check_fiat_buy(user_id, float(pack.get("price_usd") or 0))
        if not risk.get("ok"):
            ex._audit("risk_denied", user_id=user_id, amount_usd=float(pack.get("price_usd") or 0), kind="mn2_pack", reason=risk.get("error"))
            return jsonify({"success": False, "error": risk.get("error", "risk_blocked"), "risk": risk}), 429
    except Exception:
        pass

    try:
        from backend.services.paypal_service import create_order

        base = _base_url()
        item_id = pack.get("id")
        return_url = (
            f"{base}/exchange?exchange_paypal=success"
            f"&pack_id={urllib.parse.quote(item_id)}"
            f"&user_id={urllib.parse.quote(user_id)}"
        )
        cancel_url = f"{base}/exchange?exchange_paypal=cancel"
        result = create_order(
            amount=float(pack.get("price_usd") or 0),
            currency="USD",
            item_name=pack.get("name") or "MN2 exchange pack",
            return_url=return_url,
            cancel_url=cancel_url,
            metadata={"item_id": item_id, "user_id": user_id, "source": "exchange"},
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    if not result.get("success"):
        return jsonify({"success": False, "error": result.get("error", "PayPal order failed")}), 500
    ex.record_paypal_mn2_order(
        result.get("order_id"),
        user_id,
        pack,
        approve_url=result.get("approve_url") or "",
    )
    return jsonify({
        "success": True,
        "order_id": result.get("order_id"),
        "approve_url": result.get("approve_url"),
        "pack": {
            "id": pack.get("id"),
            "name": pack.get("name"),
            "price_usd": float(pack.get("price_usd") or 0),
            "mn2_granted": float(pack.get("mn2_granted") or 0),
        },
    })


@crypto_exchange_bp.route("/api/exchange/paypal/capture-mn2-order", methods=["POST"])
def exchange_paypal_capture_mn2_order():
    data = request.get_json(silent=True) or {}
    order_id = (data.get("order_id") or request.args.get("token") or "").strip()
    user_id = _uid(from_body=True)
    if not order_id:
        return jsonify({"success": False, "error": "order_id required"}), 400

    try:
        from backend.services.paypal_service import capture_order

        capture = capture_order(order_id)
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    result = ex.fulfill_paypal_mn2_order(user_id, order_id, capture)
    code = 200 if result.get("success") else 400
    return jsonify(result), code
