from flask import Flask


def _app():
    from backend.middleware.auto_fix_404_middleware import register_auto_fix_middleware
    from backend.routes.all_page_routes import all_page_bp

    app = Flask(__name__)
    app.register_blueprint(all_page_bp)
    register_auto_fix_middleware(app)
    return app


def test_user_page_serves_account_html():
    client = _app().test_client()

    response = client.get("/user/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Privacy controls" in html
    assert "Password protection" in html
    assert "Request recovery token" in html
    assert "/api/user/account-privacy" in html


def test_non_api_404_remains_404():
    client = _app().test_client()

    response = client.get("/not-a-real-page")

    assert response.status_code == 404


def test_customers_page_serves_html():
    client = _app().test_client()

    response = client.get("/customers/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Customers" in html
    assert "navigation-toolbar.js" in html


def test_agents_control_page_serves_html():
    client = _app().test_client()

    response = client.get("/dashboard/agents_control/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Agents Control Board" in html
    assert "navigation-toolbar.js" in html
