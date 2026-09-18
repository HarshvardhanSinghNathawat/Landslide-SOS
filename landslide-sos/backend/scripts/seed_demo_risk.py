#!/usr/bin/env python
"""Idempotent demo-data seeder: give zones realistic, varied risk for demos.

Overwrites the model-scored (all-green) risk with the curated zone spec from
seed_data so the prototype visibly shows yellow/orange/red zones, coherent
RiskScore history, and route detours — all without API keys.

    python scripts/seed_demo_risk.py [--reset-alerts] [--history-alerts]
                                       [--dispatch-sms]

--reset-alerts   Re-seed the demo alert set (from a clean slate) too.
--history-alerts Add a deterministic ~7-day alert history (mixed statuses).
--dispatch-sms   Dispatch pending alerts through the msg91 pipeline.
"""

import argparse
from datetime import datetime, timedelta, timezone
import logging
import math
import os
import sys
import zlib

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
    RiskLevel.orange: (AlertKind.landslide, 650, 780),
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

HISTORY_TOTAL = 20
HISTORY_DAYS = 7

_LEVEL_KIND = {
    RiskLevel.red: AlertKind.landslide,
    RiskLevel.orange: AlertKind.landslide,
    RiskLevel.yellow: AlertKind.monsoon,
    RiskLevel.green: AlertKind.advisory,
}


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
    """Ensure a spread of demo alerts exists; optional clean-slate reset."""
    if reset:
        for alert in db.scalars(select(Alert)).all():
            db.delete(alert)
        db.flush()

    active = (
        db.scalar(
            select(func.count())
            .select_from(Alert)
            .where(Alert.status.in_([AlertStatus.pending, AlertStatus.delivered]))
        )
        or 0
    )
    if active:
        return 0

    zones = {z.name: z for z in db.scalars(select(Zone)).all()}
    now = datetime.now(timezone.utc)
    seeded = 0
    for idx, zspec in enumerate(ZONES):
        zone = zones.get(zspec["name"])
        if zone is None:
            continue
        kind, sms, recipients = ALERT_KINDS[zspec["risk_level"]]
        status = AlertStatus.pending if idx % 3 == 0 else AlertStatus.delivered
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


def _rng(seed: str):
    """Deterministic PRNG for reproducible demo data."""
    state = zlib.crc32(seed.encode("utf-8")) or 1

    def rnd() -> float:
        nonlocal state
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        return state / 0x7FFFFFFF

    return rnd


def _pick_level(day_offset: int, p: float) -> RiskLevel:
    """Rainy peak on recent days → red/orange; earlier days ease to yellow/green."""
    if day_offset >= 6:
        return RiskLevel.red if p < 0.55 else RiskLevel.orange
    if day_offset >= 4:
        return RiskLevel.orange if p < 0.45 else (RiskLevel.yellow if p < 0.85 else RiskLevel.green)
    return RiskLevel.yellow if p < 0.5 else RiskLevel.green


def _history_alert_specs() -> list[dict]:
    """Deterministic ~7-day alert history: 20 alerts across the 10 zones."""
    from app.models.user import User

    now = datetime.now(timezone.utc)
    specs = []
    for i in range(HISTORY_TOTAL):
        zone_idx = i % len(ZONES)
        rnd = _rng(f"h:{zone_idx}:{i}")
        day_offset = 1 + int(rnd() * HISTORY_DAYS)          # 1 = oldest, 7 = today
        level = _pick_level(day_offset, rnd())
        kind = _LEVEL_KIND[level]
        if level == RiskLevel.orange and rnd() < 0.35:
            kind = AlertKind.flash_flood

        status = AlertStatus.pending if day_offset == 7 else AlertStatus.delivered
        if day_offset == 6:
            status = AlertStatus.acknowledged
        elif i % 13 == 0:
            status = AlertStatus.failed

        sent = 8 + int(rnd() * 9)                            # 8–16 recipients
        failed = 1 + int(rnd() * 2) if status == AlertStatus.failed else 0

        created = now - timedelta(days=day_offset, hours=int(rnd() * 20), minutes=int(rnd() * 59))
        sent_at = created + timedelta(minutes=2 + int(rnd() * 8))
        ack_at = sent_at + timedelta(hours=1 + int(rnd() * 10)) if status == AlertStatus.acknowledged else None
        specs.append({
            "zone_idx": zone_idx,
            "level": level,
            "kind": kind,
            "status": status,
            "sms_sent": sent,
            "sms_failed": failed,
            "created_at": created,
            "sent_at": sent_at,
            "acknowledged_at": ack_at,
        })
    return specs


