import json

import pytest
from django.utils import timezone
from hamcrest import assert_that, equal_to, has_entries, has_length

from tests.factories import (
    DiscussionFactory,
    NotificationFactory,
    ProjectFactory,
)


def _post_mark_thread_read(client, root_id, headers):
    return client.post(
        "/api/notifications/mark-thread-read",
        data=json.dumps({"root_discussion_id": str(root_id)}),
        content_type="application/json",
        **headers,
    )


@pytest.mark.django_db
class TestSummaryEndpoint:
    def test_unauthenticated_returns_401(self, client) -> None:
        response = client.get("/api/notifications/summary")
        assert_that(response.status_code, equal_to(401))

    def test_zero_unread(self, client, auth_headers) -> None:
        response = client.get("/api/notifications/summary", **auth_headers)
        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            equal_to({"has_unread": False, "unread_group_count": 0}),
        )

    def test_two_threads_returns_count(self, client, user, auth_headers) -> None:
        project = ProjectFactory()
        d1 = DiscussionFactory(project=project)
        d2 = DiscussionFactory(project=project)
        reply_d1 = DiscussionFactory(project=project, parent=d1)
        NotificationFactory(recipient=user, discussion=d1)
        NotificationFactory(recipient=user, discussion=reply_d1)
        NotificationFactory(recipient=user, discussion=d2)

        response = client.get("/api/notifications/summary", **auth_headers)

        assert_that(
            response.json(),
            equal_to({"has_unread": True, "unread_group_count": 2}),
        )


@pytest.mark.django_db
class TestGroupsEndpoint:
    def test_unauthenticated_returns_401(self, client) -> None:
        response = client.get("/api/notifications/groups")
        assert_that(response.status_code, equal_to(401))

    def test_returns_groups(self, client, user, auth_headers) -> None:
        project = ProjectFactory()
        root = DiscussionFactory(project=project)
        reply = DiscussionFactory(project=project, parent=root)
        NotificationFactory(recipient=user, discussion=root)
        NotificationFactory(recipient=user, discussion=reply)

        response = client.get("/api/notifications/groups", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        data = response.json()
        assert_that(data, has_length(1))
        assert_that(
            data[0],
            has_entries(
                root_discussion_id=str(root.id),
                unread_count=2,
                headline_kind="replied",
                latest_comment_id=str(reply.id),
            ),
        )

    def test_only_calling_users_notifications(
        self, client, user, other_user, auth_headers
    ) -> None:
        project = ProjectFactory()
        d_other = DiscussionFactory(project=project)
        NotificationFactory(recipient=other_user, discussion=d_other)
        d_mine = DiscussionFactory(project=project)
        NotificationFactory(recipient=user, discussion=d_mine)

        response = client.get("/api/notifications/groups", **auth_headers)

        data = response.json()
        assert_that(data, has_length(1))
        assert_that(data[0]["root_discussion_id"], equal_to(str(d_mine.id)))

    def test_default_limit(self, client, user, auth_headers) -> None:
        # Smoke test: ensure call works and returns array (no pagination).
        response = client.get("/api/notifications/groups", **auth_headers)
        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), equal_to([]))

    def test_explicit_limit(self, client, user, auth_headers) -> None:
        project = ProjectFactory()
        for _ in range(3):
            d = DiscussionFactory(project=project)
            NotificationFactory(recipient=user, discussion=d)

        response = client.get("/api/notifications/groups?limit=2", **auth_headers)

        assert_that(response.json(), has_length(2))


@pytest.mark.django_db
class TestMarkThreadReadEndpoint:
    def test_unauthenticated_returns_401(self, client) -> None:
        project = ProjectFactory()
        root = DiscussionFactory(project=project)
        response = _post_mark_thread_read(client, root.id, {})
        assert_that(response.status_code, equal_to(401))

    def test_marks_unread_rows(self, client, user, auth_headers) -> None:
        project = ProjectFactory()
        root = DiscussionFactory(project=project)
        reply = DiscussionFactory(project=project, parent=root)
        NotificationFactory(recipient=user, discussion=root)
        NotificationFactory(recipient=user, discussion=reply)

        response = _post_mark_thread_read(client, root.id, auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), equal_to({"marked": 2}))

    def test_idempotent_already_read(self, client, user, auth_headers) -> None:
        project = ProjectFactory()
        root = DiscussionFactory(project=project)
        NotificationFactory(
            recipient=user, discussion=root, in_app_read_at=timezone.now()
        )

        response = _post_mark_thread_read(client, root.id, auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), equal_to({"marked": 0}))

    def test_scoped_to_caller(self, client, user, other_user, auth_headers) -> None:
        from apps.notifications.models import Notification  # noqa: PLC0415

        project = ProjectFactory()
        root = DiscussionFactory(project=project)
        NotificationFactory(recipient=user, discussion=root)
        NotificationFactory(recipient=other_user, discussion=root)

        _post_mark_thread_read(client, root.id, auth_headers)

        unread_recipients = set(
            Notification.objects.filter(in_app_read_at__isnull=True).values_list(
                "recipient_id", flat=True
            )
        )
        assert_that(unread_recipients, equal_to({other_user.id}))
