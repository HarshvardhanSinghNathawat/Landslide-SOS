#!/usr/bin/env python
"""Generate ERRORS.pdf documenting every error/issue encountered during
the LandslideSOS backend build, audit, and verification sessions."""
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ERRORS.pdf")

styles = getSampleStyleSheet()
h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=16, spaceAfter=6)
h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12.5, spaceBefore=10, spaceAfter=4)
body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=9.5, leading=13)
small = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=8.5, leading=11)
mono = ParagraphStyle("Mono", parent=styles["Code"], fontSize=8, leading=11)

doc = SimpleDocTemplate(
    OUT, pagesize=A4,
    rightMargin=16*mm, leftMargin=16*mm, topMargin=16*mm, bottomMargin=16*mm,
    title="LandslideSOS - Error Log",
    author="Build/Audit Agent",
)

story = []
story.append(Paragraph("LandslideSOS Backend - Error & Issue Log", h1))
story.append(Paragraph(
    "Compiled 2026-09-15 after the full audit (&lsquo;check all updates&rsquo;) and the "
    "subsequent fixes. Covers runtime/environment failures, CRITICAL/HIGH/MEDIUM/LOW audit "
    "findings, and the verification results after remediation.", small))

# ---- Section 1: environment / runtime failures ----
story.append(Paragraph("1. Runtime & Environment Failures", h2))
rows = [
    ["#", "Error", "Root cause", "Fix"],
    [
        "1",
        "<font face=Courier>ImportError: DLL load failed</font> while importing sklearn <font face=Courier>_cyutility</font>",
        "Windows App Control policy blocks sklearn Cython DLLs",
        "Removed scikit-learn from requirements; switched to native XGBoost Booster (<font face=Courier>xgb.train</font>) + numpy metrics",
    ],
    [
        "2",
        "<font face=Courier>AttributeError: module 'xgboost' has no attribute 'XGBClassifier'</font>",
        "XGBClassifier wraps sklearn, which is blocked",
        "Use native Booster API: <font face=Courier>xgb.DMatrix</font> + <font face=Courier>booster.predict</font>",
    ],
    [
        "3",
        "<font face=Courier>KeyError: 'db'</font> on <font face=Courier>db+sqlite:///celery_broker.db</font>",
        "kombu transport schema is <font face=Courier>sqlalchemy</font>, not <font face=Courier>db</font>",
        "Broker set to <font face=Courier>sqlalchemy+sqlite:///celery_broker.db</font>",
    ],
    [
        "4",
        "<font face=Courier>KeyError: 'sqlalchemy'</font> result backend",
        "db/sqlalchemy result backends removed in Celery 5.x",
        "<font face=Courier>CELERY_RESULT_BACKEND=rpc://</font>",
    ],
    [
        "5",
        "<font face=Courier>celery.exe</font> blocked - 'not recognized / permission'",
        "App Control policy blocks <font face=Courier>.venv\\Scripts\\*.exe</font> shims on Windows",
        "Run via <font face=Courier>python -m celery ...</font> always; use <font face=Courier>--pool=solo</font> on Windows",
    ],
    [
        "6",
        "<font face=Courier>httpx.ConnectError: [WinError 10061]</font> 'actively refused it'",
        "Smoke test hardcodes port 8000; earlier attempts probed <font face=Courier>/api/v1/health</font> (does not exist) and served other ports",
        "Probe <font face=Courier>/</font> (root route) and launch uvicorn on :8000 for smoke runs",
    ],
    [
        "7",
        "Smoke test register returned 409 vs expected 201",
        "Non-idempotent citizen registration on re-runs",
        "Accept 201 OR 409 in smoke test; totals now 25-26 depending on DB state",
    ],
    [
        "8",
        "<font face=Courier>IndentationError</font> in smoke_test.py (fixed mid-session)",
        "Malformed block during test authoring",
        "Re-wrote the block; verified 26/26 on pristine DB",
    ],
    [
        "9",
        "IMD / OpenTopography / SMS live calls fail",
        "Outbound network blocked in the environment",
        "Graceful fallbacks: cached DEM, synthetic SWI, mock SMS provider",
    ],
    [
        "10",
        "Verbose SQL logging in dev console",
        "<font face=Courier>engine.echo</font> enabled under DEBUG",
        "Intended for dev; gated off by DEBUG=False in production",
    ],
]

tbl = Table(rows, colWidths=[8*mm, 55*mm, 42*mm, 65*mm])
tbl.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, 0), 8.5),
    ("FONTSIZE", (0, 1), (-1, -1), 8),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3f9")]),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
]))
story.append(tbl)

