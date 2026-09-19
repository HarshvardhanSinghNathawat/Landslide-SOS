# ─── LandslideSOS Dev Launcher ────────────────────────────────────
# Starts:  Backend (port 8000) + Celery worker + Frontend (port 5173)
# Press Ctrl+C in this window to stop all three.
# ──────────────────────────────────────────────────────────────────

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$be   = Join-Path $root "backend"
$fe   = $root

# --- Pre-flight: ensure .venv exists ---
if (-not (Test-Path "$be\.venv\Scripts\python.exe")) {
    Write-Host "[setup] Creating backend virtual-env..." -ForegroundColor Cyan
    & python -m venv "$be\.venv"
    & "$be\.venv\Scripts\python.exe" -m pip install -q -r "$be\requirements.txt"
}

$py = "$be\.venv\Scripts\python.exe"

# --- Pre-flight: ensure node_modules exist ---
if (-not (Test-Path "$fe\node_modules\.package-lock.json")) {
    Write-Host "[setup] Installing frontend dependencies..." -ForegroundColor Cyan
    Push-Location $fe
    npm install --silent
    Pop-Location
}

# --- Start backend ---
$backend = Start-Process -FilePath $py `
    -ArgumentList "-m","uvicorn","app.main:app","--reload","--port","8000" `
    -WorkingDirectory $be -PassThru -WindowStyle Hidden
Write-Host "[backend] uvicorn :8000  PID=$($backend.Id)" -ForegroundColor Green

# --- Start celery worker (solo pool for Windows) ---
$worker = Start-Process -FilePath $py `
    -ArgumentList "-m","celery","-A","app.tasks.celery_app","worker","--pool=solo","--loglevel=info" `
    -WorkingDirectory $be -PassThru -WindowStyle Hidden
Write-Host "[celery]  worker  PID=$($worker.Id)" -ForegroundColor Yellow

# --- Start frontend (use npm.cmd — the npm.exe shim is blocked by Windows App Control) ---
$frontend = Start-Process "npm.cmd" -ArgumentList "run","dev" `
    -WorkingDirectory $fe -PassThru -WindowStyle Hidden
Write-Host "[frontend] vite :5173 PID=$($frontend.Id)" -ForegroundColor Cyan

Write-Host "`n  All services running.  Frontend → http://localhost:5173  Backend → http://localhost:8000/docs`n" -ForegroundColor White

# Wait for Ctrl+C
try { while ($true) { Start-Sleep 2 } }
finally {
    Write-Host "`n[stopping]..." -ForegroundColor Red
    Stop-Process -Id $backend.Id, $worker.Id, $frontend.Id -Force -ErrorAction SilentlyContinue
}
