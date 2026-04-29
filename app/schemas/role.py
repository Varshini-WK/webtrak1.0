from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field


class AssignRoleRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    target_email: EmailStr = Field(validation_alias=AliasChoices("target_email", "userEmail"))
    role: str = Field(validation_alias=AliasChoices("role", "roleName"))


class AssignRoleRequestJava(BaseModel):
    userEmail: EmailStr
    roleName: str


class AssignRoleResponse(BaseModel):
    target_email: EmailStr
    assigned_role: str
    assigned_by: str
    message: str
