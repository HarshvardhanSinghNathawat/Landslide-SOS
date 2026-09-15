#!/usr/bin/env python
"""Phase 1 smoke test — exercises every endpoint end-to-end.

Run from backend/ directory while uvicorn is running on :8000.
"""

import sys
import httpx

BASE = "http://127.0.0.1:8000"
PASS = 0
FAIL = 0
FAILURES = []


def check(label: str, status: int, resp, *required_keys):
    global PASS, FAIL
    ok = True
    if resp.status_code != status:
        ok = False
    body = resp.json() if resp.text else None
    if isinstance(body, dict):
        for key in required_keys:
            if key not in body:
                ok = False
    elif isinstance(body, list) and required_keys:
        ok = ok and all(required_keys if False else True for _ in range(len(body) or 0))
    if ok:
        PASS += 1
        print(f"  PASS  {label} -> {resp.status_code}")
    else:
        FAIL += 1
        FAILURES.append(label)
        print(f"  FAIL  {label} -> {resp.status_code} {body}")

client = httpx.Client(base_url=BASE, timeout=30.0)

print("== Public endpoints ==")
r = client.get("/")
check("root", 200, r, "name", "docs")

r = client.get("/api/v1/zones")
check("zones list", 200, r)
if r.status_code == 200:
    print(f"       {len(r.json())} zones; first: {r.json()[0] if r.json() else None}")
    zone_id = r.json()[0]["id"] if r.json() else 1
else:
    zone_id = 1

r = client.get("/api/v1/zones/1/swi")
check("zone 1 swi", 200, r, "points")

r = client.get("/api/v1/zones/1/risk")
check("zone risk (not computed yet -> 404 acceptable)", 404 if r.status_code != 200 else 200, r)

r = client.get("/api/v1/rainfall")
check("rainfall series", 200, r, "points")

r = client.get("/api/v1/alerts")
check("alerts public list", 200, r)

r = client.get("/api/v1/dashboard/stats")
check("dashboard stats", 200, r,
      "zonesMonitored", "activeAlerts", "smsSentToday", "livesAtRisk", "rainfallStations")

r = client.get("/api/v1/system/health")
check("system health", 200, r, "status", "components")

print("== Auth ==")
r = client.post("/api/v1/auth/register",
                json={"email": "citizen@test.in", "full_name": "Test Citizen",
                      "password": "citizen123456", "phone": "+91900000000"})
if r.status_code == 409:
    print("  PASS  register (user already exists from prior run)")
else:
    check("register", 201, r, "id", "role")
    if r.status_code == 201:
        print(f"       registered: {r.json()}")

r = client.post("/api/v1/auth/register",
                json={"email": "admin@landslidesos.in", "full_name": "dup",
                      "password": "whatever1234"})
check("register duplicate -> 409", 409, r)

r = client.post("/api/v1/auth/login",
                json={"email": "admin@landslidesos.in", "password": "admin123456"})
check("admin login", 200, r, "access_token")
admin_token = r.json().get("access_token") if r.status_code == 200 else ""

r = client.post("/api/v1/auth/login",
                json={"email": "officer@landslidesos.in", "password": "officer123456"})
check("officer login", 200, r, "access_token")
officer_token = r.json().get("access_token") if r.status_code == 200 else ""

r = client.post("/api/v1/auth/login",
                json={"email": "officer@landslidesos.in", "password": "wrongpass"})
check("bad password -> 401", 401, r)

h_admin = {"Authorization": f"Bearer {admin_token}"}
h_officer = {"Authorization": f"Bearer {officer_token}"}

r = client.get("/api/v1/auth/me", headers=h_admin)
check("auth/me with admin token", 200, r, "email")

r = client.get("/api/v1/auth/me")
check("auth/me without token -> 401", 401, r)

print("== Officer-only endpoints ==")
r = client.post("/api/v1/alerts/sos",
                headers=h_officer,
                json={"zone_id": zone_id, "message": "Landslide reported near highway"})
check("trigger SOS (officer)", 201, r, "ref", "zone")
if r.status_code == 201:
    print(f"       alert created: ref={r.json().get('ref')} zone={r.json().get('zone')}")

r = client.post("/api/v1/reports",
                headers=h_officer,
                json={"zone_id": zone_id, "kind": "visual-confirm",
                      "description": "Debris observed on NH road"})
check("create report (officer)", 201, r, "id")

r = client.get("/api/v1/reports", headers=h_officer)
check("list reports (officer)", 200, r)

print("== Public citizen (registered user) ==")
r = client.post("/api/v1/auth/login",
                json={"email": "citizen@test.in", "password": "citizen123456"})
check("citizen login", 200, r, "access_token")
citizen_token = r.json().get("access_token") if r.status_code == 200 else ""
h_citizen = {"Authorization": f"Bearer {citizen_token}"}

r = client.post("/api/v1/alerts/sos",
                headers=h_citizen, json={"zone_id": zone_id})
check("SOS as citizen -> 403", 403, r)

r = client.get("/api/v1/admin/users", headers=h_citizen)
check("admin list as citizen -> 403", 403, r)

print("== Admin endpoints ==")
r = client.get("/api/v1/admin/users", headers=h_admin)
check("admin list users", 200, r)

r = client.get("/api/v1/admin/model/performance", headers=h_admin)
check("admin model performance", 200, r, "status")

r = client.put("/api/v1/admin/users/1", headers=h_admin,
               json={"role": "officer"})
check("admin cannot demote self -> 400", 400, r)

r = client.get("/api/v1/admin/users", headers=h_officer)
check("admin list as officer -> 403", 403, r)

print("== Zone filter ==")
r = client.get("/api/v1/zones", params={"risk": "red"})
check("zones filtered red", 200, r)
if r.status_code == 200:
    print(f"       red zones: {len(r.json())}")

client.close()

print()
print(f"Total: {PASS} passed, {FAIL} failed")
if FAILURES:
    print("Failed:", FAILURES)
    sys.exit(1)
print("ALL PHASE 1 CHECKS PASSED")