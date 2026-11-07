
import jwt
from jwt.exceptions import InvalidTokenError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.auth import (
    create_access_token,
    create_password_reset_token,
    hash_password,
    verify_password,
    verify_password_reset_token,
)
from app.database import get_db
from app.email_service import send_password_reset_email
from app.models import User
from app.rate_limiter import RateLimiter
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    MessageResponse,
    ResetPasswordRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

login_rate_limiter = RateLimiter(times=5, seconds=60)
forgot_rate_limiter = RateLimiter(times=3, seconds=600)
reset_rate_limiter = RateLimiter(times=5, seconds=300)
register_rate_limiter = RateLimiter(times=5, seconds=60)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_rate_limiter)],
)
def register_user(
    data: UserRegister,
    db: Session = Depends(get_db),
):
    email = str(data.email).lower()

    existing_user = db.scalar(
        select(User).where(User.email == email)
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email is already registered",
        )

    user = User(
    name=data.name,
    email=email,
    hashed_password=hash_password(data.password),
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email is already registered",
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user",
        )

    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(login_rate_limiter)],
)
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


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    dependencies=[Depends(forgot_rate_limiter)],
)
def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    email = str(data.email).lower()
    user = db.scalar(
        select(User).where(User.email == email)
    )

    if user is None:
        return {
            "message": "If this email is registered, password reset instructions have been sent.",
            "reset_token": None,
        }

    reset_token = create_password_reset_token(user.id, user.hashed_password)

    # Dispatch email sending in the background without blocking the HTTP response
    background_tasks.add_task(send_password_reset_email, email, reset_token)

    return {
        "message": "If this email is registered, password reset instructions have been sent.",
        "reset_token": reset_token,
    }


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    dependencies=[Depends(reset_rate_limiter)],
)
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    try:
        unverified_payload = jwt.decode(
            data.token,
            options={"verify_signature": False},
        )
        user_id = int(unverified_payload["sub"])
    except (InvalidTokenError, ValueError, TypeError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    try:
        verify_password_reset_token(data.token, user.hashed_password)
    except (InvalidTokenError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user.hashed_password = hash_password(data.new_password)
    db.commit()

    return {"message": "Password has been reset successfully. You can now log in."}

