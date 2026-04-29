from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.security import create_access_token, create_refresh_token
from app.core.settings import get_settings
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthResponse


class AuthService:
    def __init__(self, db) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.refresh_repo = RefreshTokenRepository(db)
        self.settings = get_settings()

    async def build_google_auth_url(self, state: str) -> str:
        if not self.settings.google_client_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Missing Google client id.")
        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": self.settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "select_account",
            "state": state,
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    def _exchange_code_for_identity(self, code: str) -> tuple[str, str]:
        token_payload = {
            "code": code,
            "client_id": self.settings.google_client_id,
            "client_secret": self.settings.google_client_secret,
            "redirect_uri": self.settings.google_redirect_uri,
            "grant_type": "authorization_code",
        }
        with httpx.Client(timeout=10) as client:
            token_response = client.post("https://oauth2.googleapis.com/token", data=token_payload)
        if token_response.status_code != 200:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google token exchange failed.")

        id_token_jwt = token_response.json().get("id_token")
        if not id_token_jwt:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google id token missing.")

        info = id_token.verify_oauth2_token(
            id_token_jwt,
            google_requests.Request(),
            self.settings.google_client_id,
        )
        email = str(info.get("email", "")).strip().lower()
        name = str(info.get("name", "")).strip() or email.split("@")[0]
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google account email not available.")
        return email, name

    async def oauth_login_from_google_code(self, code: str) -> tuple[AuthResponse, dict[str, str]]:
        email, name = self._exchange_code_for_identity(code)

        user = await self.user_repo.get_by_email(email)
        if not user and not self.settings.oauth_auto_create_user:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="unregistered_user")
        if not user:
            user = await self.user_repo.create_or_get_oauth_user(email=email, name=name)

        roles = await self.user_repo.get_role_names_for_user(user.id)
        access_token = create_access_token(email, roles, user.status, user.userType)
        token_id, refresh_token, expires_at = create_refresh_token()
        await self.refresh_repo.create(user.id, token_id, refresh_token, expires_at)

        response = AuthResponse(
            message="Login successful",
            email=user.email,
            name=user.name,
            roles=roles,
            status=user.status,
            user_type=user.userType,
        )
        return response, {"accessToken": access_token, "refreshToken": refresh_token, "tokenId": token_id}

    async def oauth_login(self, email: str, name: str) -> tuple[AuthResponse, dict[str, str]]:
        user = await self.user_repo.create_or_get_oauth_user(email=email, name=name)
        roles = await self.user_repo.get_role_names_for_user(user.id)

        access_token = create_access_token(email, roles, user.status, user.userType)
        token_id, refresh_token, expires_at = create_refresh_token()
        await self.refresh_repo.create(user.id, token_id, refresh_token, expires_at)

        response = AuthResponse(
            message="Login successful",
            email=user.email,
            name=user.name,
            roles=roles,
            status=user.status,
            user_type=user.userType,
        )
        return response, {"accessToken": access_token, "refreshToken": refresh_token, "tokenId": token_id}

    async def refresh_session(self, token_id: str, refresh_token: str) -> tuple[AuthResponse, dict[str, str]]:
        token_record = await self.refresh_repo.get_valid(token_id, refresh_token)
        if not token_record:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh session.")

        user = token_record.user
        roles = await self.user_repo.get_role_names_for_user(user.id)
        access_token = create_access_token(user.email, roles, user.status, user.userType)
        new_token_id, new_refresh_token, expires_at = create_refresh_token()

        async with self.db.tx() as transaction:
            await self.refresh_repo.revoke_by_token_id(token_id, client=transaction)
            await self.refresh_repo.create(user.id, new_token_id, new_refresh_token, expires_at, client=transaction)

        response = AuthResponse(
            message="Session refreshed",
            email=user.email,
            name=user.name,
            roles=roles,
            status=user.status,
            user_type=user.userType,
        )
        return response, {"accessToken": access_token, "refreshToken": new_refresh_token, "tokenId": new_token_id}

    async def logout(self, token_id: str | None) -> None:
        if token_id:
            await self.refresh_repo.revoke_by_token_id(token_id)
