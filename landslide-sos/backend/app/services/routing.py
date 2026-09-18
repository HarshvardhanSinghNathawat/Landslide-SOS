"""Analytical corridor routing for LandslideSOS.

Phase-2 prototype: produces risk-aware straight-line corridors with detours
around landslide-danger zones, without a road network.  Upgrade path: swap
this planner for an OSRM/Valhalla on-road router and mask blocked edges.
"""

import itertools
import math
from datetime import datetime, timezone

EARTH_RADIUS_KM = 6371.0
STEP_KM = 3.0
MAX_DETOUR_COMBOS = 64
CROSSING_PENALTY = 30.0
CAUTION_CROSSING_PENALTY = 4.0
DETOUR_FLANK_MARGIN_KM = 14.0
FAR_DETOUR_MARGIN_KM = 45.0

DANGER_BUFFER_KM: dict[str, float] = {"red": 25.0, "orange": 18.0}
CAUTION_BUFFER_KM: dict[str, float] = {"yellow": 10.0}


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _rad(deg: float) -> float:
    return deg * math.pi / 180.0


def _deg(rad: float) -> float:
    return rad * 180.0 / math.pi


def haversine_km(a: list[float], b: list[float]) -> float:
    lat1, lon1 = _rad(a[0]), _rad(a[1])
    lat2, lon2 = _rad(b[0]), _rad(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    val = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(val))


def bearing_deg(a: list[float], b: list[float]) -> float:
    lat1, lon1 = _rad(a[0]), _rad(a[1])
    lat2, lon2 = _rad(b[0]), _rad(b[1])
    dlon = lon2 - lon1
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (_deg(math.atan2(y, x)) + 360.0) % 360.0


def destination(point: list[float], bearing: float, dist_km: float) -> list[float]:
    lat1, lon1 = _rad(point[0]), _rad(point[1])
    brng = _rad(bearing)
    ang = dist_km / EARTH_RADIUS_KM
    lat2 = math.asin(
        math.sin(lat1) * math.cos(ang) + math.cos(lat1) * math.sin(ang) * math.cos(brng)
    )
    lon2 = lon1 + math.atan2(
        math.sin(brng) * math.sin(ang) * math.cos(lat1),
        math.cos(ang) - math.sin(lat1) * math.sin(lat2),
    )
    return [_deg(lat2), _deg(lon2)]


def interpolate(waypoints: list[list[float]], step_km: float = STEP_KM) -> list[list[float]]:
    if len(waypoints) < 2:
        return [list(w) for w in waypoints]
    pts: list[list[float]] = []
    for a, b in zip(waypoints, waypoints[1:]):
        d = haversine_km(a, b)
        if d < 1e-9:
            pts.append(list(a))
            continue
        steps = max(1, int(math.ceil(d / step_km)))
        brng = bearing_deg(a, b)
        if not pts:
            pts.append(list(a))
        for i in range(1, steps):
            pts.append(destination(a, brng, d * i / steps))
        pts.append(list(b))
    return pts


def path_km(path: list[list[float]]) -> float:
    return sum(haversine_km(a, b) for a, b in zip(path, path[1:]))


def _line_min_dist(path: list[list[float]], point: list[float]) -> float:
    return min(haversine_km(p, point) for p in path)


# ---------------------------------------------------------------------------
# Zone helpers
# ---------------------------------------------------------------------------

def _normalize_zone(z: dict, danger_map: dict, caution_map: dict) -> dict:
    risk = z["risk"]
    buffer = danger_map.get(risk, caution_map.get(risk, 0.0))
    return {
        "id": z["id"],
        "name": z["name"],
        "district": z.get("district"),
        "state": z.get("state"),
        "lat": z["lat"],
        "lng": z["lng"],
        "risk": risk,
        "buffer_km": buffer,
    }


