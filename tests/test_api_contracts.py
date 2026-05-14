from app.main import app


def test_expected_employee_routes_present() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/user/onboard" in paths
    assert "/api/v1/user/recent-invited" in paths
    assert "/api/v1/user/offboard/{emp_id}" in paths
    assert "/api/v1/profile" in paths
    assert "/api/v1/employee-profile/{empId}" in paths


def test_expected_allocation_routes_present() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/allocation" in paths
    assert "/api/v1/allocation/user" in paths
    assert "/api/v1/allocation/bench-users" in paths
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
    assert "/api/v1/employee-attendance-leave" in paths
    assert "/api/v1/reports/workforce/headcount-distribution" in paths
    assert "/api/v1/reports/workforce/role-wise-billed" in paths
    assert "/api/v1/reports/workforce/experience" in paths
    assert "/api/v1/reports/utilization/utilization-by-department" in paths
    assert "/api/v1/reports/utilization/bench-aging" in paths
    assert "/api/v1/reports/skill-capacity/skill-inventory" in paths
    assert "/api/v1/reports/compliance/contract-distribution" in paths
    assert "/api/v1/reports/attrition/overall-percent" in paths
    assert "/api/v1/reports/attrition/voluntary-involuntary" in paths
    assert "/api/v1/reports/attrition/role-wise" in paths
    assert "/api/v1/reports/attrition/manager-wise" in paths
    assert "/api/v1/reports/attrition/critical-skill" in paths
    assert "/api/v1/reports/attrition/regretted" in paths
    assert "/api/v1/reports/attrition/average-tenure" in paths


def test_expected_notification_routes_present() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/notifications" in paths
    assert "/api/v1/notifications/{notification_id}/read" in paths
    assert "/api/v1/notifications/read-all" in paths
    assert "/api/v1/notifications/announcement" in paths
    assert "/api/v1/notifications/subscribe" in paths
    assert "/api/v1/notifications/delete" in paths


def test_expected_learning_routes_present() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/trainings" in paths
    assert "/api/v1/trainings/{training_id}" in paths
    assert "/api/v1/trainings/{training_id}/trainers" in paths
    assert "/api/v1/trainings/{training_id}/trainers/{trainer_user_id}" in paths
    assert "/api/v1/trainings/{training_id}/sessions" in paths
    assert "/api/v1/trainings/{training_id}/participants" in paths
    assert "/api/v1/trainings/{training_id}/participants/{user_id}" in paths
    assert "/api/v1/trainings/{training_id}/enroll" in paths
    assert "/api/v1/trainings/open" in paths
    assert "/api/v1/trainings/{training_id}/materials" in paths
    assert "/api/v1/trainings/{training_id}/sessions/{training_session_id}/attendance" in paths
    assert "/api/v1/trainings/{training_id}/assessments" in paths
    assert "/api/v1/trainings/{training_id}/scores" in paths
    assert "/api/v1/trainings/{training_id}/analytics" in paths


def test_expected_policy_routes_present() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/reports/policies" in paths
    assert "/api/v1/reports/policies/{policy_id}/publish" in paths
    assert "/api/v1/reports/policies/{policy_id}/compliance" in paths
    assert "/api/v1/reports/policies/my" in paths
    assert "/api/v1/reports/policies/{policy_id}/viewed" in paths
    assert "/api/v1/reports/policies/{policy_id}/signed-copy" in paths
    assert "/api/v1/reports/policies/{policy_id}/signed-documents" in paths
    assert "/api/v1/reports/policies/{policy_id}/signed-documents/export" in paths


def test_expected_bgv_routes_present() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/reports/bgv" in paths
    assert "/api/v1/reports/bgv/{emp_id}" in paths