def _seed_history_alerts(db) -> int:
    """Insert the ~7-day alert history once (skips if any pre-today alert exists)."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    existing_old = (
        db.scalar(
            select(func.count()).select_from(Alert).where(Alert.created_at < today_start)
        )
        or 0
    )
    if existing_old:
        return 0

    zones = list(db.scalars(select(Zone).order_by(Zone.id)).all())
    zone_by_idx = {i: z for i, z in enumerate(zones)}
    probability_by_zone = {i: ZONES[i]["risk_probability"] for i in range(len(ZONES))}

    created = 0
    for spec in _history_alert_specs():
        zone = zone_by_idx.get(spec["zone_idx"])
        if zone is None:
            continue
        prob = probability_by_zone.get(spec["zone_idx"], 0.5)
        db.add(
            Alert(
                zone_id=zone.id,
                level=spec["level"],
                kind=spec["kind"],
                status=spec["status"],
                sms_sent=spec["sms_sent"],
                sms_failed=spec["sms_failed"],
                recipient_count=spec["sms_sent"] + spec["sms_failed"],
                created_at=spec["created_at"],
                sent_at=spec["sent_at"],
                acknowledged_at=spec["acknowledged_at"],
                message=(
                    "LSLSOS [%s] %s: %s risk detected. "
                    "Probability %.0f%%, SWI %.2f. Monitor conditions."
                    % (
                        spec["level"].value.upper(),
                        zone.name,
                        spec["kind"].value.upper(),
                        prob * 100,
                        zone.swi_current or 0.0,
                    )
                ),
            )
        )
        created += 1
    return created


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


def seed(reset_alerts: bool, dispatch_sms: bool, history_alerts: bool) -> None:
    db = SessionLocal()
    try:
        applied = 0
        for zspec in ZONES:
            applied += len(_apply_zone_risk(db, zspec))
        db.commit()

        new_alerts = _seed_alerts(db, reset=reset_alerts)
        db.commit()

        history = _seed_history_alerts(db) if history_alerts else 0
        db.commit()

        recipients_added = _seed_demo_recipients(db) if dispatch_sms else 0

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
        if history_alerts:
            if history:
                print("   History alerts created: %d" % history)
            else:
                print("   History alerts: already present (skipped)")
        print()
        colors = {"red": 0, "orange": 0, "yellow": 0, "green": 0}
        for z in zones:
            colors[z.risk_level.value] += 1
        print("   By level: %s" % ", ".join("%s=%d" % (k, v) for k, v in colors.items()))

        if dispatch_sms:
            print()
            if recipients_added:
                print("   SMS recipients added: %d" % recipients_added)
            print("   SMS dispatch (msg91%s):" % ("" if settings.MSG91_AUTH_KEY else " simulation"))
            dispatched = _dispatch_pending_sms(db)
            if dispatched == 0:
                print("     no pending alerts to dispatch")

        if history_alerts:
            statuses = {"pending": 0, "delivered": 0, "failed": 0, "acknowledged": 0}
            for s in db.scalars(select(Alert.status)).all():
                statuses[s.value] = statuses.get(s.value, 0) + 1
            print()
            print("   Alert status: %s" % ", ".join("%s=%d" % (k, v) for k, v in statuses.items()))

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset-alerts", action="store_true")
    parser.add_argument("--history-alerts", action="store_true")
    parser.add_argument("--dispatch-sms", action="store_true")
    args = parser.parse_args()
    seed(reset_alerts=args.reset_alerts, dispatch_sms=args.dispatch_sms, history_alerts=args.history_alerts)