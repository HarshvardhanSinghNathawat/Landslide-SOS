"""Unit tests for the analytical corridor routing service."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.routing import (
    haversine_km,
    interpolate,
    plan_route,
    path_km,
)

GUWAHATI = [26.1445, 91.7362]
HAFLONG = [25.1648, 93.0174]
SILCHAR = [24.8333, 92.7787]

GREEN_ZONE = {
    "id": 1, "name": "Assam - Golaghat", "district": "Golaghat",
    "state": "Assam", "lat": 26.52, "lng": 93.97, "risk": "green",
}
RED_ZONE = {
    "id": 2, "name": "Assam - Dima Hasao", "district": "Dima Hasao",
    "state": "Assam", "lat": 25.65, "lng": 92.375, "risk": "red",
}
YELLOW_ZONE = {
    "id": 3, "name": "Assam - Cachar", "district": "Cachar",
    "state": "Assam", "lat": 24.88, "lng": 92.78, "risk": "yellow",
}


def test_haversine_km():
    dist = haversine_km([26.0, 91.0], [27.0, 91.0])
    assert 95.0 < dist < 125.0  # 1 degree of latitude ~ 111 km


def test_interpolate_spacing():
    path = interpolate([GUWAHATI, HAFLONG], step_km=3.0)
    assert path[0] == GUWAHATI
    assert path[-1] == HAFLONG
    assert len(path) > 30


def test_clear_route_unchanged_when_green_only():
    plan = plan_route(GUWAHATI, HAFLONG, [GREEN_ZONE])
    assert plan["direct"]["status"] == "direct"
    assert plan["recommended"]["status"] == "direct"
    assert plan["recommended"]["path"] == plan["direct"]["path"]
    assert plan["avoided_zones"] == []
    assert plan["recommended"]["km"] == plan["direct"]["km"]


def test_detour_avoids_red_blocker():
    plan = plan_route(GUWAHATI, HAFLONG, [RED_ZONE, GREEN_ZONE])
    assert plan["direct"]["status"] == "unsafe"
    assert set(z["name"] for z in plan["direct"]["danger_zones"]) == {"Assam - Dima Hasao"}
    assert plan["recommended"]["status"] == "detour"
    assert plan["recommended"]["danger_zones"] == []
    assert any(z["name"] == "Assam - Dima Hasao" for z in plan["avoided_zones"])
    assert plan["recommended"]["km"] > plan["direct"]["km"]
    # recommended corridor must keep clear of the danger buffer
    from app.services.routing import _line_min_dist
    assert _line_min_dist(plan["recommended"]["path"], [RED_ZONE["lat"], RED_ZONE["lng"]]) > 25.0


def test_yellow_is_caution_not_blocker():
    plan = plan_route(GUWAHATI, SILCHAR, [YELLOW_ZONE])
    assert plan["direct"]["status"] == "direct"
    assert plan["recommended"]["status"] == "direct"
    assert plan["avoided_zones"] == []
    assert any(z["name"] == "Assam - Cachar" for z in plan["caution_zones"])


def test_active_pending_alert_promotes_green_zone():
    plan = plan_route(
        GUWAHATI, HAFLONG,
        [GREEN_ZONE, {"id": 5, "name": "Mizoram - Aizawl", "district": "Aizawl",
                      "state": "Mizoram", "lat": 25.65, "lng": 92.375, "risk": "green"}],
        alerts=[{"zone_id": 5, "level": "orange"}],
    )
    assert plan["direct"]["status"] == "unsafe"
    assert plan["recommended"]["status"] == "detour"


def test_response_shape():
    plan = plan_route(GUWAHATI, HAFLONG, [GREEN_ZONE])
    for key in ("start", "end", "direct", "recommended", "avoided_zones", "caution_zones", "timestamp"):
        assert key in plan
    assert plan["start"] == GUWAHATI
    assert plan["end"] == HAFLONG
    for route in (plan["direct"], plan["recommended"]):
        assert route["km"] == round(path_km(route["path"]), 2)
        for pt in route["path"]:
            assert len(pt) == 2 and isinstance(pt[0], float)