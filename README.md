# Webtrak-1 Backend

FastAPI backend scaffold for Webtrak migration.

## Implemented (Phase 1 - Auth & Session)
- `GET /api/v1/google-signin`
- `GET /api/v1/auth/google/callback`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/oauth/bypass/{email}` (blocked when `APP_ENV=prod`)

## Architecture
- API: request/response only (`app/api`)
- Tool: execution layer (`app/tools`)
- Service: business rules (`app/services`)
- Repository: DB access (`app/repositories`)
- Database models: (`app/models`)

## Run
1. Create `.env` from `.env.example`.
2. Install dependencies:
   - `python -m pip install -r requirements.txt`
3. Run migrations:
   - `alembic upgrade head`
4. Start app:
   - `python main.py`

## OAuth Notes
- `GET /api/v1/google-signin` redirects to Google OAuth consent.
- Callback endpoint validates state + exchanges authorization code.
- On success, auth cookies are set and browser is redirected to `FRONTEND_REDIRECT_URI`.
- If `OAUTH_AUTO_CREATE_USER=false`, unknown users are redirected with `?error=unregistered_user`.

## SQLAlchemy DB Workflow
- ORM models source: `app/models`
- Migration workflow: Alembic (`alembic revision --autogenerate`, `alembic upgrade head`)
- Runtime uses SQLAlchemy async session lifecycle in `app/core/database.py`.
