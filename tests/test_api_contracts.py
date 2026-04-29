from app.main import app


def test_expected_employee_routes_present() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/user/onboard" in paths
    assert "/api/v1/profile" in paths
    assert "/api/v1/employee-profile/{empId}" in paths


def test_expected_allocation_routes_present() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/allocation" in paths
    assert "/api/v1/allocation/user" in paths
    assert "/api/v1/allocation/forecasting" in paths
    assert "/api/v1/allocation/{allocation_id}" in paths
    assert "/api/v1/allocation/batch" in paths


def test_expected_timelog_routes_present() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/timelog" in paths
    assert "/api/v1/timelog/{timelog_id}" in paths
    assert "/api/v1/timelog/status" in paths
    assert "/api/v1/timelog/status/batch" in paths
    assert "/api/v1/export/timelogs" in paths
    assert "/api/v1/export/timelogs/{projectCode}/{empEmail}/{startDate}/{endDate}" in paths
    assert "/api/v1/export/timelogs/{startDate}/{endDate}" in paths
    assert "/api/v1/export/timelogs/{projectCode}/{startDate}/{endDate}" in paths


def test_expected_scheduler_route_present() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/scheduler/run-all" in paths


def test_expected_reporting_import_routes_present() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/upload" in paths
    assert "/api/v1/upload-allocation" in paths
    assert "/api/v1/upload/user-data" in paths
    assert "/api/v1/user/batch" in paths
    assert "/api/v1/leave-summary" in paths


def test_expected_notification_routes_present() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/notifications" in paths
    assert "/api/v1/notifications/{notification_id}/read" in paths
    assert "/api/v1/notifications/read-all" in paths
    assert "/api/v1/notifications/announcement" in paths
    assert "/api/v1/notifications/subscribe" in paths
    assert "/api/v1/notifications/delete" in paths
