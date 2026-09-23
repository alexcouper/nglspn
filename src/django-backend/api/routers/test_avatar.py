"""The three avatar endpoints under /api/auth/me/avatar.

The lifecycle itself is tested against the handler in
services/users/django_impl/test_handler.py; these pin the HTTP contract —
status codes, who may complete what, and the shape of the responses.
"""

import json
import uuid
from unittest.mock import patch

from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_entries,
    is_,
    none,
)

from apps.projects.models import UploadStatus
from apps.users.models import UserAvatar
from services.images.handler_interface import MAX_AVATAR_FILE_SIZE
from tests.factories import UserAvatarFactory, give_avatar

STORAGE = "services.users.django_impl.handler.storage_service"

PRESIGNED = {
    "upload_url": "https://bucket.example/put",
    "method": "PUT",
    "headers": {"Content-Type": "image/jpeg", "x-amz-acl": "public-read"},
}


def upload_request(**overrides) -> dict:
    return {
        "filename": "me.jpg",
        "content_type": "image/jpeg",
        "file_size": 300_000,
        **overrides,
    }


def post_json(client, url, payload, headers):
    return client.post(
        url, data=json.dumps(payload), content_type="application/json", **headers
    )


def reserve(client, headers, **overrides):
    with patch(f"{STORAGE}.generate_presigned_upload_url", return_value=PRESIGNED):
        return post_json(
            client,
            "/api/auth/me/avatar/upload-url",
            upload_request(**overrides),
            headers,
        )


def complete(client, headers, image_id, *, object_exists: bool = True):
    with patch(f"{STORAGE}.object_exists", return_value=object_exists):
        return post_json(
            client,
            f"/api/auth/me/avatar/{image_id}/complete",
            {"width": 512, "height": 512},
            headers,
        )


class TestReserveAvatarUpload:
    def test_returns_a_presigned_put_and_a_pending_row(
        self, client, user, auth_headers
    ) -> None:
        response = reserve(client, auth_headers)

        assert_that(response.status_code, equal_to(200))
        body = response.json()
        assert_that(
            body,
            has_entries(upload_url=PRESIGNED["upload_url"], method="PUT"),
        )
        row = UserAvatar.objects.get(pk=body["image_id"])
        assert_that(row.upload_status, equal_to(UploadStatus.PENDING))
        assert_that(row.user, equal_to(user))
        assert_that(body["storage_key"], contains_string(f"avatars/{user.id}/"))

    def test_reserving_leaves_the_current_avatar_alone(
        self, client, user, auth_headers
    ) -> None:
        current = give_avatar(user)

        reserve(client, auth_headers)

        user.refresh_from_db()
        assert_that(user.avatar_id, equal_to(current.pk))

    def test_rejects_a_gif(self, client, user, auth_headers) -> None:
        response = reserve(client, auth_headers, content_type="image/gif")

        assert_that(response.status_code, equal_to(400))
        assert_that(UserAvatar.objects.exists(), is_(False))

    def test_rejects_a_file_over_the_ceiling(self, client, user, auth_headers) -> None:
        response = reserve(client, auth_headers, file_size=MAX_AVATAR_FILE_SIZE + 1)

        assert_that(response.status_code, equal_to(400))
        assert_that(UserAvatar.objects.exists(), is_(False))

    def test_requires_authentication(self, client, db) -> None:
        response = post_json(
            client, "/api/auth/me/avatar/upload-url", upload_request(), {}
        )

        assert_that(response.status_code, equal_to(401))


class TestCompleteAvatarUpload:
    def test_completing_makes_it_the_current_avatar(
        self, client, user, auth_headers
    ) -> None:
        image_id = reserve(client, auth_headers).json()["image_id"]

        response = complete(client, auth_headers, image_id)

        assert_that(response.status_code, equal_to(200))
        row = UserAvatar.objects.get(pk=image_id)
        assert_that(response.json()["avatar_url"], equal_to(row.url))
        user.refresh_from_db()
        assert_that(user.avatar_id, equal_to(row.pk))

    def test_replacement_removes_the_old_row(self, client, user, auth_headers) -> None:
        old = give_avatar(user)
        image_id = reserve(client, auth_headers).json()["image_id"]

        complete(client, auth_headers, image_id)

        assert_that(UserAvatar.objects.filter(pk=old.pk).exists(), is_(False))

    def test_missing_object_is_a_400_and_changes_nothing(
        self, client, user, auth_headers
    ) -> None:
        image_id = reserve(client, auth_headers).json()["image_id"]

        response = complete(client, auth_headers, image_id, object_exists=False)

        assert_that(response.status_code, equal_to(400))
        assert_that(response.json()["detail"], contains_string("not found in storage"))
        user.refresh_from_db()
        assert_that(user.avatar_id, is_(none()))

    def test_someone_elses_reservation_is_a_404(
        self, client, user, auth_headers, other_user
    ) -> None:
        theirs = UserAvatarFactory(user=other_user, upload_status=UploadStatus.PENDING)

        response = complete(client, auth_headers, theirs.pk)

        assert_that(response.status_code, equal_to(404))

    def test_an_already_completed_row_is_a_404(
        self, client, user, auth_headers
    ) -> None:
        done = give_avatar(user)

        response = complete(client, auth_headers, done.pk)

        assert_that(response.status_code, equal_to(404))

    def test_unknown_id_is_a_404(self, client, user, auth_headers) -> None:
        response = complete(client, auth_headers, uuid.uuid4())

        assert_that(response.status_code, equal_to(404))


class TestRemoveAvatar:
    def test_clears_the_avatar(self, client, user, auth_headers) -> None:
        avatar = give_avatar(user)

        response = client.delete("/api/auth/me/avatar", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["avatar_url"], is_(none()))
        assert_that(UserAvatar.objects.filter(pk=avatar.pk).exists(), is_(False))

    def test_is_fine_without_an_avatar(self, client, user, auth_headers) -> None:
        response = client.delete("/api/auth/me/avatar", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["avatar_url"], is_(none()))

    def test_requires_authentication(self, client, db) -> None:
        response = client.delete("/api/auth/me/avatar")

        assert_that(response.status_code, equal_to(401))


class TestMeCarriesAvatarUrl:
    def test_me_reports_the_avatar(self, client, user, auth_headers) -> None:
        avatar = give_avatar(user)

        response = client.get("/api/auth/me", **auth_headers)

        assert_that(response.json()["avatar_url"], equal_to(avatar.url))

    def test_me_reports_null_without_one(self, client, user, auth_headers) -> None:
        response = client.get("/api/auth/me", **auth_headers)

        assert_that(response.json()["avatar_url"], is_(none()))