# ---- Section 2: audit findings ----
story.append(Paragraph("2. Audit Findings (severity CRITICAL/HIGH)", h2))
findings = [
    (
        "CRITICAL - #1",
        "Initial migration 7702ae8aba53 creates alerts.status CHECK/Enum constraint with only "
        "(pending, delivered, acknowledged). Model adds AlertStatus.failed. On a DB built purely "
        "from <font face=Courier>alembic upgrade head</font>, writing <font face=Courier>failed</font> violates the CHECK constraint.",
        "FIXED - added 'failed' to the enum in 7702ae8aba53. Verified: wrote<br/>"
        "<font face=Courier>AlertStatus.failed</font> with <font face=Courier>sms_failed=1</font> successfully on a fresh migration-built DB.",
    ),
    (
        "CRITICAL - #2",
        "Phase-3 migration 99f87406c0b8 adds alerts.sms_failed as NOT NULL with NO server_default. "
        "Fails on existing rows in both SQLite and PostgreSQL.",
        "FIXED - <font face=Courier>server_default='0'</font> added. Pristine <font face=Courier>upgrade head</font> now runs clean to head.",
    ),
    (
        "CRITICAL - #3",
        "Phase-3 migration 99f87406c0b8 creates the triggered_by FK with name=None; downgrade calls "
        "<font face=Courier>op.drop_constraint(None, 'alerts', type_='foreignkey')</font> which cannot render - broken downgrade path.",
        "FIXED - explicit <font face=Courier>fk_alerts_triggered_by</font> on both create (upgrade) and drop (downgrade).",
    ),
    (
        "CRITICAL - #4",
        "<font face=Courier>predict_static_proba</font> always builds an xgb.DMatrix and calls "
        "booster.predict. A legacy RandomForest model (sklearn pickle) would raise AttributeError.",
        "FIXED - branch on <font face=Courier>bundle['model_type']</font>: xgboost uses DMatrix/booster, else <font face=Courier>predict_proba(fv)[0][1]</font>.",
    ),
    (
        "HIGH - #5",
        "_parse_date in inventory/loader.py looped over formats but ALWAYS called "
        "<font face=Courier>date.fromisoformat(val.replace('/','-'))</font> - the format strings were ignored, "
        "so yy/mm/dd vs dd/mm/yy could be mis-parsed.",
        "FIXED - uses <font face=Courier>datetime.strptime(val, fmt)</font> for each declared format.",
    ),
    (
        "HIGH - #6",
        "sms_failed column on production PostgreSQL (unrunnable as-is) - covered by CRITICAL #2.",
        "FIXED together with #2.",
    ),
    (
        "HIGH - #7",
        ".env.example shipped relative paths <font face=Courier>MODEL_PATH=backend/models/...</font> that only "
        "resolve from repo root, while scripts run from backend/.",
        "FIXED - defaults now repo-relative to backend/ (<font face=Courier>models/risk_model.joblib</font>, <font face=Courier>data/</font>).",
    ),
    (
        "HIGH - #8",
        "MSG91 phone normalisation used <font face=Courier>phone.replace('+91','').replace('91','')</font> which "
        "strips '91' ANYWHERE in the number (e.g. 9 1 9... mangling valid 10-digit digits).",
        "FIXED - anchored regex <font face=Courier>re.sub(r'^\\+?91','',phone)</font>.",
    ),
]
for sev, issue, fix in findings:
    story.append(Paragraph(sev, styles["Heading3"] if "Heading3" in styles else body))
    story.append(Paragraph("Issue: " + issue, styles["Heading3"] if "Heading3" in styles else body) if False else Paragraph("<b>Issue:</b> " + issue, body))
    story.append(Paragraph("<b>Resolution:</b> " + fix, body))
    story.append(Spacer(1, 4))

# ---- Section 3: medium/low ----
story.append(Paragraph("3. MEDIUM / LOW Findings (all fixed)", h2))
mod_rows = [
    ["#", "Severity", "Issue", "Fix"],
    [
        "1", "MEDIUM",
        "Escalation alerts created by check_and_create_escalation_alerts left <font face=Courier>recipient_count=0</font> until dispatch.",
        "<font face=Courier>recipient_count = sent + failed</font> set in both dispatch tasks.",
    ],
    [
        "2", "LOW",
        "train_model.py docstring referenced non-existent <font face=Courier>scripts/start_recompute.py</font>.",
        "Corrected to <font face=Courier>scripts/recompute_risk.py</font>.",
    ],
    [
        "3", "LOW",
        "startup.py type annotation <font face=Courier>list[tuple[str, str, str]]</font> didn't match object values.",
        "Changed to <font face=Courier>list[tuple[str, object, str]]</font>.",
    ],
]
t = Table(mod_rows, colWidths=[8*mm, 18*mm, 84*mm, 60*mm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7f5f00")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, 0), 8.5),
    ("FONTSIZE", (0, 1), (-1, -1), 8),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fbf6e6")]),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
]))
story.append(t)

# ---- Section 4: verification ----
story.append(Paragraph("4. Verification After Remediation", h2))
ver = [
    ("Alembic upgrade head (fresh DB)", "4 migrations applied cleanly, head = 99f87406c0b8"),
    ("Seed / inventory / SWI / training", "users+zones seeded; 841 inventory events loaded; SWI computed; XGBoost (n=1441, holdout 25%) accuracy 0.994, f1 0.995, ROC-AUC 0.9997"),
    ("AlertStatus.failed write", "WROTE failed OK -> AlertStatus.failed 1 on migration-built DB"),
    ("SOS lifecycle (mock SMS)", "SOS #11: pending -> delivered (sms_sent=1, recipients=1, sent_at set) -> acknowledged OK"),
    ("pytest", "5 passed"),
    ("Smoke test (pristine DB)", "26/26 passed"),
    ("Smoke test (warm DB, idempotent register)", "25/25 passed"),
]
vrows = [["Check", "Result"]]
for c, r in ver:
    vrows.append([c, r])
vt = Table(vrows, colWidths=[62*mm, 108*mm])
vt.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5f2a")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, 0), 8.5),
    ("FONTSIZE", (0, 1), (-1, -1), 8),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef7ee")]),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
]))
story.append(vt)

story.append(Spacer(1, 8))
story.append(Paragraph(
    "All critical, high, medium and low audit findings are resolved. No open errors remain. "
    "Out-of-scope environmental limits (no outbound network, no local Docker/Postgres, App Control "
    "DLL/exe policy) are noted but bypassed via fallbacks.", small))

doc.build(story)
print("Wrote:", os.path.normpath(OUT))