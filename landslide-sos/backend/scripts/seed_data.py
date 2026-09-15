#!/usr/bin/env python
"""Seed the database with mock-data zones and demo users.

Run from backend/ directory:
    python scripts/seed_data.py
"""

import asyncio
from datetime import datetime, timedelta, timezone
import math
import os
import sys
import zlib

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func

from app.config import settings
from app.database import SessionLocal, engine, Base
from app.models.zone import Zone
from app.models.user import User
from app.models.alert import Alert, AlertStatus
from app.models.enums import AlertKind, RiskLevel, Role
from app.models.rainfall import RainfallReading
from app.models.swi import SWIReading
from app.services.security import hash_password

ZONES = [
    {"name": "Uttarakhand - Chamoli",  "district": "Chamoli",       "state": "Uttarakhand",   "lat": 30.4, "lng": 79.3, "slope": 45.0, "aspect": 180.0, "elevation": 2200.0, "lithology": "Gneiss",           "risk_level": RiskLevel.red,    "risk_probability": 0.92, "rainfall_current_mm": 142.0, "swi_current": 0.12},
    {"name": "Himachal - Kinnaur",     "district": "Kinnaur",        "state": "Himachal Pradesh", "lat": 31.6, "lng": 78.3, "slope": 38.0, "aspect": 150.0, "elevation": 2800.0, "lithology": "Metasediment",      "risk_level": RiskLevel.orange, "risk_probability": 0.78, "rainfall_current_mm": 98.0,  "swi_current": 0.28},
    {"name": "Kerala - Wayanad",       "district": "Wayanad",        "state": "Kerala",        "lat": 11.8, "lng": 76.1, "slope": 32.0, "aspect": 90.0,  "elevation": 800.0,  "lithology": "Laterite",         "risk_level": RiskLevel.red,    "risk_probability": 0.91, "rainfall_current_mm": 187.0, "swi_current": 0.08},
    {"name": "Sikkim - North",         "district": "North Sikkim",   "state": "Sikkim",        "lat": 27.5, "lng": 88.5, "slope": 41.0, "aspect": 210.0, "elevation": 3200.0, "lithology": "Gneiss",           "risk_level": RiskLevel.yellow, "risk_probability": 0.42, "rainfall_current_mm": 76.0,  "swi_current": 0.35},
    {"name": "Meghalaya - East",       "district": "East Khasi Hills","state": "Meghalaya",    "lat": 25.5, "lng": 91.9, "slope": 29.0, "aspect": 135.0, "elevation": 1200.0, "lithology": "Sandstone",        "risk_level": RiskLevel.orange, "risk_probability": 0.71, "rainfall_current_mm": 124.0, "swi_current": 0.22},
    {"name": "Mahabaleshwar",          "district": "Satara",         "state": "Maharashtra",   "lat": 17.9, "lng": 73.6, "slope": 26.0, "aspect": 110.0, "elevation": 1350.0, "lithology": "Basalt",           "risk_level": RiskLevel.yellow, "risk_probability": 0.48, "rainfall_current_mm": 89.0,  "swi_current": 0.31},
    {"name": "Ooty - Nilgiris",        "district": "Nilgiris",       "state": "Tamil Nadu",    "lat": 11.4, "lng": 76.7, "slope": 22.0, "aspect": 100.0, "elevation": 2240.0, "lithology": "Granite",          "risk_level": RiskLevel.green,  "risk_probability": 0.15, "rainfall_current_mm": 54.0,  "swi_current": 0.52},
    {"name": "Darjeeling",             "district": "Darjeeling",     "state": "West Bengal",   "lat": 27.0, "lng": 88.3, "slope": 48.0, "aspect": 190.0, "elevation": 2100.0, "lithology": "Phyllite",         "risk_level": RiskLevel.red,    "risk_probability": 0.88, "rainfall_current_mm": 156.0, "swi_current": 0.10},
    {"name": "Munnar - Idukki",        "district": "Idukki",         "state": "Kerala",        "lat": 10.1, "lng": 77.1, "slope": 35.0, "aspect": 75.0,  "elevation": 1600.0, "lithology": "Gneiss",           "risk_level": RiskLevel.orange, "risk_probability": 0.74, "rainfall_current_mm": 112.0, "swi_current": 0.19},
    {"name": "Cherrapunji",            "district": "East Khasi Hills","state": "Meghalaya",    "lat": 25.3, "lng": 91.7, "slope": 30.0, "aspect": 170.0, "elevation": 1480.0, "lithology": "Sandstone",        "risk_level": RiskLevel.yellow, "risk_probability": 0.44, "rainfall_current_mm": 95.0,  "swi_current": 0.38},
]

