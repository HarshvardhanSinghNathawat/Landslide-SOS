from pydantic import BaseModel, EmailStr, Field

from app.models.enums import Role


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    role: Role | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    is_active: bool | None = None
    opt_in_sms: bool | None = None


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    role: Role = Role.public
    phone: str | None = Field(default=None, max_length=20)
    opt_in_sms: bool = False