from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.middleware.auth import CurrentUser, DbDep, require_roles
from app.models.enums import ReportStatus, Role
from app.models.report import Report
from app.models.user import User
from app.models.zone import Zone
from app.schemas.report import ReportCreate, ReportOut

router = APIRouter(prefix="/reports", tags=["reports"])

OfficerUser = Annotated[User, Depends(require_roles(Role.admin, Role.officer))]


def _to_report_out(report: Report, db: DbDep) -> ReportOut:
    zone = db.get(Zone, report.zone_id)
    user = db.get(User, report.user_id)
    return ReportOut(
        id=report.id,
        zone_id=report.zone_id,
        zone=zone.name if zone else None,
        reporter=user.email if user else None,
        kind=report.kind,
        description=report.description,
        status=report.status,
        created_at=report.created_at,
    )


@router.get("", response_model=list[ReportOut])
def list_reports(
    db: DbDep,
    limit: int = 50,
    user: OfficerUser = None,
) -> list[ReportOut]:
    del user
    stmt = select(Report).order_by(Report.created_at.desc()).limit(limit)
    reports = db.scalars(stmt).all()
    return [_to_report_out(r, db) for r in reports]


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreate,
    db: DbDep,
    user: CurrentUser,
) -> ReportOut:
    zone = db.get(Zone, payload.zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")

    report = Report(
        zone_id=payload.zone_id,
        user_id=user.id,
        kind=payload.kind,
        description=payload.description,
        status=ReportStatus.submitted,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return _to_report_out(report, db)