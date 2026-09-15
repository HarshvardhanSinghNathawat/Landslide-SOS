from pydantic import BaseModel

from app.models.enums import Role


class UserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None
    opt_in_sms: bool | None = None