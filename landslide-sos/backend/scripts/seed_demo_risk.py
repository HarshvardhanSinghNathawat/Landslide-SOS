#!/usr/bin/env python
"""Idempotent demo-data seeder: give zones realistic, varied risk for demos.

Overwrites the model-scored (all-green) risk with the curated zone spec from
seed_data so the prototype visibly shows yellow/red zones (no orange),
coherent RiskScore history, route detours, and demo reports — all without
API keys.

    python scripts/seed_demo_risk.py [--reset-alerts] [--reset-reports] [--dispatch-sms]

--reset-alerts   Re-seed the demo alert set (from a clean slate) too.
--reset-reports  Re-seed the demo community reports too.
--dispatch-sms   Dispatch pending alerts through the msg91 pipeline.
"""

import argparse
from datetime import datetime, timedelta, timezone
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select

from app.config import settings
from app.database import SessionLocal, engine
from app.models.alert import Alert, AlertStatus
from app.models.enums import AlertKind, RiskLevel, Role
from app.models.risk import RiskScore
from app.models.zone import Zone
from scripts.seed_data import ZONES

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
engine.echo = False

ALERT_KINDS = {
    RiskLevel.red: (AlertKind.landslide, 1240, 1580),
    RiskLevel.yellow: (AlertKind.advisory, 430, 520),
}

# Opted-in demo SMS recipients (fake numbers — never dialed in simulation).
DEMO_RECIPIENTS = [
    ("Jamuna Devi", "Dima Hasao", "+919101230001"),
    ("Riju Baruah", "Karbi Anglong", "+919101230002"),
    ("Prasenjit Das", "Cachar", "+919101230003"),
    ("Nazma Begum", "Hailakandi", "+919101230004"),
    ("Anupam Dutta", "Karimganj", "+919101230005"),
    ("Homang Devi", "Golaghat", "+919101230006"),
    ("Carey Nongrum", "East Khasi", "+919101230007"),
    ("Lalremruata", "Aizawl", "+919101230008"),
    ("Ningthoujam", "Churachandpur", "+919101230009"),
    ("Kamlang Shang", "Ukhrul", "+919101230010"),
    ("Bhaskar Saikia", "Kamrup M", "+919101230011"),
    ("Suraj Chettri", "Shillong", "+919101230012"),
]

DEMO_PASSWORD = "demo123456"

DEMO_MODEL_VERSION = "demo-data"


def _apply_zone_risk(db, zspec: dict) -> list[Zone]:
    """Set zone risk/terrain/rainfall/SWI from the curated spec; upsert RiskScore."""
    zone = db.scalar(select(Zone).where(Zone.name == zspec["name"]))
    if zone is None:
        return []
    zone.slope = zspec["slope"]
    zone.aspect = zspec["aspect"]
    zone.elevation = zspec["elevation"]
    zone.lithology = zspec["lithology"]
    zone.risk_level = zspec["risk_level"]
    zone.risk_probability = zspec["risk_probability"]
    zone.rainfall_current_mm = zspec["rainfall_current_mm"]
    zone.swi_current = zspec["swi_current"]

    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    existing = db.scalar(
        select(RiskScore).where(
            RiskScore.zone_id == zone.id, RiskScore.timestamp == now
        )
    )
    if existing is not None:
        existing.probability = zspec["risk_probability"]
        existing.level = zspec["risk_level"]
        existing.model_version = DEMO_MODEL_VERSION
    else:
        db.add(
            RiskScore(
                zone_id=zone.id,
                timestamp=now,
                probability=zspec["risk_probability"],
                level=zspec["risk_level"],
                model_version=DEMO_MODEL_VERSION,
            )
        )
    return [zone]


def _seed_alerts(db, reset: bool) -> int:
    """Seed exactly 3 demo notifications (red level only — no orange)."""
    if reset:
        for alert in db.scalars(select(Alert)).all():
            db.delete(alert)
        db.flush()

    active = (
        db.scalar(select(func.count()).select_from(Alert)) or 0
    )
    if active:
        return 0

    zones = {z.name: z for z in db.scalars(select(Zone)).all()}
    now = datetime.now(timezone.utc)
    red_zones = [zspec for zspec in ZONES if zspec["risk_level"] == RiskLevel.red][:3]

    seeded = 0
    for idx, zspec in enumerate(red_zones):
        zone = zones.get(zspec["name"])
        if zone is None:
            continue
        kind, sms, recipients = ALERT_KINDS[zspec["risk_level"]]
        status = AlertStatus.pending if idx == 0 else AlertStatus.delivered
        db.add(
            Alert(
                zone_id=zone.id,
                level=zspec["risk_level"],
                kind=kind,
                status=status,
                sms_sent=sms,
                recipient_count=recipients,
                created_at=now - timedelta(minutes=20 + idx * 25),
            )
        )
        seeded += 1
    return seeded


def _seed_demo_recipients(db) -> int:
    """Ensure the opted-in demo SMS recipients exist; return count."""
    from app.models.user import User
    from app.services.security import hash_password

    added = 0
    for i, (name, district, phone) in enumerate(DEMO_RECIPIENTS, start=1):
        exists = db.scalar(select(User).where(User.email == f"recipient{i}@demo.landslidesos.in"))
        if exists:
            continue
        db.add(
            User(
                email=f"recipient{i}@demo.landslidesos.in",
                full_name=name,
                phone=phone,
                role=Role.officer,
                hashed_password=hash_password(DEMO_PASSWORD),
                opt_in_sms=True,
                is_active=True,
            )
        )
        added += 1
    if added:
        db.commit()
    return added


