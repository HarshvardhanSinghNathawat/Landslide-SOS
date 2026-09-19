from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import Role


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    phone: str | None = None
    role: Role
    opt_in_sms: bool
    is_active: bool
    created_at: datetime