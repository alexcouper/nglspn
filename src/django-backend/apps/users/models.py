import uuid
from typing import Any

from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models

from apps.projects.models import UploadStatus


class DiscussionEmailFrequency(models.TextChoices):
    IMMEDIATE = "immediate", "Every Time"
    HOURLY = "hourly", "At most every hour"
    DAILY = "daily", "At most every day"
    NEVER = "never", "Never"


class ArticleEmailFrequency(models.TextChoices):
    HOURLY = "hourly", "At most every hour"
    DAILY = "daily", "At most every day"
    WEEKLY = "weekly", "At most every week"
    NEVER = "never", "Never"


class UserManager(BaseUserManager["User"]):
    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        if not email:
            msg = "The Email field must be set"
            raise ValueError(msg)
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)

        if extra_fields.get("is_staff") is not True:
            msg = "Superuser must have is_staff=True."
            raise ValueError(msg)
        if extra_fields.get("is_superuser") is not True:
            msg = "Superuser must have is_superuser=True."
            raise ValueError(msg)

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=50, default="", blank=True)
    last_name = models.CharField(max_length=50, default="", blank=True)
    kennitala = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        null=True,
        blank=False,
    )
    info = models.TextField(default="", blank=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_system_user = models.BooleanField(default=False)
    opt_in_to_external_promotions = models.BooleanField(default=True)
    article_trust = models.BooleanField(default=True)
    discussion_email_frequency = models.CharField(
        max_length=20,
        choices=DiscussionEmailFrequency.choices,
        default=DiscussionEmailFrequency.HOURLY,
    )
    article_email_frequency = models.CharField(
        max_length=20,
        choices=ArticleEmailFrequency.choices,
        default=ArticleEmailFrequency.HOURLY,
    )
    # The current avatar. Nullable because most users never set one; SET_NULL
    # because a deleted avatar row must not take the account with it. The
    # avatar's own `user` FK is the ownership; this one is the selection.
    avatar = models.ForeignKey(
        "UserAvatar",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["kennitala"]

    class Meta:
        db_table = "users"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self) -> str:
        return self.email

    @property
    def avatar_url(self) -> str | None:
        """Public URL of the current avatar, or None.

        A `PENDING` row is never current — `complete_avatar_upload` only points
        `avatar` at a row it has just marked uploaded — but the check stays so a
        half-finished state can not render a broken image.
        """
        avatar = self.avatar
        if avatar is None or not avatar.is_uploaded:
            return None
        return avatar.url


class UserAvatar(models.Model):
    """One uploaded avatar image.

    Deliberately not a `ProjectImage`: that model's non-null project FK, gallery
    cap, cover promotion and variant pipeline all assume the image describes a
    project. An avatar shares only the lifecycle that keeps storage honest — a
    `PENDING` row reserved before the browser PUTs, marked `UPLOADED` once the
    object is confirmed, and tombstoned by a `pre_delete` receiver
    (`apps/users/signals.py`) so the orphan sweep can delete the object.

    The browser crops to a square and downsizes before upload, so there are no
    variants: one object, served as-is.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "User",
        on_delete=models.CASCADE,
        related_name="avatars",
    )
    storage_key = models.CharField(max_length=500)
    content_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField()
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    upload_status = models.CharField(
        max_length=20,
        choices=UploadStatus.choices,
        default=UploadStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "user_avatars"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Avatar for {self.user_id}: {self.storage_key}"

    @property
    def is_uploaded(self) -> bool:
        return self.upload_status == UploadStatus.UPLOADED

    @property
    def url(self) -> str:
        return f"{settings.S3_PUBLIC_URL_BASE}/{self.storage_key}"


class EmailVerificationCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="verification_codes"
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "email_verification_codes"
        indexes = [models.Index(fields=["user", "code"])]

    def __str__(self) -> str:
        return f"Verification code for {self.user.email}"


class PasswordResetCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="password_reset_codes"
    )
    code = models.CharField(max_length=6)
    attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "password_reset_codes"
        indexes = [models.Index(fields=["user", "code"])]

    def __str__(self) -> str:
        return f"Password reset code for {self.user.email}"
