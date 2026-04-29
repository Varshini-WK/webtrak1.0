# Backend API Test Inventory

Insert the admin role
BEGIN;

-- 1) Ensure admin role exists
INSERT INTO roles (name)
VALUES ('ROLE_ADMIN')
ON CONFLICT (name) DO NOTHING;

-- 2) Ensure a system project exists (user_roles needs project_id)
INSERT INTO projects (project_code, project_name, project_type, is_active, created_at)
VALUES ('BENCH', 'Bench', 'IN_HOUSE', true, NOW())
ON CONFLICT (project_code) DO NOTHING;

-- 3) Create admin user (edit email/name as needed)
INSERT INTO users (
    emp_id, email, name, status, user_type, department, phone_number, role, work_mode, doj, doi, internship_duration, band_id, created_at
)
VALUES (
    'WK001',
    'varshini.k@webknot.in',
    'System Admin',
    'ACTIVE',
    'FULLTIME',
    'Administration',
    NULL,
    'ROLE_ADMIN',
    'WFO',
    NULL,
    NULL,
    NULL,
    NULL,
    NOW()
)
ON CONFLICT (email) DO NOTHING;

-- 4) Map user -> ROLE_ADMIN on BENCH project
INSERT INTO user_roles (user_id, role_id, project_id)
SELECT u.id, r.id, p.id
FROM users u
JOIN roles r ON r.name = 'ROLE_ADMIN'
JOIN projects p ON p.project_code = 'BENCH'
WHERE u.email = 'varshini.k@webknot.in'
ON CONFLICT (user_id, role_id, project_id) DO NOTHING;

COMMIT;



- Total APIs (method + path): **84**
- Base path: `http://<host>:<port>/api/v1` (except `/health`)
- `*` in body fields means required field
- Role source: `require_any_role(...)` in route handlers