# Bootstrap admin (password: admin123456 for dev)
ADMIN_PASSWORD = "admin123456"
OFFICER_PASSWORD = "officer123456"

# Monsoon-style daily rainfall history (45 days) per zone for the SWI engine.
HISTORY_DAYS = 45
_HISTORY_TS_HOURS = (7, 19)  # two daily readings; avoids seed's hourly buckets (00,03,...)


def _zone_base_rainfall(zone) -> float:
    """Deterministic per-zone daily rainfall mean (mm) from mock intensity."""
    # Roughly scale by current mock rainfall intensity (mm "current"/10)
    return max(3.0, min(30.0, zone.rainfall_current_mm / 10.0))


def _daily_rainfall_history(zone) -> list[float]:
    """Deterministic monsoon-shaped daily series for HISTORY_DAYS ending today."""
    rng = np.random.default_rng(zlib.crc32(zone.name.encode("utf-8")))
    base = _zone_base_rainfall(zone)
    series = np.zeros(HISTORY_DAYS, dtype=float)

    # 4-6 rainy clusters of 4-8 days each (monsoon bursts)
    n_clusters = 6
    for _ in range(n_clusters):
        length = int(rng.integers(4, 9))
        start = int(rng.integers(0, HISTORY_DAYS - length))
        for k in range(length):
            idx = start + k
            burst = 1.0 + 2.2 * math.sin(math.pi * (k + 1) / (length + 1))
            series[idx] += base * burst * rng.uniform(0.5, 1.1)

    # scattered light rain
    sprinkle = rng.choice(HISTORY_DAYS, size=int(HISTORY_DAYS * 0.15), replace=False)
    series[sprinkle] += rng.uniform(1.0, base * 0.4, size=sprinkle.size)

    return [round(v, 1) for v in series]


def _seed_rainfall_history(db, zone) -> None:
    """Upsert 45 days of two-point daily rainfall for one zone."""
    daily = _daily_rainfall_history(zone)
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    for days_ago in range(HISTORY_DAYS, 0, -1):
        day_ts = now - timedelta(days=days_ago)
        total = daily[HISTORY_DAYS - days_ago]
        for fraction, hour in ((0.65, _HISTORY_TS_HOURS[0]), (0.35, _HISTORY_TS_HOURS[1])):
            ts = day_ts.replace(hour=hour)
            exists = db.scalar(
                select(func.count())
                .select_from(RainfallReading)
                .where(RainfallReading.zone_id == zone.id, RainfallReading.timestamp == ts)
            )
            if exists and exists > 0:
                continue
            db.add(RainfallReading(
                zone_id=zone.id,
                timestamp=ts,
                observed_mm=round(total * fraction, 1),
                forecast_mm=None,
            ))


