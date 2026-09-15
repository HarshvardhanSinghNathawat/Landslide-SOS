"""Unit tests for the 3-tank SWI engine."""

import sys
import os
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.services.swi.engine import (
    daily_from_hourly,
    compute_swi_series,
    swi_to_risk_level,
)
from app.models.enums import RiskLevel


def test_daily_from_hourly_aggregates():
    now = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    hourly = [
        (now, 12.0),
        (now.replace(hour=15), 18.0),
        (now.replace(day=2, hour=3), 30.0),
    ]
    daily = daily_from_hourly(hourly)
    assert daily == [(date(2026, 9, 1), 30.0), (date(2026, 9, 2), 30.0)]


def test_swi_bounded_and_responds_to_rain():
    series = compute_swi_series([0.0] * 30 + [120.0] * 10)
    assert all(0.0 <= v <= 1.0 for v in series)
    assert series[-1] > series[20]  # rain raises SWI
    assert series[20] < 0.2  # dry period stays low


def test_swi_decays_after_rain_stops():
    series = compute_swi_series([100.0] * 15 + [0.0] * 60)
    peak = max(series)
    assert series[-1] < peak * 0.3  # slow recession after rain stops


def test_swi_dry_series_stays_near_zero():
    series = compute_swi_series([0.0] * 100)
    assert series[-1] < 0.01


def test_swi_thresholds():
    assert swi_to_risk_level(0.50) == RiskLevel.green
    assert swi_to_risk_level(0.35) == RiskLevel.yellow
    assert swi_to_risk_level(0.25) == RiskLevel.orange
    assert swi_to_risk_level(0.15) == RiskLevel.red