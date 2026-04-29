from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.refresh_token import RefreshToken

def _as_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(UTC).replace(tzinfo=None)

class RefreshTokenRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def create(self, user_id: int, token_id: str, token: str, expires_at: datetime, client=None):
        expires_at = _as_naive_utc(expires_at)
        if client is not None:
            row = RefreshToken(user_id=user_id, token_id=token_id, token=token, expires_at=expires_at, revoked=False)
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            row = RefreshToken(user_id=user_id, token_id=token_id, token=token, expires_at=expires_at, revoked=False)
            session.add(row)
            await session.flush()
            return row

    async def get_valid(self, token_id: str, token: str):
        async with self.db.session() as session:
            record = await session.scalar(
                select(RefreshToken)
                .where(RefreshToken.token_id == token_id, RefreshToken.token == token, RefreshToken.revoked.is_(False))
                .options(selectinload(RefreshToken.user))
            )
        if not record:
            return None
        now_aware = datetime.now(UTC)
        now_naive_utc = now_aware.replace(tzinfo=None)
        if record.expires_at < now_naive_utc:
            return None
        return record

    async def revoke_by_token_id(self, token_id: str, client=None) -> None:
        session = client
        if session is None:
            async with self.db.tx() as session:
                record = await session.scalar(select(RefreshToken).where(RefreshToken.token_id == token_id))
                if record:
                    record.revoked = True
                    await session.flush()
                return
        record = await session.scalar(select(RefreshToken).where(RefreshToken.token_id == token_id))
        if record:
            record.revoked = True
            await session.flush()