def seed():
    # Ensure tables exist (AUTO_CREATE_TABLES handles this, but be explicit for seed)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # --- seed users ---
        existing_admin = db.scalar(select(User).where(User.email == "admin@landslidesos.in"))
        if not existing_admin:
            admin = User(
                email="admin@landslidesos.in",
                full_name="Admin User",
                hashed_password=hash_password(ADMIN_PASSWORD),
                phone="+919999900001",
                role=Role.admin,
                opt_in_sms=False,
            )
            db.add(admin)

        existing_officer = db.scalar(select(User).where(User.email == "officer@landslidesos.in"))
        if not existing_officer:
            officer = User(
                email="officer@landslidesos.in",
                full_name="Field Officer",
                hashed_password=hash_password(OFFICER_PASSWORD),
                phone="+919999900002",
                role=Role.officer,
                opt_in_sms=True,
            )
            db.add(officer)

        db.commit()

        # --- seed zones ---
        existing_zone_count = db.scalar(select(func.count()).select_from(Zone)) or 0
        if existing_zone_count == 0:
            for z in ZONES:
                zone = Zone(**z)
                db.add(zone)
            db.commit()

        # --- seed demo alerts ---
        existing_alert_count = db.scalar(select(func.count()).select_from(Alert)) or 0
        if existing_alert_count == 0:
            zones = list(db.scalars(select(Zone).limit(10)).all())
            now = datetime.now(timezone.utc)
            seed_alerts = [
                (zones[0], AlertKind.landslide, RiskLevel.red,    AlertStatus.delivered,    1240, 1580, 2),
                (zones[2], AlertKind.landslide, RiskLevel.red,    AlertStatus.delivered,     980, 1120, 18),
                (zones[7], AlertKind.landslide, RiskLevel.orange, AlertStatus.acknowledged,  650, 780,  45),
                (zones[1], AlertKind.advisory,   RiskLevel.yellow, AlertStatus.delivered,    430, 520,  60),
                (zones[4], AlertKind.landslide, RiskLevel.orange, AlertStatus.pending,       310, 450, 120),
                (zones[3], AlertKind.landslide, RiskLevel.yellow, AlertStatus.delivered,     280, 340, 180),
                (zones[8], AlertKind.advisory,   RiskLevel.green,  AlertStatus.acknowledged, 150, 200, 300),
                (zones[5], AlertKind.advisory,   RiskLevel.yellow, AlertStatus.delivered,     200, 260, 360),
            ]
            for zone, kind, level, status, sms, recipients, mins_ago in seed_alerts:
                alert = Alert(
                    zone_id=zone.id,
                    level=level,
                    kind=kind,
                    status=status,
                    sms_sent=sms,
                    recipient_count=recipients,
                    created_at=now - timedelta(minutes=mins_ago),
                )
                db.add(alert)
            db.commit()

        # --- seed rainfall history (monsoon series for SWI engine) + today's buckets ---
        zones = list(db.scalars(select(Zone).limit(10)).all())
        for zone in zones:
            _seed_rainfall_history(db, zone)
        db.commit()

        # today's hourly mock buckets (upsert to keep /rainfall chart populated)
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        mock_rainfall_points = [
            ("00:00", 12, 15), ("03:00", 28, 30), ("06:00", 45, 52), ("09:00", 68, 75),
            ("12:00", 92, 88), ("15:00", 110, 105), ("18:00", 85, 95), ("21:00", 62, 70),
        ]
        for zone in zones:
            for time_str, value, forecast in mock_rainfall_points:
                hour, minute = map(int, time_str.split(":"))
                ts = now.replace(hour=hour, minute=minute)
                exists = db.scalar(
                    select(func.count())
                    .select_from(RainfallReading)
                    .where(RainfallReading.zone_id == zone.id, RainfallReading.timestamp == ts)
                )
                if exists and exists > 0:
                    continue
                db.add(RainfallReading(
                    zone_id=zone.id,
                    timestamp=ts,
                    observed_mm=value,
                    forecast_mm=forecast,
                ))
        db.commit()

        # --- seed SWI readings for today ---
        existing_swi = db.scalar(select(func.count()).select_from(SWIReading)) or 0
        if existing_swi == 0:
            zones = list(db.scalars(select(Zone).limit(10)).all())
            now = datetime.now(timezone.utc)
            mock_swi_points = [
                (6, 0.52, 0.50), (8, 0.45, 0.43), (10, 0.38, 0.36), (12, 0.28, 0.27),
                (14, 0.18, 0.19), (16, 0.12, 0.13),
            ]
            for zone in zones:
                for hour, computed, satellite in mock_swi_points:
                    ts = now.replace(hour=hour, minute=0, second=0, microsecond=0)
                    db.add(SWIReading(
                        zone_id=zone.id,
                        timestamp=ts,
                        computed_swi=computed,
                        satellite_swi=satellite,
                    ))
            db.commit()

        # Print summary
        zones = list(db.scalars(select(Zone).limit(20)).all())
        alerts = list(db.scalars(select(Alert).limit(20)).all())
        users = list(db.scalars(select(User).limit(20)).all())
        rainfall_count = db.scalar(select(func.count()).select_from(RainfallReading)) or 0
        swi_count = db.scalar(select(func.count()).select_from(SWIReading)) or 0
        print("✅ Seed complete!")
        print(f"   Users:     {len(users)} (admin@landslidesos.in / officer@landslidesos.in)")
        print(f"   Zones:     {len(zones)}")
        print(f"   Alerts:    {len(alerts)}")
        print(f"   Rainfall:  {rainfall_count} readings")
        print(f"   SWI:       {swi_count} readings")
        print()
        print("   Admin password:   admin123456")
        print("   Officer password: officer123456")

    finally:
        db.close()


if __name__ == "__main__":
    seed()