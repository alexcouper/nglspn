from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from django.contrib.auth import authenticate
from django.http import HttpRequest
from ninja import Router

from api.auth.jwt import (
    create_access_token,
    create_refresh_token,
    create_reset_token,
    verify_token,
)
from api.auth.security import auth
from api.rate_limit import check_rate_limit
from api.schemas.auth import (
    AccessToken,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ForgotPasswordVerifyError,
    ForgotPasswordVerifyRequest,
    ForgotPasswordVerifyResponse,
    LoginRequest,
    RefreshRequest,
    ResendVerificationResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    Token,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from api.schemas.errors import Error
from api.schemas.user import UserCreate, UserResponse, UserUpdate
from api.tasks import email as email_tasks
from services import HANDLERS, REPO
from services.users.exceptions import (
    CodeExhaustedError,
    EmailAlreadyRegisteredError,
    KennitalaAlreadyRegisteredError,
    RateLimitError,
    UserNotFoundError,
)
from services.users.handler_interface import RegisterUserInput

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

logger = logging.getLogger(__name__)
router = Router()

VERIFICATION_CODE_EXPIRY_MINUTES = 15


@router.post(
    "/register",
    response={201: UserResponse, 400: Error, 429: Error},
    tags=["Authentication"],
)
def register(
    request: HttpRequest,
    payload: UserCreate,
) -> tuple[int, AbstractUser | Error]:
    rate_limit_response = check_rate_limit(request, "register", "5/m")
    if rate_limit_response:
        return rate_limit_response

    try:
        user = HANDLERS.users.register(
            RegisterUserInput(
                email=payload.email,
                password=payload.password,
                kennitala=payload.kennitala,
                first_name=payload.first_name,
                last_name=payload.last_name,
            )
        )
    except (EmailAlreadyRegisteredError, KennitalaAlreadyRegisteredError):
        return 400, Error(
            detail="Registration failed. Please check your information and try again."
        )

    # Send verification email
    try:
        verification = HANDLERS.users.create_verification_code(
            user, VERIFICATION_CODE_EXPIRY_MINUTES
        )
        email_tasks.send_verification_email.enqueue(
            str(user.id), verification.code, VERIFICATION_CODE_EXPIRY_MINUTES
        )
    except Exception:
        logger.exception("Failed to send verification email during registration")

    return 201, user


@router.post(
    "/login", response={200: Token, 401: Error, 429: Error}, tags=["Authentication"]
)
def login(
    request: HttpRequest,
    payload: LoginRequest,
) -> dict[str, Any] | tuple[int, dict[str, str]]:
    rate_limit_response = check_rate_limit(request, "login", "5/m")
    if rate_limit_response:
        return rate_limit_response

    user = authenticate(request, username=payload.email, password=payload.password)

    if not user:
        return 401, {"detail": "Invalid credentials"}

    # Send verification email if user is not verified
    if not user.is_verified:
        try:
            verification = HANDLERS.users.create_verification_code(
                user, VERIFICATION_CODE_EXPIRY_MINUTES
            )
            email_tasks.send_verification_email.enqueue(
                str(user.id), verification.code, VERIFICATION_CODE_EXPIRY_MINUTES
            )
        except RateLimitError:
            pass  # Ignore rate limit - user already has a recent code
        except Exception:
            logger.exception("Failed to send verification email during login")

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "is_verified": user.is_verified,
    }


@router.post(
    "/refresh",
    response={200: AccessToken, 401: Error},
    tags=["Authentication"],
)
def refresh_token_endpoint(
    request: HttpRequest,
    payload: RefreshRequest,
) -> dict[str, str] | tuple[int, dict[str, str]]:
    token_payload = verify_token(payload.refresh_token)

    if not token_payload:
        return 401, {"detail": "Invalid or expired refresh token"}

    if token_payload.get("type") != "refresh":
        return 401, {"detail": "Invalid token type"}

    try:
        user = REPO.users.get_by_id(UUID(token_payload["user_id"]))
    except UserNotFoundError:
        return 401, {"detail": "User not found"}

    if not user.is_active:
        return 401, {"detail": "Account is inactive"}

    access_token = create_access_token(user.id)

    return {"access_token": access_token, "token_type": "bearer"}


@router.get(
    "/me",
    response={200: UserResponse, 401: Error},
    auth=auth,
    tags=["Authentication"],
)
def get_current_user_info(request: HttpRequest) -> AbstractUser:
    return request.auth


@router.put(
    "/me",
    response={200: UserResponse, 400: Error, 401: Error},
    auth=auth,
    tags=["Authentication"],
)
def update_current_user(
    request: HttpRequest,
    payload: UserUpdate,
) -> AbstractUser:
    user = request.auth

    # Update only provided fields
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(user, field, value)

    user.save()
    return user


