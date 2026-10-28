
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.dependencies import get_current_user
from app.auth import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models import User
from app.schemas import (
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    data: UserRegister,
    db: Session = Depends(get_db),
):
    existing_user = db.scalar(
        select(User).where(User.email == str(data.email))
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email is already registered",
        )

    user = User(
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        email=str(data.email).lower(),
        hashed_password=hash_password(data.password),
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user",
        )

    return user


@router.post("/login", response_model=TokenResponse)
def login_user(
    data: UserLogin,
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(User.email == str(data.email).lower())
    )

    if user is None or not verify_password(
        data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user.id)

    return {
        "access_token": token,
        "token_type": "bearer",
    }

@router.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: User = Depends(get_current_user),
):
    return current_user

