from ninja import Schema


class Token(Schema):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    is_verified: bool


class AccessToken(Schema):
    access_token: str
    token_type: str = "bearer"  # noqa: S105


class LoginRequest(Schema):
    email: str
    password: str


class RefreshRequest(Schema):
    """Transition path only: the refresh token normally arrives as a cookie.

    Browsers that logged in before the cookie existed still hold the token in
    localStorage and send it here once. Remove together with the body fallback
    in the refresh endpoint.
    """

    refresh_token: str | None = None


class VerifyEmailRequest(Schema):
    code: str


class VerifyEmailResponse(Schema):
    message: str
    is_verified: bool


class ResendVerificationResponse(Schema):
    message: str


class ForgotPasswordRequest(Schema):
    email: str


class ForgotPasswordResponse(Schema):
    message: str


class ForgotPasswordVerifyRequest(Schema):
    email: str
    code: str


class ForgotPasswordVerifyResponse(Schema):
    reset_token: str


class ForgotPasswordVerifyError(Schema):
    detail: str
    attempts_remaining: int


class ResetPasswordRequest(Schema):
    reset_token: str
    new_password: str


class ResetPasswordResponse(Schema):
    message: str
