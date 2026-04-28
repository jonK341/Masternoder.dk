"""Automatic Register Intelligence - discovers and registers routes/blueprints."""
from backend.services.register_intelligence.route_discovery import (
    discover_blueprints,
    discover_routes_from_blueprints,
    discover_routes_simple,
)
from backend.services.register_intelligence.frontend_api_scanner import (
    scan_frontend_api_calls,
    all_frontend_api_paths,
)
from backend.services.register_intelligence.orchestrator import (
    RegisterIntelligence,
    run_register_intelligence,
)
from backend.services.register_intelligence.missing_route_resolver import (
    MissingRouteResolver,
)

__all__ = [
    "discover_blueprints",
    "discover_routes_from_blueprints",
    "discover_routes_simple",
    "scan_frontend_api_calls",
    "all_frontend_api_paths",
    "RegisterIntelligence",
    "run_register_intelligence",
    "MissingRouteResolver",
]
