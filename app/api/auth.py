from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi import HTTPException, status
from fastapi.responses import RedirectResponse

from app.core.database import get_db
from app.core.settings import get_settings
from app.schemas.common import GenericResponse
from app.schemas.auth import AuthResponse
from app.tools.auth_tool import AuthTool

router = APIRouter()


@router.get("/google-signin")
async def google_signin(response: Response, db=Depends(get_db)) -> RedirectResponse:
    state = str(uuid4())
    tool = AuthTool(db)
    redirect_url = await tool.build_google_signin_url(state=state)
    redirect = RedirectResponse(url=redirect_url, status_code=302)
    tool.set_oauth_state_cookie(redirect, state)
    return redirect


@router.get("/auth/google/callback")
async def google_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db=Depends(get_db),
) -> RedirectResponse:
    settings = get_settings()
    tool = AuthTool(db)
    frontend_redirect_uri = settings.frontend_redirect_uri

    if error:
        return RedirectResponse(url=f"{frontend_redirect_uri}?error=oauth_failed", status_code=302)

    expected_state = request.cookies.get("oauthState")
    if not state or not expected_state or state != expected_state:
        return RedirectResponse(url=f"{frontend_redirect_uri}?error=invalid_oauth_state", status_code=302)

    if not code:
        return RedirectResponse(url=f"{frontend_redirect_uri}?error=missing_oauth_code", status_code=302)

    try:
        redirect = RedirectResponse(url=frontend_redirect_uri, status_code=302)
        await tool.login_with_google_code(response=redirect, code=code)
        tool.clear_oauth_state_cookie(redirect)
        return redirect
    except HTTPException as exc:
        if exc.detail == "unregistered_user":
            return RedirectResponse(url=f"{frontend_redirect_uri}?error=unregistered_user", status_code=302)
        return RedirectResponse(url=f"{frontend_redirect_uri}?error=oauth_login_failed", status_code=302)


@router.post("/auth/refresh", response_model=GenericResponse)
async def refresh_session(request: Request, response: Response, db=Depends(get_db)) -> GenericResponse:
    token_id = request.cookies.get("tokenId", "")
    refresh_token = request.cookies.get("refreshToken", "")
    tool = AuthTool(db)
    result = await tool.refresh(response=response, token_id=token_id, refresh_token=refresh_token)
    return GenericResponse(message="success", data=result.model_dump())


@router.post("/auth/logout", response_model=GenericResponse)
async def logout(request: Request, response: Response, db=Depends(get_db)) -> GenericResponse:
    token_id = request.cookies.get("tokenId")
    tool = AuthTool(db)
    await tool.logout(response=response, token_id=token_id)
    return GenericResponse(message="LoggedOut Successfully", data=None)


@router.get("/oauth/bypass/{email}", response_model=GenericResponse)
async def oauth_bypass(email: str, response: Response, db=Depends(get_db)) -> GenericResponse:
    settings = get_settings()
    if settings.app_env.lower() == "prod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bypass is blocked in production.")
    name = email.split("@")[0].replace(".", " ").title()
    tool = AuthTool(db)
    result = await tool.login(response=response, email=email, name=name)
    return GenericResponse(message="success", data=result.model_dump())
