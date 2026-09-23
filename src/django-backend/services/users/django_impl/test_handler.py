from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.projects.models import UploadStatus
from apps.users.models import UserAvatar
from services.images.exceptions import (
    FileTooLargeError,
    UnsupportedContentTypeError,
    UploadNotCompletedError,
)
from services.images.handler_interface import MAX_AVATAR_FILE_SIZE, FileMeta
from services.users.django_impl import (
    VERIFICATION_COOLDOWN_SECONDS,
    DjangoUserHandler,
    generate_verification_code,
)
from services.users.exceptions import (
    EmailAlreadyRegisteredError,
    KennitalaAlreadyRegisteredError,
    RateLimitError,
)
from services.users.handler_interface import RegisterUserInput
from tests.factories import (
    EmailVerificationCodeFactory,
    UserAvatarFactory,
    UserFactory,
    give_avatar,
)

handler = DjangoUserHandler()


class TestGenerateVerificationCode:
    def test_generates_6_digit_code(self):
        code = generate_verification_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_generates_different_codes(self):
        codes = {generate_verification_code() for _ in range(100)}
        assert len(codes) > 1


@pytest.mark.django_db
class TestRegister:
    def test_creates_user_with_correct_fields(self):
        data = RegisterUserInput(
            email="new@example.com",
            password="securepass123",
            kennitala="1234567890",
            first_name="Jane",
            last_name="Doe",
        )

        user = handler.register(data)

        assert user.email == "new@example.com"
        assert user.first_name == "Jane"
        assert user.last_name == "Doe"
        assert user.kennitala == "1234567890"
        assert user.check_password("securepass123")

    def test_defaults_email_frequencies_to_hourly(self):
        data = RegisterUserInput(
            email="notify@example.com",
            password="securepass123",
            kennitala="9876543210",
            first_name="Test",
            last_name="User",
        )

        user = handler.register(data)

        assert user.discussion_email_frequency == "hourly"
        assert user.article_email_frequency == "hourly"

    def test_raises_on_duplicate_email(self):
        UserFactory(email="taken@example.com")
        data = RegisterUserInput(
            email="taken@example.com",
            password="pass123",
            kennitala="9999999999",
            first_name="A",
            last_name="B",
        )

        with pytest.raises(EmailAlreadyRegisteredError):
            handler.register(data)

    def test_raises_on_duplicate_kennitala(self):
        UserFactory(kennitala="1111111111")
        data = RegisterUserInput(
            email="unique@example.com",
            password="pass123",
            kennitala="1111111111",
            first_name="A",
            last_name="B",
        )

        with pytest.raises(KennitalaAlreadyRegisteredError):
            handler.register(data)


@pytest.mark.django_db
class TestCreateVerificationCode:
    def test_creates_code_for_user(self):
        user = UserFactory()

        verification = handler.create_verification_code(user, expires_minutes=15)

        assert verification.user == user
        assert len(verification.code) == 6
        assert verification.code.isdigit()
        assert verification.expires_at > timezone.now()

    def test_code_expires_after_configured_minutes(self):
        user = UserFactory()
        before = timezone.now()
        verification = handler.create_verification_code(user, expires_minutes=5)
        after = timezone.now()

        expected_min = before + timedelta(minutes=5)
        expected_max = after + timedelta(minutes=5)
        assert expected_min <= verification.expires_at <= expected_max

    def test_rate_limits_requests(self):
        user = UserFactory()
        handler.create_verification_code(user, expires_minutes=15)

        with pytest.raises(RateLimitError):
            handler.create_verification_code(user, expires_minutes=15)

    def test_allows_new_code_after_cooldown(self):
        user = UserFactory()
        verification = handler.create_verification_code(user, expires_minutes=15)

        verification.created_at = timezone.now() - timedelta(
            seconds=VERIFICATION_COOLDOWN_SECONDS + 1
        )
        verification.save()

        new_verification = handler.create_verification_code(user, expires_minutes=15)
        assert new_verification.id != verification.id


