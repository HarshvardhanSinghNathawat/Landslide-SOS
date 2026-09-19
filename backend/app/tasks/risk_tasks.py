"""Celery tasks: 30-minute risk recompute for every monitoring zone."""

import logging

from celery import shared_task

from app.database import SessionLocal
from app.services.model.trainer import score_all_zones

logger = logging.getLogger(__name__)


@shared_task(name="risk.recompute_all")
def recompute_all() -> list[dict]:
    """Refresh SWI and fused risk for every zone (runs on a 30-min beat).

    After scoring, zones that escalated to yellow/orange/red automatically
    create an Alert and queue an SMS dispatch (Phase 3).
    """
    from app.tasks.alert_tasks import check_and_create_escalation_alerts

    db = SessionLocal()
    try:
        results = score_all_zones(db)
        logger.info("Recomputed risk for %d zones", len(results))
        created = check_and_create_escalation_alerts(db, results)
        logger.info("Escalation alerts created: %d", len(created))
        return results
    finally:
        db.close()