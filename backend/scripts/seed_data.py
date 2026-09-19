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
    {"name": "Dima Hasao - Haflong",      "district": "Dima Hasao",       "state": "Assam",     "lat": 25.1647, "lng": 93.0188, "slope": 42.0, "aspect": 180.0, "elevation": 900.0,  "lithology": "Sandstone",     "risk_level": RiskLevel.red,    "risk_probability": 0.91, "rainfall_current_mm": 148.0, "swi_current": 0.10},
    {"name": "Karbi Anglong - Hamren",    "district": "Karbi Anglong",    "state": "Assam",     "lat": 25.8400, "lng": 93.4300, "slope": 38.0, "aspect": 150.0, "elevation": 700.0,  "lithology": "Sandstone",     "risk_level": RiskLevel.yellow, "risk_probability": 0.44, "rainfall_current_mm": 118.0, "swi_current": 0.22},
    {"name": "Cachar - Barak Foothills",  "district": "Cachar",           "state": "Assam",     "lat": 24.8200, "lng": 92.8000, "slope": 30.0, "aspect": 135.0, "elevation": 180.0,  "lithology": "Sandstone",     "risk_level": RiskLevel.yellow, "risk_probability": 0.42, "rainfall_current_mm": 125.0, "swi_current": 0.19},
    {"name": "Hailakandi - Katlicherra",  "district": "Hailakandi",       "state": "Assam",     "lat": 24.6800, "lng": 92.5600, "slope": 28.0, "aspect": 110.0, "elevation": 90.0,   "lithology": "Sandstone",     "risk_level": RiskLevel.yellow, "risk_probability": 0.45, "rainfall_current_mm": 96.0,   "swi_current": 0.31},
    {"name": "Karimganj - Baramukh",      "district": "Karimganj",        "state": "Assam",     "lat": 24.8700, "lng": 92.3600, "slope": 26.0, "aspect": 100.0, "elevation": 80.0,   "lithology": "Sandstone",     "risk_level": RiskLevel.yellow, "risk_probability": 0.42, "rainfall_current_mm": 101.0, "swi_current": 0.29},
    {"name": "Golaghat - Nambor RF",      "district": "Golaghat",         "state": "Assam",     "lat": 26.5000, "lng": 93.9000, "slope": 25.0, "aspect": 95.0,  "elevation": 130.0,  "lithology": "Sandstone",     "risk_level": RiskLevel.yellow, "risk_probability": 0.48, "rainfall_current_mm": 89.0,   "swi_current": 0.33},
    {"name": "Meghalaya - East Khasi",    "district": "East Khasi Hills","state": "Meghalaya",  "lat": 25.5700, "lng": 91.8800, "slope": 33.0, "aspect": 170.0, "elevation": 1520.0, "lithology": "Sandstone",     "risk_level": RiskLevel.red,    "risk_probability": 0.88, "rainfall_current_mm": 201.0, "swi_current": 0.08},
    {"name": "Mizoram - Aizawl",          "district": "Aizawl",           "state": "Mizoram",    "lat": 23.7300, "lng": 92.7200, "slope": 40.0, "aspect": 200.0, "elevation": 1130.0, "lithology": "Metasediment",  "risk_level": RiskLevel.red,    "risk_probability": 0.87, "rainfall_current_mm": 176.0, "swi_current": 0.12},
    {"name": "Manipur - Churachandpur",   "district": "Churachandpur",    "state": "Manipur",    "lat": 24.3300, "lng": 93.6800, "slope": 35.0, "aspect": 160.0, "elevation": 850.0,  "lithology": "Metasediment",  "risk_level": RiskLevel.yellow, "risk_probability": 0.43, "rainfall_current_mm": 132.0, "swi_current": 0.20},
    {"name": "Manipur - Ukhrul",          "district": "Ukhrul",           "state": "Manipur",    "lat": 25.1000, "lng": 94.3700, "slope": 37.0, "aspect": 210.0, "elevation": 1800.0, "lithology": "Metasediment",  "risk_level": RiskLevel.yellow, "risk_probability": 0.44, "rainfall_current_mm": 141.0, "swi_current": 0.17},
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
                (zones[0], AlertKind.landslide, RiskLevel.red,    AlertStatus.delivered,      1240, 1580, 25),
                (zones[6], AlertKind.landslide, RiskLevel.red,    AlertStatus.delivered,      1240, 1580, 130),
                (zones[7], AlertKind.landslide, RiskLevel.red,    AlertStatus.pending,        1240, 1580, 300),
                (zones[1], AlertKind.advisory,   RiskLevel.yellow, AlertStatus.delivered,     430, 520,  27 * 60),
                (zones[5], AlertKind.advisory,   RiskLevel.yellow, AlertStatus.delivered,     430, 520,  49 * 60),
                (zones[2], AlertKind.advisory,   RiskLevel.yellow, AlertStatus.acknowledged,  430, 520,  78 * 60),
                (zones[4], AlertKind.advisory,   RiskLevel.yellow, AlertStatus.failed,        0,   520,  98 * 60),
                (zones[8], AlertKind.advisory,   RiskLevel.yellow, AlertStatus.delivered,     430, 520,  124 * 60),
                (zones[9], AlertKind.advisory,   RiskLevel.yellow, AlertStatus.acknowledged,  430, 520,  145 * 60),
                (zones[3], AlertKind.advisory,   RiskLevel.yellow, AlertStatus.delivered,     430, 520,  162 * 60),
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