from fastapi import UploadFile

from app.schemas.policy import PolicyCreateRequest, PolicyPublishRequest
from app.services.policy_service import PolicyService


class PolicyTool:
    def __init__(self, db) -> None:
        self.service = PolicyService(db)

    async def create_policy(self, *, actor_email: str, payload: PolicyCreateRequest, document: UploadFile) -> dict:
        return await self.service.create_policy(actor_email=actor_email, payload=payload, document=document)

    async def publish_policy(self, *, actor_email: str, policy_id: int, payload: PolicyPublishRequest) -> dict:
        return await self.service.publish_policy(actor_email=actor_email, policy_id=policy_id, payload=payload)

    async def list_my_policies(self, *, actor_email: str):
        return await self.service.list_my_policies(actor_email=actor_email)

    async def mark_viewed(self, *, actor_email: str, policy_id: int) -> dict:
        return await self.service.mark_viewed(actor_email=actor_email, policy_id=policy_id)

    async def upload_signed_copy(self, *, actor_email: str, policy_id: int, signed_copy: UploadFile) -> dict:
        return await self.service.upload_signed_copy(actor_email=actor_email, policy_id=policy_id, signed_copy=signed_copy)

    async def get_policy_compliance(self, *, policy_id: int):
        return await self.service.get_policy_compliance(policy_id=policy_id)

    async def list_signed_documents(self, *, policy_id: int):
        return await self.service.list_signed_documents(policy_id=policy_id)

    async def export_signed_documents(self, *, policy_id: int) -> dict:
        return await self.service.export_signed_documents(policy_id=policy_id)
