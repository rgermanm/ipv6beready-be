from datetime import timedelta
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.config import settings
from app.models.user import (
    GoogleToken,
    PasswordChange,
    Token,
    User,
    UserCreate,
    UserPublic,
    to_public,
)
from app.repositories.users import EmailAlreadyExistsError
from app.security import (
    create_access_token,
    get_current_active_user,
    get_current_active_user_for_refresh,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def verify_recaptcha(token: str | None) -> bool:
    if not token or not settings.recaptcha_secret_key:
        return True
    try:
        response = httpx.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": settings.recaptcha_secret_key,
                "response": token,
            },
            timeout=5.0,
        )
        return bool(response.json().get("success", False))
    except Exception:
        return True


def _issue_token(user: User) -> Token:
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.email)}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
def register_user(user_in: UserCreate) -> UserPublic:
    if user_in.recaptcha_token and not verify_recaptcha(user_in.recaptcha_token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reCAPTCHA verification failed. Please try again.",
        )

    existing_user = UserService.get_user_by_email(user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists in the system.",
        )

    try:
        user = UserService.create_db_user(user_in)
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists in the system.",
        )
    return to_public(user)


@router.post("/login", response_model=Token)
def login_for_access_token(
    username: str = Form(..., description="Email address"),
    password: str = Form(..., description="Password"),
    recaptcha_token: str | None = Form(None, description="reCAPTCHA token"),
) -> Token:
    if recaptcha_token and not verify_recaptcha(recaptcha_token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reCAPTCHA verification failed. Please try again.",
        )

    user = UserService.authenticate_user(email=username, password=password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return _issue_token(user)


@router.post("/refresh", response_model=Token)
def refresh_access_token(
    current_user: User = Depends(get_current_active_user_for_refresh),
) -> Token:
    return _issue_token(current_user)


@router.get("/me", response_model=UserPublic)
def read_users_me(
    current_user: User = Depends(get_current_active_user),
) -> UserPublic:
    return to_public(current_user)


@router.put("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    password_in: PasswordChange,
    current_user: User = Depends(get_current_active_user),
) -> None:
    if not UserService.change_password(
        user=current_user,
        old_password=password_in.old_password,
        new_password=password_in.new_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password.",
        )


@router.delete("/delete-account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    current_user: User = Depends(get_current_active_user),
) -> None:
    UserService.delete_account(current_user)


@router.post("/google", response_model=Token)
def google_oauth(google_token: GoogleToken) -> Any:
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google sign-in is not configured.",
        )
    try:
        idinfo = id_token.verify_oauth2_token(
            google_token.credential,
            google_requests.Request(),
            settings.google_client_id,
        )
        google_id = idinfo.get("sub")
        email = idinfo.get("email")
        name = idinfo.get("name") or (email.split("@")[0] if email else "User")
        avatar = idinfo.get("picture")

        if not google_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Google token: missing required information",
            )

        user = UserService.create_or_get_google_user(
            google_id=google_id,
            email=email,
            name=name,
            avatar=avatar,
        )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
            )
        return _issue_token(user)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error authenticating with Google: {exc}",
        ) from exc
