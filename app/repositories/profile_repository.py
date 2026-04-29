from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.user import User
from app.models.user_profile import UserProfile


def _map_profile_keys(data: dict) -> dict:
    keymap = {
        "primarySkills": "primary_skills",
        "secondarySkills": "secondary_skills",
        "personalResume": "personal_resume",
        "profilePhoto": "profile_photo",
        "panCard": "pan_card",
    }
    return {keymap.get(k, k): v for k, v in data.items()}


def _map_user_keys(data: dict) -> dict:
    keymap = {
        "empId": "emp_id",
        "userType": "user_type",
        "phoneNumber": "phone_number",
        "workMode": "work_mode",
        "deliveryStatus": "delivery_status",
        "workLocationType": "work_location_type",
        "bandId": "band_id",
        "internshipDuration": "internship_duration",
    }
    return {keymap.get(k, k): v for k, v in data.items()}


class ProfileRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def get_user_by_email(self, email: str):
        async with self.db.session() as session:
            return await session.scalar(select(User).where(User.email == email))

    async def get_user_by_emp_id(self, emp_id: str):
        async with self.db.session() as session:
            return await session.scalar(select(User).where(User.emp_id == emp_id))

    async def get_profile(self, user_id: int):
        async with self.db.session() as session:
            return await session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))

    async def get_or_create_profile(self, user_id: int, client: AsyncSession | None = None):
        session = client
        if session is None:
            async with self.db.tx() as session:
                profile = await session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
                if profile:
                    return profile
                profile = UserProfile(user_id=user_id)
                session.add(profile)
                await session.flush()
                return profile
        profile = await session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
        if profile:
            return profile
        profile = UserProfile(user_id=user_id)
        session.add(profile)
        await session.flush()
        return profile

    async def update_profile(self, user_id: int, data: dict, client: AsyncSession | None = None):
        payload = _map_profile_keys(dict(data))
        session = client
        if session is None:
            async with self.db.tx() as session:
                profile = await session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
                if profile is None:
                    profile = UserProfile(user_id=user_id)
                    session.add(profile)
                for k, v in payload.items():
                    setattr(profile, k, v)
                await session.flush()
                return profile
        profile = await session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
        if profile is None:
            profile = UserProfile(user_id=user_id)
            session.add(profile)
        for k, v in payload.items():
            setattr(profile, k, v)
        await session.flush()
        return profile

    async def update_user(self, user_id: int, data: dict, client: AsyncSession | None = None):
        payload = _map_user_keys(data)
        if client is None:
            async with self.db.tx() as session:
                user = await session.get(User, user_id)
                for k, v in payload.items():
                    setattr(user, k, v)
                await session.flush()
                return user
        user = await client.get(User, user_id)
        for k, v in payload.items():
            setattr(user, k, v)
        await client.flush()
        return user

    async def add_document(self, user_id: int, doc_type: str, file_url: str, client: AsyncSession | None = None):
        if client is None:
            async with self.db.tx() as session:
                doc = Document(user_id=user_id, doc_type=doc_type, file_url=file_url)
                session.add(doc)
                await session.flush()
                return doc
        doc = Document(user_id=user_id, doc_type=doc_type, file_url=file_url)
        client.add(doc)
        await client.flush()
        return doc
