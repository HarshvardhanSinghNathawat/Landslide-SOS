from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.middleware.auth import CurrentUser, DbDep
from app.models.enums import Role
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, Token
from app.schemas.user import UserOut
from app.services.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbDep) -> User:
    email = str(payload.email).lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        phone=payload.phone,
        opt_in_sms=payload.opt_in_sms,
        role=Role.public,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: DbDep) -> Token:
    email = str(payload.email).lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    token = create_access_token(user.id, user.role.value)
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user