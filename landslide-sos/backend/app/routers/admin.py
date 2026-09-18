from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.middleware.auth import DbDep, require_roles
from app.models.enums import Role
from app.models.user import User
from app.schemas.admin import UserUpdate
from app.schemas.user import UserOut
from app.services.model.trainer import latest_metrics, model_exists

router = APIRouter(prefix="/admin", tags=["admin"])

AdminUser = Annotated[User, Depends(require_roles(Role.admin))]


@router.get("/users", response_model=list[UserOut])
def list_users(db: DbDep, user: AdminUser, limit: int = 100) -> list[UserOut]:
    users = db.scalars(select(User).order_by(User.id).limit(limit)).all()
    return [UserOut.model_validate(u) for u in users]


@router.put("/users/{target_user_id}", response_model=UserUpdate)
def update_user(
    target_user_id: int,
    payload: UserUpdate,
    db: DbDep,
    user: AdminUser,
) -> dict:
    if target_user_id == user.id and payload.role is not None and payload.role != Role.admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own admin role",
        )

    target = db.get(User, target_user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.role is not None:
        target.role = payload.role
    if payload.is_active is not None:
        target.is_active = payload.is_active
    if payload.opt_in_sms is not None:
        target.opt_in_sms = payload.opt_in_sms

    db.commit()
    db.refresh(target)
    return {"id": target.id, "role": target.role, "is_active": target.is_active, "opt_in_sms": target.opt_in_sms}


@router.get("/model/performance")
def model_performance(db: DbDep, user: AdminUser) -> dict:
    run = latest_metrics(db)
    if run is None:
        return {
            "status": "no_model_trained",
            "message": "Run scripts/train_model.py to train XGBoost/RF on the landslide atlas",
        }
    return {
        "status": "trained" if model_exists() else "missing_file",
        "model_name": run["model_name"],
        "version": run["version"],
        "trained_at": run["trained_at"].isoformat(),
        "accuracy": run["accuracy"],
        "precision": run["precision"],
        "recall": run["recall"],
        "f1_score": run["f1_score"],
        "roc_auc": run["roc_auc"],
        "n_samples": run["n_samples"],
        "n_features": run["n_features"],
        "params": run["params"],
        "confusion_matrix": run["confusion_matrix"],
        "notes": run["notes"],
    }