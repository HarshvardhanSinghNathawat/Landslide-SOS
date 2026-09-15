from pydantic import BaseModel


class StatsOut(BaseModel):
    zonesMonitored: int
    activeAlerts: int
    smsSentToday: int
    livesAtRisk: int
    rainfallStations: int
    modelAccuracy: float | None = None