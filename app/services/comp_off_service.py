from __future__ import annotations

from datetime import date, timedelta

from fastapi import HTTPException, status

from app.repositories.comp_off_repository import CompOffRepository


class CompOffService:
    VALIDITY_DAYS = 90

    def __init__(self, db) -> None:
        self.repo = CompOffRepository(db)

    async def grant_for_approved_request(
        self,
        *,
        user_id: int,
        user_request_id: int,
        approved_by_id: int,
        request_date: date,
        is_half_day: bool,
        client,
    ) -> None:
        units = 0.5 if is_half_day else 1.0
        await self.repo.create_grant(
            {
                "user_id": user_id,
                "source_request_id": user_request_id,
                "grant_date": request_date,
                "expiry_date": request_date + timedelta(days=self.VALIDITY_DAYS),
                "units": units,
                "remaining_units": units,
                "status": "ACTIVE",
                "created_by_id": approved_by_id,
            },
            client=client,
        )

    async def consume_for_leave(
        self,
        *,
        user_request_id: int,
        user_id: int,
        for_date: date,
        units: float,
        client,
    ) -> None:
        if units <= 0:
            return
        grants = await self.repo.list_active_grants(user_id=user_id, as_of=for_date)
        remaining_to_use = units
        for grant in grants:
            if remaining_to_use <= 0:
                break
            take = min(float(grant.remaining_units), remaining_to_use)
            if take <= 0:
                continue
            grant.remaining_units = float(grant.remaining_units) - take
            if grant.remaining_units <= 0:
                grant.remaining_units = 0
                grant.status = "EXHAUSTED"
            await self.repo.create_usage(
                {
                    "grant_id": grant.id,
                    "user_request_id": user_request_id,
                    "used_units": take,
                    "used_for_date": for_date,
                },
                client=client,
            )
            remaining_to_use -= take
        if remaining_to_use > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient comp-off balance for requested usage.",
            )
