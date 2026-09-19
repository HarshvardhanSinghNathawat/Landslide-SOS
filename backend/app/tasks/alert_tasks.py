"""Celery tasks for SMS dispatch and auto-alerting on risk escalation."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models.alert import Alert, AlertKind, AlertStatus
from app.models.enums import RiskLevel
from app.models.zone import Zone
from app.services.sms import send_sms

logger = logging.getLogger(__name__)

_LEVEL_TO_KIND: dict[RiskLevel, AlertKind] = {
    RiskLevel.red: AlertKind.landslide,
    RiskLevel.orange: AlertKind.landslide,
    RiskLevel.yellow: AlertKind.advisory,
    RiskLevel.green: AlertKind.advisory,
}


def _alert_message(zone: Zone, level: RiskLevel, kind: AlertKind) -> str:
    return (
        f"LSLSOS [{level.value.upper()}] {zone.name}: "
        f"{kind.value.upper()} risk detected. "
        f"Probability {zone.risk_probability:.0%}, SWI {zone.swi_current:.2f}. "
        f"Monitor conditions."
    )


@shared_task(name="alert.dispatch_sms")
def dispatch_sms(alert_id: int) -> dict:
    """Dispatch SMS for a single alert to all opted-in recipients."""
    db = SessionLocal()
    try:
        alert = db.get(Alert, alert_id)
        if alert is None:
            return {"error": "alert not found"}

        if alert.status != AlertStatus.pending:
            return {"status": alert.status.value, "skipped": True}

        from app.models.user import User
        recipients = db.scalars(
            select(User).where(
                User.opt_in_sms == True,  # noqa: E712
                User.is_active == True,  # noqa: E712
                User.phone.isnot(None),
            )
        ).all()
        phones = [u.phone for u in recipients if u.phone]

        zone = db.get(Zone, alert.zone_id)
        if not zone or not phones:
            alert.status = AlertStatus.delivered if not phones else AlertStatus.pending
            alert.sent_at = datetime.now(timezone.utc)
            db.commit()
            return {"skipped": True, "reason": "no recipients" if not phones else "zone missing"}

        message = (
            f"LSLSOS [{alert.level.value.upper()}] {zone.name}: "
            f"{alert.kind.value.upper()} risk detected. "
            f"Probability {zone.risk_probability:.0%}, SWI {zone.swi_current:.2f}. "
            f"{alert.message or 'Monitor conditions.'}"
        )

        sent = 0
        failed = 0
        for phone in phones:
            result = send_sms(phone, message)
            if result.ok:
                sent += 1
            else:
                failed += 1
                logger.warning("SMS to %s failed: %s", phone, result.error)

        alert.sms_sent = sent
        alert.sms_failed = failed
        alert.recipient_count = sent + failed
        alert.status = AlertStatus.delivered if sent > 0 else AlertStatus.failed
        alert.sent_at = datetime.now(timezone.utc)
        db.commit()

        logger.info("Alert %d: sent=%d failed=%d total=%d", alert_id, sent, failed, len(phones))
        return {"sent": sent, "failed": failed, "total": len(phones)}

    finally:
        db.close()


@shared_task(name="alert.dispatch_sms_batch")
def dispatch_sms_batch(alert_id: int, phones: list[str], message: str) -> dict:
    """Dispatch SMS to a pre-resolved list of phone numbers."""
    db = SessionLocal()
    try:
        alert = db.get(Alert, alert_id)
        if alert is None:
            return {"error": "alert not found"}

        sent = 0
        failed = 0
        for phone in phones:
            result = send_sms(phone, message)
            if result.ok:
                sent += 1
            else:
                failed += 1

        alert.sms_sent = sent
        alert.sms_failed = failed
        alert.recipient_count = sent + failed
        alert.status = AlertStatus.delivered if sent > 0 else AlertStatus.failed
        alert.sent_at = datetime.now(timezone.utc)
        db.commit()

        logger.info("Alert %d batch: sent=%d failed=%d", alert_id, sent, failed)
        return {"sent": sent, "failed": failed, "total": len(phones)}
    finally:
        db.close()


def check_and_create_escalation_alerts(db, results: list[dict]) -> list[int]:
    """After risk recompute, create alerts for zones that escalated to orange/red.

    Compares current zone.risk_level against the latest RiskScore before the
    current run.  Returns list of created Alert IDs.
    """
    from app.models.risk import RiskScore

    created: list[int] = []
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    for r in results:
        zone = db.get(Zone, r["zone_id"])
        if zone is None:
            continue

        level = RiskLevel(r["level"])
        if level not in (RiskLevel.red, RiskLevel.orange, RiskLevel.yellow):
            continue

        # Check if there's a previous risk score for this zone (before current minute)
        prev = db.scalar(
            select(RiskScore)
            .where(RiskScore.zone_id == zone.id, RiskScore.timestamp < now)
            .order_by(RiskScore.timestamp.desc())
            .limit(1)
        )

        # Create alert only if:
        # - no previous score exists (first-ever), OR
        # - previous level was strictly lower (escalation)
        if prev is not None:
            prev_level = RiskLevel(prev.level) if isinstance(prev.level, RiskLevel) else RiskLevel(prev.level)
            _rank = {RiskLevel.green: 0, RiskLevel.yellow: 1, RiskLevel.orange: 2, RiskLevel.red: 3}
            if _rank.get(level, 0) <= _rank.get(prev_level, 0):
                continue

        kind = _LEVEL_TO_KIND[level]
        alert = Alert(
            zone_id=zone.id,
            level=level,
            kind=kind,
            status=AlertStatus.pending,
            message=_alert_message(zone, level, kind),
            created_at=now,
        )
        db.add(alert)
        db.flush()
        created.append(alert.id)

    if created:
        db.commit()
        logger.info("Created %d escalation alerts", len(created))
        for aid in created:
            dispatch_sms.delay(aid)

    return created
