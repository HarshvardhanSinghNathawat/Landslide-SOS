from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import func, select

from app.middleware.auth import DbDep
from app.models.alert import Alert, AlertStatus
from app.models.enums import RiskLevel
from app.models.model_run import ModelRun
from app.models.rainfall import RainfallReading
from app.models.zone import Zone
from app.schemas.dashboard import StatsOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=StatsOut)
def get_stats(db: DbDep) -> StatsOut:
    zones_monitored = db.scalar(select(func.count()).select_from(Zone)) or 0
    active_alerts = db.scalar(
        select(func.count()).select_from(Alert).where(
            Alert.status.in_([AlertStatus.pending, AlertStatus.delivered])
        )
    ) or 0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    sms_sent_today = db.scalar(
        select(func.coalesce(func.sum(Alert.sms_sent), 0)).where(Alert.created_at >= today_start)
    ) or 0

    lives_at_risk = db.scalar(
        select(func.coalesce(func.sum(Alert.recipient_count), 0)).where(
            Alert.status.in_([AlertStatus.pending, AlertStatus.delivered])
        )
    ) or 0

    rainfall_stations = db.scalar(
        select(func.count(func.distinct(RainfallReading.zone_id)))
    ) or 0

    model_accuracy = db.scalar(
        select(ModelRun.accuracy)
        .order_by(ModelRun.id.desc())
        .limit(1)
    )

    return StatsOut(
        zonesMonitored=zones_monitored,
        activeAlerts=active_alerts,
        smsSentToday=int(sms_sent_today),
        livesAtRisk=int(lives_at_risk),
        rainfallStations=rainfall_stations,
        modelAccuracy=model_accuracy,
    )