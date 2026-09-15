# LandslideSOS Backend — FastAPI

India Landslide Early Warning & SOS System — the real-data backend replacing the frontend's mock data.

**Phase 1 (Foundation) ✅ + Phase 2a (Data Pipeline) ✅ COMPLETE.** This README is the session handoff document. Each phase appends its own section.

## Quickstart

```bash
cd D:\SIH\landslide-sos\backend

# 1. Create virtualenv + install (already done)
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Apply DB migrations (SQLite dev DB by default; see .env.example for Postgres+PostGIS)
.\.venv\Scripts\python.exe -m alembic upgrade head

# 3. Seed demo data (10 zones from mockData.js, 8 alerts, 45-day monsoon rainfall history, SWI readings, admin+officer users)
.\.venv\Scripts\python.exe scripts\seed_data.py

# 4. Load the landslide inventory (841 sample events, NRSC/ISRO-atlas style)
.\.venv\Scripts\python.exe scripts\load_inventory.py

# 5. Recompute Soil Water Index for all zones from rainfall history
.\.venv\Scripts\python.exe scripts\compute_swi.py

# (optional, needs network) pull real SRTM 30m terrain for each zone
# .\.venv\Scripts\python.exe scripts\update_zone_terrain.py

# 6. Run API
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

# 4. Run API
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- Interactive docs: http://127.0.0.1:8000/docs
- Root: http://127.0.0.1:8000/
- Frontend (Vite) runs on http://localhost:5173 — CORS already allows it.

### Demo accounts
| Role | Email | Password |
|---|---|---|
| admin | admin@landslidesos.in | admin123456 |
| officer | officer@landslidesos.in | officer123456 |

---

## Architecture

```
backend/
├── app/
│   ├── main.py            # FastAPI app, CORS, router mounts
│   ├── config.py          # pydantic-settings (reads .env)
│   ├── database.py        # engine, SessionLocal, Base, get_db
│   ├── models/            # SQLAlchemy ORM (8 tables)
│   ├── schemas/           # Pydantic v2 response/request models
│   ├── routers/           # auth, zones, rainfall, alerts, reports, dashboard, admin, system
│   ├── services/          # security.py (bcrypt + JWT); Phase 3 adds alerting/
│   ├── middleware/auth.py # get_current_user, require_roles, DbDep
│   └── tasks/             # (empty) Celery lands here in Phase 2b
├── alembic/               # DB migrations (env.py uses app config URL)
├── scripts/seed_data.py   # demo data loader
├── tests/smoke_test.py    # 26-endpoint end-to-end check (must pass each phase)
├── requirements.txt
├── .env.example           # copy to .env for real config
└── README.md
```

## Database (PostGIS-ready)

`Base.metadata` drives both Alembic and startup `create_all`. Switch a DB by editing `DATABASE_URL`:

```env
DATABASE_URL=sqlite:///./landslidesos.db                                    # dev
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/landslidesos          # prod
```

> **PostGIS strategy:** schema today stores `lat`/`lng` floats + `geom_wkt` WKT text for
> cross-DB dev. On Postgres, Phase 2b migrates `geom_wkt` → GeoAlchemy2
> `Geometry(geometry_type="POINT", srid=4326)` columns with a PostGIS GiST index.

### Tables (all created by `alembic revision --autogenerate -m "initial schema"`)
`users`, `zones`, `alerts`, `rainfall_readings`, `swi_readings`, `risk_scores`, `reports`, `landslide_events`

Key fields matching the frontend mock contract (`src/data/mockData.js`):
- `zones`: `name, lat, lng, slope, aspect, elevation, lithology, risk_level, risk_probability, rainfall_current_mm, swi_current` → exposed as `risk`, `rainfall`, `swi`
- `alerts`: `level, kind, status, sms_sent, recipient_count` → exposed as `type`, `sms`, `recipients`, `ref` (`ALS-{1000+id}`)
- `rainfall_readings`: `zone_id, timestamp, observed_mm, forecast_mm` (unique per zone+timestamp)
- `swi_readings`: `zone_id, timestamp, computed_swi, satellite_swi`
- `landslide_events`: training labels for Phase 2b (empty until inventory loader runs)

## API Reference (all under `/api/v1`)

### Auth
| Method | Path | Auth | Body / Response |
|---|---|---|---|
| POST | `/auth/register` | public | {email, full_name, password, phone?, opt_in_sms?} → UserOut (201, role=public) |
| POST | `/auth/login` | public | {email, password} → {access_token, user} (JWT, 8h expiry) |
| GET | `/auth/me` | any bearer | → UserOut |

### Zones
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/zones?risk=red` | public | ordered by severity (red→green) then rainfall; `risk` filter optional |
| GET | `/zones/{id}/swi` | public | SWI timeline; `risk` derived from SWI thresholds (0.45/0.32/0.22) |
| GET | `/zones/{id}/risk` | public | latest RiskScore; 404 until Phase 2b trains the model |

