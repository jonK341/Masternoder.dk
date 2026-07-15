from html.parser import HTMLParser

import pytest
from flask import Flask


TAB_IDS = (
    "explorer",
    "staking",
    "leaderboard",
    "teams",
    "reserves",
    "masternodes",
    "market",
)


class _ExplorerMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tabs = {}
        self.panels = {}
        self.elements = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        element_id = attributes.get("id")
        if element_id:
            self.elements[element_id] = attributes

        tab_id = attributes.get("data-mn2-tab")
        classes = set(attributes.get("class", "").split())
        if tag == "button" and "mn2-hub-tab" in classes and tab_id:
            self.tabs[tab_id] = attributes
        if tag == "section" and "mn2-tab-panel" in classes and tab_id:
            self.panels[tab_id] = attributes


def _app():
    from backend.routes.all_page_routes import all_page_bp

    app = Flask(__name__)
    app.register_blueprint(all_page_bp)
    return app


@pytest.mark.parametrize("path", ["/explorer", "/explorer/", "/explorer/index.html"])
def test_explorer_page_routes_serve_the_hub(path):
    response = _app().test_client().get(path)

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert "MN2 Network Explorer" in response.get_data(as_text=True)


def test_explorer_tabs_have_complete_accessible_relationships():
    response = _app().test_client().get("/explorer/")
    parser = _ExplorerMarkup()
    parser.feed(response.get_data(as_text=True))

    assert tuple(parser.tabs) == TAB_IDS
    assert tuple(parser.panels) == TAB_IDS

    for index, tab_id in enumerate(TAB_IDS):
        tab = parser.tabs[tab_id]
        panel = parser.panels[tab_id]

        assert tab["id"] == f"mn2-tab-{tab_id}"
        assert tab["role"] == "tab"
        assert tab["aria-controls"] == f"mn2-panel-{tab_id}"
        assert tab["aria-selected"] == ("true" if index == 0 else "false")
        assert tab["tabindex"] == ("0" if index == 0 else "-1")

        assert panel["id"] == f"mn2-panel-{tab_id}"
        assert panel["role"] == "tabpanel"
        assert panel["aria-labelledby"] == f"mn2-tab-{tab_id}"
        assert ("hidden" not in panel) == (index == 0)

    route_note = parser.elements["mn2-route-note"]
    assert route_note["aria-live"] == "polite"
    assert route_note["aria-atomic"] == "true"
