"""IMD Rainfall Client — real-time AWS station data via api.imd.gov.in.

With IMD_API_KEY configured and the server IP whitelisted, this fetches
Automatic Weather Station (AWS) data mapping to find the nearest station to a
zone, then pulls the station's latest rainfall reading.

Without IMD_API_KEY the client runs in SIMULATION mode: it returns
deterministic, monsoon-plausible readings (tagged "SIM-*" stations) so the full
rainfall → SWI → risk pipeline stays demonstrable. Provide a real key to go live.
"""

from __future__ import annotations

import logging
import math
import zlib
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings
from app.services.geo import haversine_m

logger = logging.getLogger(__name__)

_BASE_URL = settings.IMD_API_BASE_URL.rstrip("/")

_CACHE_TTL_S = 3600  # re-fetch station mapping hourly
_station_cache: dict[str, Any] = {"data": None, "ts": 0.0}


class IMDError(Exception):
    """Raised when IMD returns a non-200 response or bad JSON."""


class IMDNotConfigured(Exception):
    """Raised when IMD_API_KEY is not set — caller should fall back to DB."""


def _simulate_last_24h(lat: float, lng: float) -> dict[str, Any]:
    """Deterministic monsoon-plausible reading for a (lat, lng) — simulation mode."""
    key = f"{lat:.3f}:{lng:.3f}"
    state = zlib.crc32(key.encode("utf-8")) or 1

    def rnd() -> float:
        nonlocal state
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        return state / 0x7FFFFFFF

    base = 60.0 + rnd() * 150.0                       # 60–210 mm daily intensity
    hour = datetime.now(timezone.utc).hour
    pulse = 1.0 + 0.35 * math.sin(math.pi * (hour + rnd() * 4) / 12.0)
    mm = base * (0.75 + 0.5 * pulse) * (0.85 + 0.3 * rnd())

    name = f"SIM-{state % 10000:04d}"
    return {
        "station": name,
        "last_24h_mm": round(max(5.0, min(250.0, mm)), 1),
        "raw_response": {"simulated": True, "note": "no IMD_API_KEY configured"},
    }


def _api_key() -> str:
    if not settings.IMD_API_KEY:
        raise IMDNotConfigured("IMD_API_KEY not configured")
    return settings.IMD_API_KEY


def _get_client() -> httpx.Client:
    return httpx.Client(
        base_url=_BASE_URL,
        timeout=30.0,
        headers={"X-Api-Key": _api_key()},
    )


def _fetch_station_mapping() -> list[dict]:
    """Download the AWS station → lat/lng mapping (once per hour)."""
    import time

    now = time.time()
    if _station_cache["data"] is not None and (now - _station_cache["ts"]) < _CACHE_TTL_S:
        return _station_cache["data"]

    with _get_client() as client:
        resp = client.get("/api/v1/aws_data_mapping")
        resp.raise_for_status()
        stations = resp.json()
    _station_cache["data"] = stations
    _station_cache["ts"] = now
    logger.info("Fetched IMD AWS mapping: %d stations", len(stations))
    return stations


def find_nearest_station(lat: float, lng: float) -> dict | None:
    """Return the nearest AWS station dict, or None if mapping unavailable."""
    stations = _fetch_station_mapping()
    best, best_dist = None, float("inf")
    for s in stations:
        try:
            s_lat = float(s.get("Latitude", 0))
            s_lng = float(s.get("Longitude", 0))
        except (ValueError, TypeError):
            continue
        d = haversine_m(lat, lng, s_lat, s_lng)
        if d < best_dist:
            best_dist = d
            best = {**s, "_distance_m": d}
    return best


def get_station_rainfall(station_id: str) -> dict[str, Any]:
    """Fetch the latest AWS data for a station.

    Returns dict with keys: station, last_24h_mm, raw_response.
    """
    with _get_client() as client:
        resp = client.get("/api/v1/aws_data", params={"id": station_id})
        resp.raise_for_status()
        data = resp.json()

    # AWS response is a list with one entry per station ID
    if isinstance(data, list) and data:
        row = data[0]
    elif isinstance(data, dict) and "data" in data:
        row = data["data"] if isinstance(data["data"], list) else [data["data"]]
        row = row[0] if row else {}
    else:
        row = data if isinstance(data, dict) else {}

    last_24h = _parse_float(row.get("Last 24 hrs Rainfall", 0))
    return {
        "station": row.get("STATION", row.get("CALL_SIGN", station_id)),
        "last_24h_mm": last_24h,
        "raw_response": row,
    }


def fetch_zone_rainfall(lat: float, lng: float) -> dict[str, Any]:
    """Convenience: find nearest station and pull its rainfall.

    Without IMD_API_KEY, returns a deterministic simulated reading (station
    tagged SIM-*) so the pipeline still runs end-to-end.

    Returns: {"station": str, "last_24h_mm": float, "distance_m": float}
    """
    if not settings.IMD_API_KEY:
        logger.info("[IMD SIMULATED] no IMD_API_KEY — synthetic AWS reading for (%.3f, %.3f)", lat, lng)
        data = _simulate_last_24h(lat, lng)
        data["distance_m"] = 0.0
        return data

    station = find_nearest_station(lat, lng)
    if station is None:
        raise IMDError("No AWS stations available")

    sid = station.get("CALL_SIGN") or station.get("ID") or ""
    if not sid:
        raise IMDError(f"Station missing ID: {station}")

    result = get_station_rainfall(sid)
    result["distance_m"] = station.get("_distance_m", 0)
    return result


def get_daily_rainfall_timeseries(
    lat: float, lng: float, days: int = 45
) -> list[dict[str, Any]]:
    """Attempt to fetch a daily rainfall time series for the zone.

    The current IMD AWS API only exposes the latest 24h value; a daily series
    is not available via the public API at present. This returns a single-point
    placeholder when the station is available, and an empty list otherwise.

    Phase 2b replaces this with the IMD gridded time-series download
    (data.gov.in PARAKH / 0.25° daily gridded dataset).
    """
    try:
        result = fetch_zone_rainfall(lat, lng)
    except (IMDNotConfigured, IMDError):
        return []

    return [
        {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "rainfall_mm": result["last_24h_mm"],
            "station": result["station"],
        }
    ]


def _parse_float(val: Any) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return 0.0