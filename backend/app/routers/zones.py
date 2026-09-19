from fastapi import APIRouter, HTTPException, status
from sqlalchemy import case, select

from app.middleware.auth import DbDep
from app.models.enums import RiskLevel
from app.models.risk import RiskScore
from app.models.swi import SWIReading
from app.models.zone import Zone
from app.schemas.risk import RiskOut
from app.schemas.swi import SWIPoint, SWISeries
from app.schemas.zone import ZoneOut

router = APIRouter(prefix="/zones", tags=["zones"])

SEVERITY = case(
    (Zone.risk_level == RiskLevel.red, 4),
    (Zone.risk_level == RiskLevel.orange, 3),
    (Zone.risk_level == RiskLevel.yellow, 2),
    (Zone.risk_level == RiskLevel.green, 1),
    else_=0,
)


def _risk_from_swi(swi: float) -> RiskLevel:
    if swi >= 0.45:
        return RiskLevel.green
    if swi >= 0.32:
        return RiskLevel.yellow
    if swi >= 0.22:
        return RiskLevel.orange
    return RiskLevel.red


def _get_zone_or_404(db: DbDep, zone_id: int) -> Zone:
    zone = db.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    return zone


@router.get("", response_model=list[ZoneOut])
def list_zones(db: DbDep, risk: RiskLevel | None = None) -> list[Zone]:
    stmt = select(Zone)
    if risk is not None:
        stmt = stmt.where(Zone.risk_level == risk)
    stmt = stmt.order_by(SEVERITY.desc(), Zone.rainfall_current_mm.desc())
    return list(db.scalars(stmt).all())


@router.get("/{zone_id}/swi", response_model=SWISeries)
def zone_swi(zone_id: int, db: DbDep) -> SWISeries:
    zone = _get_zone_or_404(db, zone_id)
    readings = db.scalars(
        select(SWIReading)
        .where(SWIReading.zone_id == zone_id)
        .order_by(SWIReading.timestamp.asc())
    ).all()

    derived = []
    for r in readings:
        derived.append(
            SWIPoint(
                date=r.timestamp.date(),
                swi=r.computed_swi,
                risk=_risk_from_swi(r.computed_swi),
            )
        )
    if not derived:
        derived.append(
            SWIPoint(date=zone.last_updated.date(), swi=zone.swi_current, risk=zone.risk_level)
        )
    return SWISeries(zone_id=zone_id, points=derived)


@router.get("/{zone_id}/risk", response_model=RiskOut)
def zone_risk(zone_id: int, db: DbDep) -> RiskOut:
    zone = _get_zone_or_404(db, zone_id)
    latest = db.scalar(
        select(RiskScore)
        .where(RiskScore.zone_id == zone_id)
        .order_by(RiskScore.timestamp.desc())
        .limit(1)
    )
    if latest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No risk score computed yet for this zone (Phase 2b populates these)",
        )
    return RiskOut(
        zone_id=zone_id,
        probability=latest.probability,
        level=latest.level,
        computed_at=latest.timestamp,
        model_version=latest.model_version,
    )