### Rainfall
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/rainfall?zone_id=&hours=24` | public | hourly buckets `{time, value, forecast}` |

### Alerts
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/alerts?limit=50` | public | newest first; `ref` = `ALS-{1000+id}` |
| POST | `/alerts/sos` | officer/admin | creates Alert; **Phase 3** wires MSG91/web-push |

### Reports (two-way field reporting)
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/reports` | officer/admin | list newest first |
| POST | `/reports` | any logged-in | {zone_id, kind, description} |

### Dashboard & System
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/dashboard/stats` | public | zonesMonitored, activeAlerts, smsSentToday, livesAtRisk, rainfallStations, modelAccuracy (None until 2b) |
| GET | `/system/health` | public | db status + component readiness (Rainfall API/DEM/ML/SMS/Push/GIS) |

### Admin (admin role only)
| Method | Path | Notes |
|---|---|---|
| GET | `/admin/users?limit=100` | list all users |
| PUT | `/admin/users/{id}` | update role/is_active/opt_in_sms (can't demote self) |
| GET | `/admin/model/performance` | placeholder until Phase 2b |

## RBAC
`app/middleware/auth.py` — `require_roles(Role.admin, ...)` returns `403` for unauthorized roles; `401` for missing/invalid tokens. Rules enforced:
- SOS trigger → officer/admin only
- Reports list → officer/admin; create → any authenticated user
- `/admin/*` → admin only; admin cannot demote or deactivate self

## Configuration (`.env`)
See `.env.example`. Notable:
- `SECRET_KEY` — change in prod (JWT signing)
- `SMS_PROVIDER=mock` — Phase 3 wires MSG91
- `IMD_API_KEY` — rainfall ingest active only when set (needs api.imd.gov.in account + server IP whitelisting)
- `OPENTOPOGRAPHY_API_KEY` — optional; boosts DEM rate-limits (else unauthenticated, cached)
- `DATA_DIR` — where DEM tiles + inventory CSV live (default `backend/data/`)
- `AUTO_CREATE_TABLES=true` — dev-only convenience; set `false` in prod (use Alembic)

## Phase 2a — Data Pipeline (this section)

### IMD Rainfall client — `app/services/rainfall/imd_client.py`
Uses IMD's real API `api.imd.gov.in/api/v1/aws_data` (+ station mapping). Finds the nearest AWS
station to each zone and pulls latest 24h rainfall. `IMD_API_KEY` must be set and the **server IP
whitelisted** at api.imd.gov.in; otherwise ingest stays off and the API falls back to DB/seed data.
> Gridded daily time series isn't exposed by the public gateway — Phase 2b swaps in the IMD 0.25°
> gridded dataset (data.gov.in PARAKH) via a scheduled download instead of AWS-only 24h snapshots.

### Terrain (SRTM 30m) — `app/services/dem/opentopography.py` + `scripts/update_zone_terrain.py`
Downloads `SRTMGL1` (~30 m) ASCII grids from OpenTopography around each zone, derives
`elevation`, `slope`, `aspect` with numpy gradients, caches tiles in `data/dem/`, and persists
`geom_wkt` (WGS84 point). `scripts/update_zone_terrain.py [--zone-id N]` updates all zones;
subsequent runs are offline via cache. On network failure it logs a warning and keeps existing values.

### Computed SWI (3-tank model) — `app/services/swi/engine.py` + `scripts/compute_swi.py`
Daily rainfall → cascading surface→root→deep tank model (k₁0.6/k₂0.3/k₃0.08, caps 50/120/300 mm,
link fractions 0.5/0.7) → normalised SWI ∈ [0,1]. Risk mapping (shared with zones router):
`SWI ≥ 0.45 green / ≥ 0.32 yellow / ≥ 0.22 orange / else red`. Engine upserts one `SWIReading`
per day and refreshes `Zone.swi_current`. The seed ships **45 days of monsoon-style rainfall
history** so out-of-the-box SWI values are meaningful (e.g. Wayanad ≈ 0.45).

`compute_swi.py [--days 45]` recomputes every zone; this is the hook Phase 2b's Celery job calls.

### Landslide inventory — `app/services/inventory/loader.py` + `scripts/load_inventory.py`
Loads ISRO/NRSC-style Landslide Atlas CSVs (`latitude, longitude, state, district,
event_date, area_ha, severity, trigger`) into `landslide_events`, idempotently by
(lat, lng, event_date). Ships with **841 sample events** (`data/inventory/landslide_atlas_sample.csv`)
clustered around the 10 zones, 1998-2022 — training labels placeholder for Phase 2b.
Drop the real ~80k-row NRSC extraction (with `geometry`) in the same format when available.

```bash
python scripts/load_inventory.py --csv data/inventory/landslide_atlas_sample.csv --source "NRSC-ISRO Landslide Atlas 2023 (sample)"
```

### Schema change (migration `c85d9a255d2e`)
- `zones.geom_wkt` (Text) — WGS84 point WKT (SQLite-safe; PostGIS `geometry` column for prod)
- `landslide_events.geom_wkt` (Text)

### Verification (Phase 2a exit)
- `pytest tests/test_swi_engine.py` → 5 passed (aggregation, boundedness, response, decay, thresholds)
- Server up + `tests/smoke_test.py` → 26 passed; zones now return **real computed `swi`**
  (e.g. `Kerala - Wayanad swi: 0.4470`), `/system/health` lists IMD/DEM/SWI/Inventory components
- `/system/health` "Landslide Inventory: operational (841 events)"

## Phase 2b — Risk Model + Scheduled Scoring (this section)

The inventory-trained model replaces mock zone risk with **real ML predictions**.

### Training — `app/services/model/features.py` + `trainer.py` + `scripts/train_model.py`
- **Features (7):** `slope_deg, elevation_m, aspect_sin, aspect_cos, lithology_ordinal,
  distance_km, severity` — computed per zone from SRTM terrain + atlas events.
- **Dataset:** the 841 atlas events (positive, severity-weighted) + 60 deterministic
  ambient points per zone (negative). Class ratio ~58/42.
- **Learner:** **native XGBoost Booster** (`xgb.train`, `binary:logistic`) — deliberately
  avoids the sklearn `XGBClassifier` wrapper and scikit-learn itself, because strict Windows
  App Control policies block sklearn's compiled `_cyutility` DLLs. Metrics
  (accuracy/precision/recall/f1/roc_auc/confusion matrix) are computed in **pure numpy**
  (`_stratified_split` + `_evaluate`). The RandomForest path stays optional (needs sklearn).
- Persists `models/risk_model.joblib` + `models/risk_model.json`, and records a `ModelRun`
  row served by `/admin/model/performance`.
- Fused per-zone score: `clamp(0.75 * static_model_prob + 0.25 * swi_current, 0.005, 0.995)`;
  level: `≥0.60 red / ≥0.45 orange / ≥0.30 yellow / else green`.

```bash
python scripts/train_model.py                    # xgboost (default)
python scripts/recompute_risk.py                 # one-shot per-zone rescore
```

### Celery scheduler — `app/tasks/`
- `celery_app.py` overrides `beat_schedule`: `risk.recompute_all` every 30 min,
  `rainfall.ingest_imd` hourly. Tasks use `@shared_task` and are imported at the bottom of
  the app module (no circular imports). SQLite transport — **no Redis**.
- **Windows note:** the worker must run with `--pool=solo`:

```bash
.\.venv\Scripts\celery.exe -A app.tasks.celery_app worker --pool=solo -l info
.\.venv\Scripts\celery.exe -A app.tasks.celery_app beat -l info      # second terminal
```

### Endpoints (Phase 2b)
- `GET /admin/model/performance` → `{status, accuracy, f1_score, roc_auc, confusion_matrix, ...}`
- `/dashboard/stats.modelAccuracy` un-None once trained
- `/zones/{id}/risk` now returns `probability`, `level`, `computed_at`, `model_version`
- `/zones?risk=red|orange|yellow|green` filters on real fused scores (from `RiskScore`)
- `/system/health` "ML Prediction Model" + "Risk Scheduler (Celery)" statuses

### Verification (Phase 2b exit)
- `pytest tests` → 5 passed; `tests/smoke_test.py` → 25-26 passed, 0 failed (register check is idempotent — accepts 201 or 409)
- Rang on a **pristine DB** (drop → migrate → seed → load_inventory → compute_swi → train):
  XGBoost v2026.09.15, n=1441, accuracy=0.994, f1=0.995, roc_auc=0.9997 (holdout 25%)
- `/admin/model/performance` returns trained metrics; every zone has `RiskScore` rows;
  the Celery worker (solo pool) registers `risk.recompute_all` + `rainfall.ingest_imd`.

```bash
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000   # terminal 1
.\.venv\Scripts\python.exe tests\smoke_test.py                    # terminal 2
```
Expected: `26 passed, 0 failed — ALL PHASE 1 CHECKS PASSED` (verified 2026-09-15).

## Phase 3 — Alerts → SMS (this section)

### SMS provider abstraction — `app/services/sms/__init__.py`
`send_sms(phone, message)` dispatches through the configured `SMS_PROVIDER`:
- **`mock`** (default) — logs to console, returns `SmsResult(ok=True)`; no network.
- **`msg91`** — MSG91 flow API (`POST https://api.msg91.com/api/v5/flow`), TRAI DLT compliant.
  Uses `authkey` header + `flow_id` template; `SmsResult.external_id = request_id` on success.
- `Fast2SMS` slot reserved, same interface.
Swap providers via `.env` — **no code change**.

### Config (`.env`)
```env
SMS_PROVIDER=mock            # mock | msg91
MSG91_AUTH_KEY=              # from msg91 dashboard
MSG91_SENDER_ID=LSLSOS
MSG91_TEMPLATE_ID=           # DLT-approved flow template ID
SMS_MAX_PER_ZONE_PER_HOUR=3  # rate limit
SMS_RECIPIENT_LIMIT=200
```

### Alert lifecycle — `app/models/alert.py`, `app/routers/alerts.py`
- `status`: `pending → delivered | failed`, then `acknowledged` (PATCH endpoint).
- New columns (migration `99f87406c0b8`): `triggered_by` (user FK), `sms_failed`, `sent_at`;
  `AlertStatus.failed` added to enum.
- `recipients` resolved at creation = users with `opt_in_sms=True` AND `phone` set.
- `POST /alerts/sos` (officer/admin) creates an Alert (status `pending`) then queues
  `alert.dispatch_sms_batch` (Celery). If the broker is down, **falls back to synchronous
  dispatch** so SMS still sends.
- `PATCH /alerts/{id}/acknowledge` → sets `acknowledged_at` + status `acknowledged`.
- `list_alerts` fixed to a single JOIN (was N+1 before).

### Auto-alerting on risk escalation — `app/tasks/alert_tasks.py`
`risk.recompute_all` (30-min beat) now calls `check_and_create_escalation_alerts` after scoring.
When a zone escalates (level strictly higher than its previous `RiskScore`, or first-ever score),
an Alert is auto-created and `alert.dispatch_sms` is queued. No alert when level stays flat/drops.

### Celery tasks
- `alert.dispatch_sms` — generic: loads Alert, resolves opted-in recipients, sends, tracks sent/failed.
- `alert.dispatch_sms_batch` — payload carries pre-resolved phone list + message.
- These join `risk.recompute_all` and `rainfall.ingest_imd` in the worker's task registry.

### Verification (Phase 3 exit)
- `pytest tests` → 5 passed; `tests/smoke_test.py` → 26 passed, 0 failed
  (`AlertOut` now carries `sms_failed`; `PATCH /alerts/{id}/acknowledge` added).
- SOS triggers: alert returns `status=pending`, then transitions to `delivered`
  (mock provider logs the message to server console).
- First-ever risk scoring of a zone auto-creates its first Alert (escalation from nothing).

---

## Phase 4 — Production (this section)

### Containerization — `backend/Dockerfile` + `docker-compose.yml`
Multi-stage Dockerfile: Python 3.12-slim base, installs `libpq-dev` for psycopg2,
runs as non-root `app` user. Production stage uses **Gunicorn + Uvicorn** (4 workers).

`docker-compose.yml` orchestrates 5 services:
| Service | Image | Purpose |
|---------|-------|---------|
| `postgres` | `postgis/postgis:16-3.4` | Primary database with PostGIS |
| `redis` | `redis:7-alpine` | Celery broker + result backend |
| `backend` | Custom build | FastAPI API server (port 8000) |
| `celery-worker` | Same build | Task execution (SMS, risk scoring) |
| `celery-beat` | Same build | Scheduled tasks (risk 30min, rainfall 60min) |

All services have health checks; backend/worker depend on Postgres + Redis healthy.
Volumes persist `pgdata`, `backend-data`, `backend-models`.

### Production config hardening — `app/startup.py`
On startup with `ENVIRONMENT=production`, validates:
- `SECRET_KEY` is not the dev default (≥32 chars random)
- `AUTO_CREATE_TABLES=False` (use `alembic upgrade head`)
- `DEBUG=False`
Exits immediately with a clear error if any check fails.

### Structured logging — `app/middleware/logging.py`
`RequestLoggingMiddleware` logs every request with method, path, status code,
duration (ms), and a generated `X-Request-ID` (returned in the response header).
Logs go to stdout (JSON-compatible for Docker log collectors).

### CI/CD — `.github/workflows/ci.yml`
Three-job pipeline: **lint** (ruff check + format), **test** (pytest + seed + train + smoke test),
**docker** (build image, cache with GitHub Actions cache). Triggered on push/PR to `main`.

### Deploy docs — `DEPLOY.md`
Complete deployment guide: prerequisites, quick start (9 steps), architecture table,
env var reference, database backup/restore, Celery management, monitoring, scaling,
troubleshooting.

### Verification (Phase 4 exit)
- `pytest tests` → 5 passed; `tests/smoke_test.py` → 26 passed, 0 failed
- `docker build -t landslidesos/backend ./backend` succeeds
- `docker compose config` validates (requires Docker running)
- Production startup validation catches insecure defaults
- Every request returns `X-Request-ID` header

---

## Roadmap (session-by-session)

| Session | Phase | Deliverable | Exit check |
|---|---|---|---|
| 1 ✅ | **P1 Foundation** | FastAPI + migrations + models + JWT/RBAC + CRUD | smoke_test 26/26 (this doc section) |
| 2 ✅ | **P2a Data pipeline** | IMD client, SRTM→slope, computed-SWI engine, ISRO inventory loader | SWI computed per zone, 841 atlas events loaded, geom_wkt persisted |
| 3 ✅ | **P2b Model** | XGBoost on atlas, risk-scoring API, Celery 30-min recompute | smoke 26/26, `/admin/model/performance` trained, all zones have fused risk |
| 4 ✅ | **P3 Alerts** | MSG91 + mock provider, SOS→SMS, auto-escalation alerts, acknowledge | smoke 26/26, mock SMS logged, alert lifecycle (pending→delivered→acknowledged) |
| 5 ✅ | **P4 Production** | Docker + compose, CI/CD, logging/monitoring, deploy docs | smoke 26/26, Dockerfile multi-stage, startup validation, X-Request-ID, DEPLOY.md |

## Tracked technical notes
- IMD API requires **IP whitelisting** — register the deploy server's IP.
- MSG91 live SMS needs TRAI **DLT** (PE ID + Sender ID + templates); swap via `SMS_PROVIDER` — no code change.
- PostGIS: `geom_wkt` (WKT text) is the SQLite-safe geospatial carrier today. On Postgres,
  Phase 2b replaces it with GeoAlchemy2 `Geometry(geometry_type="POINT", srid=4326)` columns
  and PostGIS index, via a Postgres-only Alembic migration.
- `update_zone_terrain.py` needs outbound HTTPS (OpenTopography); blocked networks fall back
  to the seed/mock terrain values gracefully.
- IMD's public gateway exposes AWS 24h rainfall, not a gridded daily series — the Phase 2b
  ingest job should pull the IMD 0.25° daily gridded dataset (PARAKH) for the SWI engine.