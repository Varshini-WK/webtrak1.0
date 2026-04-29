# Reporting Import/Export Contract Notes

This document maps legacy Java contracts to current FastAPI contracts for reporting/import-export paths.

## Timelog Export

- Legacy employee export:
  - `GET /export/timelogs/{projectCode}/{empEmail}/{startDate}/{endDate}`
  - Response: `time_logs.xlsx` (`Logged Date`, `Logged Hours`, `Description`)
- Legacy project summary export:
  - `GET /export/timelogs/{startDate}/{endDate}`
  - `GET /export/timelogs/{projectCode}/{startDate}/{endDate}`
  - Optional query: `empEmail`
  - Response: `project_time_logs.xlsx`

FastAPI now supports:
- `GET /api/v1/export/timelogs` with query params and `format=csv|xlsx`
- Legacy-compatible route variants for all path-based exports above.

## Import Endpoints

- Legacy:
  - `POST /upload` (leave balances from Excel)
  - `POST /upload-allocation` (allocation import from Excel)
  - `POST /upload/user-data` (user master corrections from Excel)
  - `POST /user/batch` (bulk user import from Excel)

FastAPI now supports:
- `POST /api/v1/upload`
- `POST /api/v1/upload-allocation`
- `POST /api/v1/upload/user-data`
- `POST /api/v1/user/batch`

## Leave/LOP Summary

- Legacy:
  - `GET /leave-summary` with filters and pagination, focused on LOP records.

FastAPI now supports:
- `GET /api/v1/leave-summary` with equivalent filters (`page`, `size`, `search`, `type`, `band`, `year`, `month`) and paginated LOP-focused response.