@pytest.mark.django_db
class TestVerifyCode:
    def test_verifies_valid_code_and_marks_user_verified(self):
        user = UserFactory(is_verified=False)
        EmailVerificationCodeFactory(user=user, code="123456")

        result = handler.verify_code(user, "123456")

        assert result is True
        user.refresh_from_db()
        assert user.is_verified is True

    def test_rejects_wrong_code(self):
        user = UserFactory(is_verified=False)
        EmailVerificationCodeFactory(user=user, code="123456")

        result = handler.verify_code(user, "000000")

        assert result is False
        user.refresh_from_db()
        assert user.is_verified is False

    def test_verifies_valid_code(self):
        user = UserFactory(is_verified=False)
        verification = EmailVerificationCodeFactory(user=user, code="123456")

        result = handler.verify_code(user, "123456")

        assert result is True
        user.refresh_from_db()
        verification.refresh_from_db()
        assert user.is_verified is True
        assert verification.used_at is not None

    def test_rejects_invalid_code(self):
        user = UserFactory(is_verified=False)
        EmailVerificationCodeFactory(user=user, code="123456")

        result = handler.verify_code(user, "654321")

        assert result is False
        user.refresh_from_db()
        assert user.is_verified is False

    def test_rejects_expired_code(self):
        user = UserFactory(is_verified=False)
        EmailVerificationCodeFactory(
            user=user,
            code="123456",
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        result = handler.verify_code(user, "123456")

        assert result is False
        user.refresh_from_db()
        assert user.is_verified is False

    def test_rejects_already_used_code(self):
        user = UserFactory(is_verified=False)
        EmailVerificationCodeFactory(
            user=user,
            code="123456",
            used_at=timezone.now(),
        )

        result = handler.verify_code(user, "123456")

        assert result is False
        user.refresh_from_db()
        assert user.is_verified is False


# ----------------------------------------------------------------------
# Avatar lifecycle
# ----------------------------------------------------------------------

STORAGE = "services.users.django_impl.handler.storage_service"

PRESIGNED = {
    "upload_url": "https://bucket.example/put",
    "method": "PUT",
    "headers": {"Content-Type": "image/jpeg"},
}


def jpeg_meta(size: int = 300_000) -> FileMeta:
    return FileMeta(filename="me.jpg", content_type="image/jpeg", file_size=size)


def pending_avatar_for(user) -> UserAvatar:
    return UserAvatarFactory(user=user, upload_status=UploadStatus.PENDING)


def assert_is_current_avatar(user, avatar: UserAvatar) -> None:
    user.refresh_from_db()
    avatar.refresh_from_db()
    assert user.avatar_id == avatar.pk
    assert avatar.upload_status == UploadStatus.UPLOADED
    assert avatar.uploaded_at is not None


def assert_row_gone(avatar: UserAvatar) -> None:
    assert not UserAvatar.objects.filter(pk=avatar.pk).exists()


@pytest.mark.django_db
class TestCreateAvatarUpload:
    def test_reserves_a_pending_row_under_the_users_prefix(self):
        user = UserFactory()

        with patch(f"{STORAGE}.generate_presigned_upload_url", return_value=PRESIGNED):
            prepared = handler.create_avatar_upload(user, jpeg_meta())

        row = UserAvatar.objects.get(pk=prepared.image.pk)
        assert row.user == user
        assert row.upload_status == UploadStatus.PENDING
        assert row.storage_key.startswith(f"avatars/{user.id}/")
        assert prepared.storage_key == row.storage_key
        assert prepared.upload_url == PRESIGNED["upload_url"]

    def test_reserving_does_not_change_the_current_avatar(self):
        user = UserFactory()
        current = give_avatar(user)

        with patch(f"{STORAGE}.generate_presigned_upload_url", return_value=PRESIGNED):
            handler.create_avatar_upload(user, jpeg_meta())

        user.refresh_from_db()
        assert user.avatar_id == current.pk

    def test_rejects_a_gif(self):
        user = UserFactory()
        meta = FileMeta(filename="a.gif", content_type="image/gif", file_size=10)

        with pytest.raises(UnsupportedContentTypeError):
            handler.create_avatar_upload(user, meta)
        assert not UserAvatar.objects.exists()

    def test_rejects_a_file_over_two_megabytes(self):
        user = UserFactory()

        with pytest.raises(FileTooLargeError):
            handler.create_avatar_upload(user, jpeg_meta(MAX_AVATAR_FILE_SIZE + 1))
        assert not UserAvatar.objects.exists()


@pytest.mark.django_db
class TestCompleteAvatarUpload:
    def test_first_avatar_becomes_current(self):
        user = UserFactory()
        avatar = pending_avatar_for(user)

        with patch(f"{STORAGE}.object_exists", return_value=True):
            handler.complete_avatar_upload(user, avatar, width=512, height=512)

        assert_is_current_avatar(user, avatar)
        assert user.avatar_url.endswith(avatar.storage_key)

    def test_replacement_retires_the_previous_row(self):
        user = UserFactory()
        previous = give_avatar(user)
        replacement = pending_avatar_for(user)

        with patch(f"{STORAGE}.object_exists", return_value=True):
            handler.complete_avatar_upload(user, replacement, width=512, height=512)

        assert_is_current_avatar(user, replacement)
        assert_row_gone(previous)

    def test_missing_object_raises_and_changes_nothing(self):
        user = UserFactory()
        previous = give_avatar(user)
        replacement = pending_avatar_for(user)

        with (
            patch(f"{STORAGE}.object_exists", return_value=False),
            pytest.raises(UploadNotCompletedError),
        ):
            handler.complete_avatar_upload(user, replacement, width=512, height=512)

        user.refresh_from_db()
        replacement.refresh_from_db()
        assert user.avatar_id == previous.pk
        assert replacement.upload_status == UploadStatus.PENDING


@pytest.mark.django_db
class TestRemoveAvatar:
    def test_clears_the_avatar_and_deletes_its_row(self):
        user = UserFactory()
        avatar = give_avatar(user)

        handler.remove_avatar(user)

        user.refresh_from_db()
        assert user.avatar_id is None
        assert user.avatar_url is None
        assert_row_gone(avatar)

    def test_is_a_no_op_without_an_avatar(self):
        user = UserFactory()

        handler.remove_avatar(user)

        user.refresh_from_db()
        assert user.avatar_id is None


@pytest.mark.django_db
class TestAvatarUrl:
    def test_pending_row_is_never_served(self):
        user = UserFactory()
        pending = pending_avatar_for(user)
        user.avatar = pending
        user.save(update_fields=["avatar"])

        assert user.avatar_url is None
