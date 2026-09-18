from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.middleware.auth import DbDep, require_roles
from app.models.enums import Role
from app.models.user import User
from app.schemas.admin import UserCreate, UserUpdate
from app.schemas.user import UserOut
from app.services.model.trainer import latest_metrics, model_exists
from app.services.security import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])

AdminUser = Annotated[User, Depends(require_roles(Role.admin))]


@router.get("/users", response_model=list[UserOut])
def list_users(db: DbDep, user: AdminUser, limit: int = 100) -> list[UserOut]:
    users = db.scalars(select(User).order_by(User.id).limit(limit)).all()
    return [UserOut.model_validate(u) for u in users]


@router.put("/users/{target_user_id}", response_model=UserOut)
def update_user(
    target_user_id: int,
    payload: UserUpdate,
    db: DbDep,
    user: AdminUser,
) -> User:
    if target_user_id == user.id and payload.role is not None and payload.role != Role.admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own admin role",
        )

    target = db.get(User, target_user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.email is not None:
        email = str(payload.email).lower()
        if email != target.email:
            clash = db.scalar(select(User).where(User.email == email))
            if clash is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
            target.email = email
    if payload.full_name is not None:
        target.full_name = payload.full_name
    if payload.password is not None:
        target.hashed_password = hash_password(payload.password)
    if payload.role is not None:
        target.role = payload.role
    if payload.is_active is not None:
        target.is_active = payload.is_active
    if payload.opt_in_sms is not None:
        target.opt_in_sms = payload.opt_in_sms

    db.commit()
    db.refresh(target)
    return target


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: DbDep,
    user: AdminUser,
) -> User:
    email = str(payload.email).lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    new_user = User(
        email=email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        phone=payload.phone,
        role=payload.role,
        opt_in_sms=payload.opt_in_sms,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


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