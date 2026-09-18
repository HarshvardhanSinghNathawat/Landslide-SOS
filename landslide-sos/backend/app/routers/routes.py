from fastapi import APIRouter
from sqlalchemy import or_, select

from app.middleware.auth import DbDep
from app.models.alert import Alert, AlertStatus
from app.models.enums import RiskLevel
from app.models.zone import Zone
from app.schemas.route import RoutePlan, RouteRequest
from app.services import routing

router = APIRouter(prefix="/routes", tags=["routes"])


@router.post("/plan", response_model=RoutePlan)
def plan(payload: RouteRequest, db: DbDep) -> RoutePlan:
    zones = db.scalars(select(Zone)).all()
    alerts = db.scalars(
        select(Alert).where(
            Alert.status.in_([AlertStatus.pending, AlertStatus.delivered]),
            Alert.level.in_([RiskLevel.orange, RiskLevel.red]),
        )
    ).all()
    zone_dicts = [
        {
            "id": z.id,
            "name": z.name,
            "district": z.district,
            "state": z.state,
            "lat": z.lat,
            "lng": z.lng,
            "risk": z.risk_level.value,
        }
        for z in zones
    ]
    data = routing.plan_route(
        [payload.start_lat, payload.start_lng],
        [payload.end_lat, payload.end_lng],
        zone_dicts,
        alerts=[{"zone_id": a.zone_id, "level": a.level.value} for a in alerts],
    )
    return RoutePlan.model_validate(data)