@router.post(
    "/verify-email",
    response={200: VerifyEmailResponse, 400: Error, 401: Error, 429: Error},
    auth=auth,
    tags=["Authentication"],
)
def verify_email(
    request: HttpRequest,
    payload: VerifyEmailRequest,
) -> VerifyEmailResponse | tuple[int, Error]:
    rate_limit_response = check_rate_limit(request, "verify_email", "5/m")
    if rate_limit_response:
        return rate_limit_response

    user = request.auth

    if user.is_verified:
        return VerifyEmailResponse(
            message="Email already verified",
            is_verified=True,
        )

    if HANDLERS.users.verify_code(user, payload.code):
        return VerifyEmailResponse(
            message="Email verified successfully",
            is_verified=True,
        )

    return 400, Error(detail="Invalid or expired verification code")


@router.post(
    "/resend-verification",
    response={200: ResendVerificationResponse, 400: Error, 401: Error},
    auth=auth,
    tags=["Authentication"],
)
def resend_verification(
    request: HttpRequest,
) -> ResendVerificationResponse | tuple[int, Error]:
    user = request.auth

    if user.is_verified:
        return 400, Error(detail="Email already verified")

    try:
        verification = HANDLERS.users.create_verification_code(
            user, VERIFICATION_CODE_EXPIRY_MINUTES
        )
        email_tasks.send_verification_email.enqueue(
            str(user.id), verification.code, VERIFICATION_CODE_EXPIRY_MINUTES
        )
        return ResendVerificationResponse(message="Verification email sent")
    except RateLimitError:
        msg = "Please wait before requesting another verification code"
        return 400, Error(detail=msg)
    except Exception:
        logger.exception("Failed to send verification email")
        return 400, Error(detail="Failed to send verification email")


RESET_CODE_EXPIRY_MINUTES = 15
FORGOT_RESET_GENERIC_MESSAGE = (
    "If an account exists with that email, we've sent a reset code"
)


@router.post(
    "/forgot-password",
    response={200: ForgotPasswordResponse},
    tags=["Authentication"],
)
def forgot_password(
    request: HttpRequest,
    payload: ForgotPasswordRequest,
) -> ForgotPasswordResponse:
    try:
        reset_code = HANDLERS.users.create_password_reset_code(
            payload.email, RESET_CODE_EXPIRY_MINUTES
        )
        if reset_code:
            email_tasks.send_password_reset_email.enqueue(
                str(reset_code.user.id),
                reset_code.code,
                RESET_CODE_EXPIRY_MINUTES,
            )
    except RateLimitError:
        pass  # Silently ignore — don't reveal rate limiting
    except Exception:
        logger.exception("Failed to process forgot password request")

    return ForgotPasswordResponse(message=FORGOT_RESET_GENERIC_MESSAGE)


@router.post(
    "/forgot-password/verify",
    response={200: ForgotPasswordVerifyResponse, 400: ForgotPasswordVerifyError},
    tags=["Authentication"],
)
def forgot_password_verify(
    request: HttpRequest,
    payload: ForgotPasswordVerifyRequest,
) -> ForgotPasswordVerifyResponse | tuple[int, ForgotPasswordVerifyError]:
    try:
        result = HANDLERS.users.verify_password_reset_code(payload.email, payload.code)
    except CodeExhaustedError:
        return 400, ForgotPasswordVerifyError(
            detail="Too many failed attempts. Please request a new code.",
            attempts_remaining=0,
        )

    if result.user is None:
        return 400, ForgotPasswordVerifyError(
            detail="Invalid or expired code",
            attempts_remaining=result.attempts_remaining,
        )

    reset_token = create_reset_token(result.user.id)
    return ForgotPasswordVerifyResponse(reset_token=reset_token)


@router.post(
    "/reset-password",
    response={200: ResetPasswordResponse, 400: Error},
    tags=["Authentication"],
)
def reset_password(
    request: HttpRequest,
    payload: ResetPasswordRequest,
) -> ResetPasswordResponse | tuple[int, Error]:
    token_payload = verify_token(payload.reset_token)

    if not token_payload:
        return 400, Error(detail="Invalid or expired reset token")

    if token_payload.get("type") != "reset":
        return 400, Error(detail="Invalid token type")

    try:
        user = REPO.users.get_by_id(UUID(token_payload["user_id"]))
    except UserNotFoundError:
        return 400, Error(detail="Invalid or expired reset token")

    HANDLERS.users.reset_password(user, payload.new_password)
    return ResetPasswordResponse(message="Password updated successfully")
