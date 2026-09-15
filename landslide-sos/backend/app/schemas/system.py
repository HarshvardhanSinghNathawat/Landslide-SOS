from pydantic import BaseModel


class ComponentHealth(BaseModel):
    name: str
    status: str
    uptime: str | None = None
    latency: str | None = None


class HealthOut(BaseModel):
    status: str
    database: str
    components: list[ComponentHealth]