def _seed_demo_reports(db, reset: bool = False) -> int:
    """Seed a few demo community reports (idempotent; skips if any exist)."""
    from app.models.enums import ReportStatus
    from app.models.report import Report
    from app.models.user import User

    if reset:
        for report in db.scalars(select(Report)).all():
            db.delete(report)
        db.flush()

    existing = db.scalar(select(func.count()).select_from(Report)) or 0
    if existing:
        return 0

    zones = {z.name: z for z in db.scalars(select(Zone)).all()}
    reporter = db.scalar(select(User).where(User.email == "officer@landslidesos.in"))
    if reporter is None:
        return 0

    now = datetime.now(timezone.utc)
    specs = [
        ("Dima Hasao - Haflong", "landslide", ReportStatus.verified,
         "Fresh cracks on the NH-6 hillside above Haflong; earth shifting overnight.", 6),
        ("Meghalaya - East Khasi", "landslide", ReportStatus.submitted,
         "New debris slide across the Shillong-Cherrapunji road, traffic blocked.", 2),
        ("Mizoram - Aizawl", "flash-flood", ReportStatus.submitted,
         "Road washout below Aizawl west; runoff carrying mud onto the highway.", 1),
        ("Karbi Anglong - Hamren", "visual-confirm", ReportStatus.verified,
         "Seepage and minor tilt observed on the slope near Hamren market.", 10),
        ("Karimganj - Baramukh", "visual-confirm", ReportStatus.resolved,
         "Inspected depression near Baramukh - no active slip detected.", 26),
        ("Cachar - Barak Foothills", "visual-confirm", ReportStatus.submitted,
         "Visible slope scar after heavy rain; monitoring requested.", 30),
    ]

    seeded = 0
    for zone_name, kind, status, description, hours_ago in specs:
        zone = zones.get(zone_name)
        if zone is None:
            continue
        db.add(
            Report(
                zone_id=zone.id,
                user_id=reporter.id,
                kind=kind,
                description=description,
                status=status,
                created_at=now - timedelta(hours=hours_ago),
            )
        )
        seeded += 1
    db.commit()
    return seeded


def _dispatch_pending_sms(db) -> int:
    """Dispatch SMS for every pending alert through the msg91 pipeline.

    In simulation mode (no MSG91_AUTH_KEY) each send resolves ok=True with a
    deterministic request id, so alerts flip to delivered with real recipient
    counts and sent_at timestamps.
    """
    from app.tasks.alert_tasks import dispatch_sms

    pending = list(
        db.scalars(
            select(Alert).where(Alert.status == AlertStatus.pending).order_by(Alert.id)
        )
    )
    if not pending:
        return 0

    zone_ids = {a.zone_id for a in pending}
    zones = {z.id: z for z in db.scalars(select(Zone).where(Zone.id.in_(zone_ids))).all()}

    dispatched = 0
    for alert in pending:
        result = dispatch_sms(alert.id)
        zone = zones.get(alert.zone_id)
        sent = result.get("sent", 0)
        print(
            "   [MSG91%s] alert#%d  %-24s %-6s -> %d/%d delivered"
            % (
                ":SIM" if sent else "",
                alert.id,
                (zone.name if zone else "?"),
                alert.level.value,
                sent,
                result.get("total", 0),
            )
        )
        dispatched += 1
    return dispatched


def seed(reset_alerts: bool, dispatch_sms: bool, reset_reports: bool = False) -> None:
    db = SessionLocal()
    try:
        applied = 0
        for zspec in ZONES:
            applied += len(_apply_zone_risk(db, zspec))
        db.commit()

        new_alerts = _seed_alerts(db, reset=reset_alerts)
        db.commit()

        recipients_added = _seed_demo_recipients(db) if dispatch_sms else 0

        reports_added = _seed_demo_reports(db, reset=reset_reports)

        zones = list(db.scalars(select(Zone).order_by(Zone.id)).all())
        print("Demo seed complete!")
        print("   Zones updated:   %d/%d" % (applied, len(ZONES)))
        print()
        for z in zones:
            print(
                "   %-42s %-6s  p=%.2f  rainfall=%.1fmm  swi=%.2f"
                % (z.name, z.risk_level.value, z.risk_probability, z.rainfall_current_mm, z.swi_current)
            )
        print()
        if new_alerts:
            print("   Demo alerts created: %d" % new_alerts)
        else:
            print("   Demo alerts: existing active alerts kept")
        print()
        colors = {"red": 0, "orange": 0, "yellow": 0, "green": 0}
        for z in zones:
            colors[z.risk_level.value] += 1
        print("   By level: %s" % ", ".join("%s=%d" % (k, v) for k, v in colors.items()))
        if reports_added:
            print("   Demo reports: %d added" % reports_added)

        if dispatch_sms:
            print()
            if recipients_added:
                print("   SMS recipients added: %d" % recipients_added)
            print("   SMS dispatch (msg91%s):" % ("" if settings.MSG91_AUTH_KEY else " simulation"))
            dispatched = _dispatch_pending_sms(db)
            if dispatched == 0:
                print("     no pending alerts to dispatch")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset-alerts", action="store_true")
    parser.add_argument("--reset-reports", action="store_true")
    parser.add_argument("--dispatch-sms", action="store_true")
    args = parser.parse_args()
    seed(reset_alerts=args.reset_alerts, dispatch_sms=args.dispatch_sms, reset_reports=args.reset_reports)