def _split_blockers_and_caution(
    zones: list[dict],
    alerts: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    by_id: dict[int, dict] = {}
    for z in zones:
        normed = _normalize_zone(z, DANGER_BUFFER_KM, CAUTION_BUFFER_KM)
        by_id[normed["id"]] = normed

    for a in alerts:
        zid = a["zone_id"]
        level = a["level"]
        if zid in by_id and by_id[zid]["buffer_km"] == 0.0:
            buf = DANGER_BUFFER_KM.get(level, CAUTION_BUFFER_KM.get(level, 0.0))
            if buf > 0:
                by_id[zid]["buffer_km"] = buf
                by_id[zid]["risk"] = level

    all_z = list(by_id.values())
    blockers = [z for z in all_z if z["risk"] in DANGER_BUFFER_KM and z["buffer_km"] > 0]
    cautions = [z for z in all_z if z["risk"] in CAUTION_BUFFER_KM and z["buffer_km"] > 0]
    return all_z, blockers, cautions


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _crossed_names(zones: list[dict], path: list[list[float]]) -> list[dict]:
    return [
        {
            "id": z["id"],
            "name": z["name"],
            "risk": z["risk"],
            "district": z.get("district"),
            "state": z.get("state"),
            "lat": z["lat"],
            "lng": z["lng"],
        }
        for z in zones
        if _line_min_dist(path, [z["lat"], z["lng"]]) <= z["buffer_km"]
    ]


def _score_path(
    path: list[list[float]],
    blockers: list[dict],
    cautions: list[dict],
) -> tuple[float, list[dict], list[dict]]:
    km = path_km(path)
    crossed = _crossed_names(blockers, path)
    caut = _crossed_names(cautions, path)
    cost = km + CROSSING_PENALTY * len(crossed) + CAUTION_CROSSING_PENALTY * len(caut)
    return cost, crossed, caut


# ---------------------------------------------------------------------------
# Detour generation
# ---------------------------------------------------------------------------

def _detour_candidates(
    blockers: list[dict],
    start: list[float],
    end: list[float],
) -> list[list[list[float]]]:
    if not blockers:
        return [[start, end]]

    corridor_brng = bearing_deg(start, end)
    flank_options: list[list[list[float]]] = []
    for b in blockers:
        left = destination(
            [b["lat"], b["lng"]],
            (corridor_brng - 90.0) % 360,
            b["buffer_km"] + DETOUR_FLANK_MARGIN_KM,
        )
        right = destination(
            [b["lat"], b["lng"]],
            (corridor_brng + 90.0) % 360,
            b["buffer_km"] + DETOUR_FLANK_MARGIN_KM,
        )
        flank_options.append([left, right])

    combos: list[list[list[float]]] = []
    for i, combo in enumerate(itertools.product(*flank_options)):
        if i >= MAX_DETOUR_COMBOS:
            break
        combos.append([start, *combo, end])

    mid_lat = (start[0] + end[0]) / 2
    mid_lng = (start[1] + end[1]) / 2
    mid = [mid_lat, mid_lng]
    for side in [1, -1]:
        bow = destination(mid, side * 90, FAR_DETOUR_MARGIN_KM)
        combos.append([start, bow, end])

    return combos


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def plan_route(
    start: list[float],
    end: list[float],
    zones: list[dict],
    alerts: list[dict] | None = None,
) -> dict:
    alerts = alerts or []
    all_zones, blockers, cautions = _split_blockers_and_caution(zones, alerts)
    direct_path = interpolate([start, end])
    direct_km = path_km(direct_path)
    direct_crossed = _crossed_names(blockers, direct_path)
    direct_caut = _crossed_names(cautions, direct_path)

    if not direct_crossed:
        return {
            "start": start,
            "end": end,
            "direct": {
                "path": direct_path,
                "km": round(direct_km, 2),
                "status": "direct",
                "danger_zones": [],
            },
            "recommended": {
                "path": direct_path,
                "km": round(direct_km, 2),
                "status": "direct",
                "danger_zones": [],
            },
            "avoided_zones": [],
            "caution_zones": [
                {"id": c["id"], "name": c["name"], "risk": c["risk"],
                 "district": c["district"], "state": c["state"]}
                for c in direct_caut
            ],
            "timestamp": datetime.now(timezone.utc),
        }

    best_path = direct_path
    best_cost = float("inf")
    best_crossed: list[dict] = []
    best_caut: list[dict] = []

    for waypoints in _detour_candidates(blockers, start, end):
        path = interpolate(waypoints)
        cost, crossed, caut = _score_path(path, blockers, cautions)
        if cost < best_cost or (
            cost == best_cost and len(crossed) < len(best_crossed)
        ):
            best_cost = cost
            best_path = path
            best_crossed = crossed
            best_caut = caut

    safe_path = best_path
    safe_status = "detour"

    return {
        "start": start,
        "end": end,
        "direct": {
            "path": direct_path,
            "km": round(direct_km, 2),
            "status": "unsafe" if direct_crossed else "direct",
            "danger_zones": direct_crossed,
        },
        "recommended": {
            "path": safe_path,
            "km": round(path_km(safe_path), 2),
            "status": safe_status,
            "danger_zones": best_crossed,
        },
        "avoided_zones": [
            {"id": z["id"], "name": z["name"], "risk": z["risk"],
             "district": z["district"], "state": z["state"]}
            for z in direct_crossed
        ],
        "caution_zones": [
            {"id": c["id"], "name": c["name"], "risk": c["risk"],
             "district": c["district"], "state": c["state"]}
            for c in best_caut
        ],
        "timestamp": datetime.now(timezone.utc),
    }
