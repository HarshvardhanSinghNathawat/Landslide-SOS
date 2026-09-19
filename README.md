# LandslideSOS — Assam Landslide Early Warning & SOS System

Full-stack prototype for **Smart India Hackathon 2026**: AI-powered landslide early warning
tailored to **Assam & Northeast India**. A **React + Vite** frontend is wired to a real
**FastAPI + Celery** backend that ingests rainfall/SWI data, trains an XGBoost risk model on a
Northeast landslide atlas, and dispatches SMS alerts (via an SMS provider abstraction) for SOS events.

```
landslide-sos/
├── backend/          # FastAPI backend (app, models, routers, services, tasks, scripts, alembic)
├── src/              # React frontend pages/components (live API, no mock data)
├── public/           # frontend static assets
├── start-dev.ps1     # one-command dev launcher (backend + celery + frontend)
├── docker-compose.yml
├── DEPLOY.md
└── .github/workflows/ci.yml
```

---

## Focus regions (Northeast India)

10 monitored zones across Assam and the neighbouring hill states, centred on the districts with
the highest landslide casualty rates:

| State | Zones |
|---|---|
| **Assam** | Dima Hasao - Haflong, Karbi Anglong - Hamren, Cachar - Barak Foothills, Hailakandi - Katlicherra, Karimganj - Baramukh, Golaghat - Nambor RF |
| **Meghalaya** | East Khasi Hills |
| **Mizoram** | Aizawl |
| **Manipur** | Churachandpur, Ukhrul |

The risk model is trained on a 501-event Northeast Landslide Atlas inventory
(`backend/data/inventory/landslide_atlas_ne.csv`, NRSC/ISRO-atlas style).

---

## Quickstart (one command)

From the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-dev.ps1
```

This will (on first run) create the backend virtualenv, install dependencies,
install frontend `node_modules`, then launch:

| Service     | Endpoint                        |
|-------------|---------------------------------|
| Frontend    | http://localhost:5173           |
| Backend API | http://localhost:8000/docs      |
| Celery      | worker + beat (solo pool, Win)  |

Press `Ctrl+C` in the launcher window to stop everything.

---

## Fresh-clone backend setup (manual)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

.\.venv\Scripts\python.exe -m alembic upgrade head      # apply migrations
.\.venv\Scripts\python.exe scripts\setup.py             # seed + inventory + SWI + train
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Interactive API docs: http://127.0.0.1:8000/docs

Demo logins (seeded):
- Admin: `admin@landslidesos.in` / `admin123456`
- Officer: `officer@landslidesos.in` / `officer123456`

---

## Backend overview

- **Stack:** FastAPI, SQLAlchemy 2, Pydantic v2, Alembic, Celery, XGBoost, PyJWT + bcrypt.
- **Dev DB:** SQLite (`backend/landslidesos.db`) — no Postgres needed locally.
- **Broker:** Celery uses kombu `sqlalchemy+sqlite:///celery_broker.db` (built-in transport, no Redis in dev).
- **SMS:** `SMS_PROVIDER=mock` by default (logs to console). Set `MSG91` creds + `SMS_PROVIDER=msg91` for real SMS.
- **ML:** `scripts/train_model.py` trains XGBoost on the 501-event NE atlas + ambient negatives.
- **Production:** `docker-compose.yml` spins up PostGIS + Redis + backend + celery; see `DEPLOY.md`.

## Frontend overview

- **Stack:** React 19, Vite 8, React Router 7, Tailwind 4, Leaflet maps, Recharts.
- **Live data:** every page calls the FastAPI backend through `src/api/client.js` (authenticated
  with a JWT from `/auth/login`). The Vite dev server proxies `/api` → `http://127.0.0.1:8000`.
- The GIS map is centred on Northeast India, with per-zone risk, rainfall, slope, and an
  animated SWI (soil-wetness) timeline served by the backend.

## CI

`.github/workflows/ci.yml` runs ruff lint, backend tests, and a docker build on every push.