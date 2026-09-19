from datetime import datetime, timezone
from typing import Annotated
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload

from app.middleware.auth import DbDep, require_roles
from app.models.alert import Alert, AlertStatus
from app.models.enums import RiskLevel, Role
from app.models.user import User
from app.models.zone import Zone
from app.schemas.alert import AlertAcknowledge, AlertOut, SOSCreate
from app.services.sms import send_sms

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])

OfficerUser = Annotated[User, Depends(require_roles(Role.admin, Role.officer))]


def _to_alert_out(alert: Alert, zone_name: str) -> AlertOut:
    return AlertOut(
        id=alert.id,
        ref=f"ALS-{1000 + alert.id}",
        zone_id=alert.zone_id,
        zone=zone_name,
        type=alert.level.value if hasattr(alert.level, "value") else str(alert.level),
        level=alert.level,
        kind=alert.kind,
        status=alert.status,
        message=alert.message,
        sms=alert.sms_sent,
        sms_failed=alert.sms_failed,
        recipients=alert.recipient_count,
        time=alert.created_at,
        sent_at=alert.sent_at,
        acknowledged_at=alert.acknowledged_at,
    )


@router.get("", response_model=list[AlertOut])
def list_alerts(
    db: DbDep,
    limit: int = 50,
    level: RiskLevel | None = None,
    search: str | None = None,
) -> list[AlertOut]:
    stmt = (
        select(Alert, Zone.name.label("zone_name"))
        .join(Zone, Alert.zone_id == Zone.id, isouter=True)
        .order_by(Alert.created_at.desc())
        .limit(limit)
    )
    if level is not None:
        stmt = stmt.where(Alert.level == level)
    if search:
        stmt = stmt.where(or_(Zone.name.ilike(f"%{search}%"), Alert.message.ilike(f"%{search}%")))
    rows = db.execute(stmt).all()
    return [
        AlertOut(
            id=alert.id,
            ref=f"ALS-{1000 + alert.id}",
            zone_id=alert.zone_id,
            zone=zone_name or "Unknown",
            type=alert.level.value if hasattr(alert.level, "value") else str(alert.level),
            level=alert.level,
            kind=alert.kind,
            status=alert.status,
            message=alert.message,
            sms=alert.sms_sent,
            sms_failed=alert.sms_failed,
            recipients=alert.recipient_count,
            time=alert.created_at,
            sent_at=alert.sent_at,
            acknowledged_at=alert.acknowledged_at,
        )
        for alert, zone_name in rows
    ]


@router.post("/sos", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
def trigger_sos(
    payload: SOSCreate,
    db: DbDep,
    user: OfficerUser,
) -> AlertOut:
    zone = db.get(Zone, payload.zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")

    recipients = db.scalars(
        select(User).where(User.opt_in_sms == True, User.is_active == True, User.phone.isnot(None))  # noqa: E712
    ).all()

    alert = Alert(
        zone_id=zone.id,
        triggered_by=user.id,
        level=zone.risk_level,
        kind=payload.kind,
        status=AlertStatus.pending,
        message=payload.message,
        recipient_count=len(recipients),
        created_at=datetime.now(timezone.utc),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    if recipients:
        phones = [u.phone for u in recipients if u.phone]
        msg = (
            f"LSLSOS ALERT [{zone.name}]: {payload.kind.value.upper()} "
            f"risk level {zone.risk_level.value.upper()}. "
            f"{payload.message or 'SOS triggered by officer.'}"
        )
        try:
            from app.tasks.alert_tasks import dispatch_sms_batch
            dispatch_sms_batch.delay(alert.id, phones, msg)
        except Exception:
            logger.info("Celery broker unavailable; dispatching SMS synchronously")
            from app.tasks.alert_tasks import dispatch_sms_batch
            dispatch_sms_batch(alert.id, phones, msg)

    return _to_alert_out(alert, zone.name)


@router.patch("/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge_alert(
    alert_id: int,
    db: DbDep,
    user: OfficerUser,
    payload: AlertAcknowledge | None = None,
) -> AlertOut:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.acknowledged_at is not None:
        raise HTTPException(status_code=409, detail="Alert already acknowledged")

    alert.status = AlertStatus.acknowledged
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)

    zone = db.get(Zone, alert.zone_id)
    return _to_alert_out(alert, zone.name if zone else "Unknown")