| # | Method | Path | Role Access | Headers | Body |
|---:|---|---|---|---|---|
| 1 | GET | `/api/v1/allocation` | ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 2 | POST | `/api/v1/allocation` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => AllocationCreateRequest {employee_email*:string, project_code*:string, role:any, allocated_hours*:integer, start_date*:string, end_date:any, allocation_type:AllocationType, locked_in_date:any, is_manager:boolean} |
| 3 | GET | `/api/v1/allocation-extension-request` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 4 | POST | `/api/v1/allocation-extension-request` | ROLE_ADMIN, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => CreateAllocationExtensionRequest {user_email*:string, project_code*:string, requested_end_date*:string, reason:any} |
| 5 | PUT | `/api/v1/allocation-extension-request/status` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => UpdateAllocationExtensionStatusRequest {request_id*:integer, status*:string} |
| 6 | POST | `/api/v1/allocation/batch` | ROLE_ADMIN | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | multipart/form-data => Body_batch_import_allocations_api_v1_allocation_batch_post {file*:string} |
| 7 | GET | `/api/v1/allocation/forecasting` | ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 8 | GET | `/api/v1/allocation/roles` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 9 | POST | `/api/v1/allocation/update` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => inline |
| 10 | GET | `/api/v1/allocation/user` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 11 | DELETE | `/api/v1/allocation/{allocation_id}` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 12 | PUT | `/api/v1/allocation/{allocation_id}` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => AllocationUpdateRequest {employee_email*:string, project_code*:string, role:any, allocated_hours*:integer, start_date:any, end_date:any, allocation_type:any, locked_in_date:any, is_manager:boolean} |
| 13 | POST | `/api/v1/assign-role` | Public/No explicit role check | x-admin-bootstrap-key | application/json => AssignRoleRequestJava {userEmail*:string, roleName*:string} |
| 14 | GET | `/api/v1/auth/google/callback` | Public/No explicit role check | None | None |
| 15 | POST | `/api/v1/auth/logout` | Public/No explicit role check | None | None |
| 16 | POST | `/api/v1/auth/refresh` | Public/No explicit role check | None | None |
| 17 | GET | `/api/v1/employee-profile/{empId}` | ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 18 | PUT | `/api/v1/employee-profile/{empId}` | ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => EmployeeProfileHrUpdate {name:any, department:any, user_status:any, work_mode:any, band_id:any, primary_skills:any, secondary_skills:any, experience:any, yoe:any} |
| 19 | GET | `/api/v1/export/timelogs` | ROLE_ADMIN, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 20 | GET | `/api/v1/export/timelogs/{projectCode}/{empEmail}/{startDate}/{endDate}` | ROLE_ADMIN, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 21 | GET | `/api/v1/export/timelogs/{projectCode}/{startDate}/{endDate}` | ROLE_ADMIN, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 22 | GET | `/api/v1/export/timelogs/{startDate}/{endDate}` | ROLE_ADMIN, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 23 | GET | `/api/v1/google-signin` | Public/No explicit role check | None | None |
| 24 | GET | `/api/v1/leave-summary` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 25 | GET | `/api/v1/manager-projects` | ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 26 | GET | `/api/v1/manager-projects-with-roles` | ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 27 | GET | `/api/v1/manager/allocation-extension-status` | ROLE_ADMIN, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 28 | GET | `/api/v1/masters/bands` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 29 | GET | `/api/v1/masters/designations` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 30 | GET | `/api/v1/masters/kpi-definitions` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 31 | POST | `/api/v1/masters/kpi-definitions` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => KpiDefinitionCreate {band_id*:integer, department*:Department, kpi_name*:string, weightage*:any, active:boolean} |
| 32 | DELETE | `/api/v1/masters/kpi-definitions/{kpi_id}` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 33 | GET | `/api/v1/masters/kpi-definitions/{kpi_id}` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 34 | PUT | `/api/v1/masters/kpi-definitions/{kpi_id}` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => KpiDefinitionUpdate {band_id:any, department:any, kpi_name:any, weightage:any, active:any} |
| 35 | GET | `/api/v1/masters/submission-cycles` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 36 | POST | `/api/v1/masters/submission-cycles` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => SubmissionCycleCreate {cycle_key*:string, scope:any, window_start_at*:string, window_end_at:any, manual_closed:boolean, updated_by:any} |
| 37 | GET | `/api/v1/masters/submission-cycles/by-key` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 38 | DELETE | `/api/v1/masters/submission-cycles/{cycle_id}` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 39 | GET | `/api/v1/masters/submission-cycles/{cycle_id}` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 40 | PUT | `/api/v1/masters/submission-cycles/{cycle_id}` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => SubmissionCycleUpdate {cycle_key:any, scope:any, window_start_at:any, window_end_at:any, manual_closed:any, updated_by:any} |
| 41 | GET | `/api/v1/masters/webknot-values` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 42 | POST | `/api/v1/masters/webknot-values` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => WebknotValueCreate {title*:string, evaluation_criteria:any, active:boolean} |
| 43 | DELETE | `/api/v1/masters/webknot-values/{row_id}` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 44 | PUT | `/api/v1/masters/webknot-values/{row_id}` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => WebknotValueUpdate {title:any, evaluation_criteria:any, active:any} |
| 45 | GET | `/api/v1/notifications` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_FINANCE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 46 | POST | `/api/v1/notifications/announcement` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => AnnouncementCreateRequest {title*:string, message*:string} |
| 47 | GET | `/api/v1/notifications/delete` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 48 | PUT | `/api/v1/notifications/read-all` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_FINANCE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 49 | GET | `/api/v1/notifications/subscribe` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_FINANCE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 50 | PUT | `/api/v1/notifications/{notification_id}/read` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_FINANCE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 51 | GET | `/api/v1/oauth/bypass/{email}` | Public/No explicit role check | None | None |
| 52 | GET | `/api/v1/profile` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 53 | PUT | `/api/v1/profile` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | multipart/form-data => Body_update_profile_api_v1_profile_put {body*:string, profilePic:any} |
| 54 | GET | `/api/v1/project` | ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 55 | POST | `/api/v1/project` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => CreateProjectRequest {project_code*:string, project_name*:string, project_type*:ProjectTypeEnum} |
| 56 | GET | `/api/v1/project-assigned-to-user` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 57 | GET | `/api/v1/projects` | ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 58 | POST | `/api/v1/projects` | ROLE_ADMIN | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => array[CreateProjectRequest {project_code*:string, project_name*:string, project_type*:ProjectTypeEnum}] |
| 59 | GET | `/api/v1/projects/all` | ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 60 | POST | `/api/v1/roles/assign` | Public/No explicit role check | x-admin-bootstrap-key | application/json => AssignRoleRequest {target_email*:string, role*:string} |
| 61 | POST | `/api/v1/scheduler/run-all` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 62 | GET | `/api/v1/timelog` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 63 | POST | `/api/v1/timelog` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => TimeLogCreateRequest {project_code*:string, log_date*:string, hours*:integer, description:any} |
| 64 | PUT | `/api/v1/timelog/entry` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => UpdateTimeLogEntryRequestJava {timeLogId*:integer, description:any, loggedHours*:integer} |
| 65 | GET | `/api/v1/timelog/get/{empEmail}/{logDate}` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 66 | PUT | `/api/v1/timelog/status` | ROLE_ADMIN, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => TimeLogStatusUpdateRequest {timelog_id*:integer, status*:string, manager_comment:any} |
| 67 | PUT | `/api/v1/timelog/status/batch` | ROLE_ADMIN, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => TimeLogStatusBatchRequest {employee_email*:string, project_code*:string, log_date*:string, status*:string, manager_comment:any} |
| 68 | DELETE | `/api/v1/timelog/{timelog_id}` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 69 | PUT | `/api/v1/timelog/{timelog_id}` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => TimeLogUpdateRequest {project_code*:string, log_date*:string, hours*:integer, description:any} |
| 70 | POST | `/api/v1/upload` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | multipart/form-data => Body_upload_leave_excel_api_v1_upload_post {file*:string} |
| 71 | POST | `/api/v1/upload-allocation` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | multipart/form-data => Body_upload_allocation_excel_api_v1_upload_allocation_post {file*:string} |
| 72 | POST | `/api/v1/upload/user-data` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | multipart/form-data => Excel `file` with header columns (preferred): `emp_id,email,name,status,user_type,department,phone_number,role,work_mode,doj,doi,internship_duration,band_id` (legacy positional fallback still supported) |
| 73 | GET | `/api/v1/user` | Public/No explicit role check | None | None |
| 74 | POST | `/api/v1/user/batch` | ROLE_ADMIN | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | multipart/form-data => Excel `file` with header columns (preferred): `emp_id,email,name,status,user_type,department,phone_number,role,work_mode,doj,doi,internship_duration,band_id` (legacy `emp_id,name,email` positional fallback still supported) |
| 75 | GET | `/api/v1/user/onboard` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 76 | POST | `/api/v1/user/onboard` | ROLE_ADMIN, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => UserOnboardCreate {email*:string, name*:string, user_type:string, department:any, phone_number:any, work_mode:any, role:any, band_id:any, doj:any, doi:any, internship_duration:any} |
| 77 | PUT | `/api/v1/user/onboard` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | multipart/form-data => Body_update_user_onboard_api_v1_user_onboard_put {user_data*:string, resume:any, reliving_letter:any, salary_slips:array, profile_photo:any, aadhaar:any, pan_card:any} |
| 78 | DELETE | `/api/v1/userRequest` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => UserRequestDelete {user_request_id*:integer} |
| 79 | POST | `/api/v1/userRequest` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => UserRequestCreate {request_from_date*:string, request_to_date*:string, request_type*:string, comments:any, is_half_day:boolean, reference_file_url:any, manager_comp_off_email:any} |
| 80 | PUT | `/api/v1/userRequest` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => UserRequestUpdate {request_from_date*:string, request_to_date*:string, request_type*:string, comments:any, is_half_day:boolean, reference_file_url:any, manager_comp_off_email:any, user_request_id*:integer} |
| 81 | GET | `/api/v1/userRequest/get/{empEmails}/{fromDate}/{toDate}/{requestType}` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 82 | GET | `/api/v1/userRequest/get/{fromDate}/{toDate}/{requestType}` | ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | None |
| 83 | PUT | `/api/v1/userRequest/status` | ROLE_ADMIN, ROLE_HR, ROLE_MANAGER | Authorization: Bearer <accessToken> OR auth cookies(email, roles) | application/json => UserRequestStatusUpdate {user_request_id*:integer, user_request_status*:string, message:any} |
| 84 | GET | `/health` | Public/No explicit role check | None | None |

## Notes for Fresh DB Testing
- Run migrations + seed before protected endpoint testing, because many routes need users + roles present.
- Public endpoints for initial auth/bootstrap: `/health`, `/api/v1/google-signin`, `/api/v1/auth/google/callback`, `/api/v1/oauth/bypass/{email}` (non-prod), role assign endpoints with bootstrap header.
- Role assignment endpoints (`/api/v1/roles/assign`, `/api/v1/assign-role`) rely on service-level checks and optional `x-admin-bootstrap-key`.
- User import endpoints now accept header-driven full `users` table columns: `emp_id,email,name,status,user_type,department,phone_number,role,work_mode,doj,doi,internship_duration,band_id`.
- `/api/v1/user/batch` creates/updates users; for newly created users it auto-assigns `ROLE_EMPLOYEE` on `GLOBAL`.
- `/api/v1/upload/user-data` updates only existing users (rows with unknown email are skipped).
