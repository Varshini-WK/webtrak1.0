from app.main import app


def test_master_routes_registered() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/masters/bands" in paths
    assert "/api/v1/masters/kpi-definitions" in paths
    assert "/api/v1/masters/kpi-definitions/{kpi_id}" in paths
    assert "/api/v1/masters/webknot-values" in paths
    assert "/api/v1/masters/webknot-values/{row_id}" in paths
    assert "/api/v1/masters/submission-cycles" in paths
    assert "/api/v1/masters/submission-cycles/by-key" in paths
    assert "/api/v1/masters/submission-cycles/{cycle_id}" in paths
    assert "/api/v1/masters/designations" in paths
