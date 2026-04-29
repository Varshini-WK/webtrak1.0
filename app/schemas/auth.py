from pydantic import BaseModel, EmailStr


class AuthResponse(BaseModel):
    message: str
    email: EmailStr
    name: str
    roles: list[str]
    status: str
    user_type: str
