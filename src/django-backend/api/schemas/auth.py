from ninja import Schema


class Token(Schema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105
    is_verified: bool


class AccessToken(Schema):
    access_token: str
    token_type: str = "bearer"  # noqa: S105


class LoginRequest(Schema):
    email: str
    password: str


class RefreshRequest(Schema):
    refresh_token: str


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
