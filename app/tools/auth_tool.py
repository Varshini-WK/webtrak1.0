from fastapi import Response

from app.core.settings import get_settings
from app.schemas.auth import AuthResponse
from app.services.auth_service import AuthService


class AuthTool:
    def __init__(self, db) -> None:
        self.service = AuthService(db)
        self.settings = get_settings()

    def _set_cookie(self, response: Response, key: str, value: str, max_age: int = 0) -> None:
        response.set_cookie(
            key=key,
            value=value,
            httponly=True,
            secure=self.settings.cookie_secure,
            samesite="lax",
            max_age=max_age if max_age > 0 else None,
            domain=self.settings.cookie_domain,
            path="/",
        )

    async def build_google_signin_url(self, state: str) -> str:
        return await self.service.build_google_auth_url(state)

    def set_oauth_state_cookie(self, response: Response, state: str) -> None:
        self._set_cookie(response, "oauthState", state, max_age=600)

    def clear_oauth_state_cookie(self, response: Response) -> None:
        response.delete_cookie(key="oauthState", path="/", domain=self.settings.cookie_domain)

    async def login_with_google_code(self, response: Response, code: str) -> AuthResponse:
        auth_response, tokens = await self.service.oauth_login_from_google_code(code=code)
        self._set_cookie(response, "accessToken", tokens["accessToken"], max_age=self.settings.access_token_minutes * 60)
        self._set_cookie(response, "refreshToken", tokens["refreshToken"], max_age=self.settings.refresh_token_days * 86400)
        self._set_cookie(response, "tokenId", tokens["tokenId"], max_age=self.settings.refresh_token_days * 86400)
        self._set_cookie(response, "email", auth_response.email, max_age=self.settings.refresh_token_days * 86400)
        self._set_cookie(response, "employeeName", auth_response.name, max_age=self.settings.refresh_token_days * 86400)
        self._set_cookie(response, "roles", ",".join(auth_response.roles), max_age=self.settings.refresh_token_days * 86400)
        self._set_cookie(response, "status", auth_response.status, max_age=self.settings.refresh_token_days * 86400)
        self._set_cookie(response, "type", auth_response.user_type, max_age=self.settings.refresh_token_days * 86400)
        return auth_response

    async def login(self, response: Response, email: str, name: str) -> AuthResponse:
        auth_response, tokens = await self.service.oauth_login(email=email, name=name)
        self._set_cookie(response, "accessToken", tokens["accessToken"], max_age=self.settings.access_token_minutes * 60)
        self._set_cookie(response, "refreshToken", tokens["refreshToken"], max_age=self.settings.refresh_token_days * 86400)
        self._set_cookie(response, "tokenId", tokens["tokenId"], max_age=self.settings.refresh_token_days * 86400)
        self._set_cookie(response, "email", auth_response.email, max_age=self.settings.refresh_token_days * 86400)
        self._set_cookie(response, "employeeName", auth_response.name, max_age=self.settings.refresh_token_days * 86400)
        self._set_cookie(response, "roles", ",".join(auth_response.roles), max_age=self.settings.refresh_token_days * 86400)
        self._set_cookie(response, "status", auth_response.status, max_age=self.settings.refresh_token_days * 86400)
        self._set_cookie(response, "type", auth_response.user_type, max_age=self.settings.refresh_token_days * 86400)
        return auth_response

    async def refresh(self, response: Response, token_id: str, refresh_token: str) -> AuthResponse:
        auth_response, tokens = await self.service.refresh_session(token_id=token_id, refresh_token=refresh_token)
        self._set_cookie(response, "accessToken", tokens["accessToken"], max_age=self.settings.access_token_minutes * 60)
        self._set_cookie(response, "refreshToken", tokens["refreshToken"], max_age=self.settings.refresh_token_days * 86400)
        self._set_cookie(response, "tokenId", tokens["tokenId"], max_age=self.settings.refresh_token_days * 86400)
        self._set_cookie(response, "email", auth_response.email, max_age=self.settings.refresh_token_days * 86400)
        self._set_cookie(response, "employeeName", auth_response.name, max_age=self.settings.refresh_token_days * 86400)
        self._set_cookie(response, "roles", ",".join(auth_response.roles), max_age=self.settings.refresh_token_days * 86400)
        self._set_cookie(response, "status", auth_response.status, max_age=self.settings.refresh_token_days * 86400)
        self._set_cookie(response, "type", auth_response.user_type, max_age=self.settings.refresh_token_days * 86400)
        return auth_response

    async def logout(self, response: Response, token_id: str | None) -> dict[str, str]:
        await self.service.logout(token_id=token_id)
        for key in ["accessToken", "refreshToken", "tokenId", "email", "employeeName", "roles", "status", "type"]:
            response.delete_cookie(key=key, path="/", domain=self.settings.cookie_domain)
        return {"message": "Logged out successfully"}
