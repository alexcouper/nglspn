import json

import pytest
from django.utils import timezone
from hamcrest import assert_that, equal_to, has_entries, has_length

from tests.factories import (
    DiscussionFactory,
    NotificationFactory,
    ProjectFactory,
    PublishedArticleFactory,
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
                kind="discussion",
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


@pytest.mark.django_db
class TestGroupsEndpointArticleKind:
    def test_article_group_includes_kind_and_metadata(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory()
        article = PublishedArticleFactory(
            project=project, title="Spring update", body="Body."
        )
        article.slug = "spring-update"
        article.save(update_fields=["slug"])
        NotificationFactory(recipient=user, discussion=None, article=article)

        response = client.get("/api/notifications/groups", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        data = response.json()
        assert_that(data, has_length(1))
        assert_that(
            data[0],
            has_entries(
                kind="article",
                article_id=str(article.id),
                article_slug="spring-update",
                article_title="Spring update",
                channel_name=article.channel.name,
                unread_count=1,
                root_discussion_id=None,
            ),
        )

    def test_mixed_groups_returned(self, client, user, auth_headers) -> None:
        project_a = ProjectFactory()
        project_b = ProjectFactory()
        discussion = DiscussionFactory(project=project_a)
        article = PublishedArticleFactory(project=project_b, title="News")
        article.slug = "news"
        article.save(update_fields=["slug"])
        NotificationFactory(recipient=user, discussion=discussion)
        NotificationFactory(recipient=user, discussion=None, article=article)

        response = client.get("/api/notifications/groups", **auth_headers)

        kinds = sorted(g["kind"] for g in response.json())
        assert_that(kinds, equal_to(["article", "discussion"]))

    def test_summary_counts_both_kinds(self, client, user, auth_headers) -> None:
        project_a = ProjectFactory()
        project_b = ProjectFactory()
        discussion = DiscussionFactory(project=project_a)
        article = PublishedArticleFactory(project=project_b)
        NotificationFactory(recipient=user, discussion=discussion)
        NotificationFactory(recipient=user, discussion=None, article=article)

        response = client.get("/api/notifications/summary", **auth_headers)

        assert_that(
            response.json(),
            equal_to({"has_unread": True, "unread_group_count": 2}),
        )


@pytest.mark.django_db
class TestMarkThreadReadByArticle:
    def test_marks_article_notification(self, client, user, auth_headers) -> None:
        project = ProjectFactory()
        article = PublishedArticleFactory(project=project)
        NotificationFactory(recipient=user, discussion=None, article=article)

        response = client.post(
            "/api/notifications/mark-thread-read",
            data=json.dumps({"article_id": str(article.id)}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), equal_to({"marked": 1}))

    def test_scoped_to_caller(self, client, user, other_user, auth_headers) -> None:
        from apps.notifications.models import Notification  # noqa: PLC0415

        project = ProjectFactory()
        article = PublishedArticleFactory(project=project)
        NotificationFactory(recipient=user, discussion=None, article=article)
        NotificationFactory(recipient=other_user, discussion=None, article=article)

        client.post(
            "/api/notifications/mark-thread-read",
            data=json.dumps({"article_id": str(article.id)}),
            content_type="application/json",
            **auth_headers,
        )

        unread_recipients = set(
            Notification.objects.filter(in_app_read_at__isnull=True).values_list(
                "recipient_id", flat=True
            )
        )
        assert_that(unread_recipients, equal_to({other_user.id}))

    def test_rejects_article_id_with_root_discussion_id(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory()
        article = PublishedArticleFactory(project=project)
        discussion = DiscussionFactory(project=project)

        response = client.post(
            "/api/notifications/mark-thread-read",
            data=json.dumps(
                {
                    "article_id": str(article.id),
                    "root_discussion_id": str(discussion.id),
                }
            ),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(422))

    def test_rejects_all_three_fields(self, client, user, auth_headers) -> None:
        project = ProjectFactory()
        article = PublishedArticleFactory(project=project)
        discussion = DiscussionFactory(project=project)

        response = client.post(
            "/api/notifications/mark-thread-read",
            data=json.dumps(
                {
                    "article_id": str(article.id),
                    "root_discussion_id": str(discussion.id),
                    "comment_id": str(discussion.id),
                }
            ),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(422))


@pytest.mark.django_db
class TestMarkThreadReadByComment:
    def test_marks_thread_when_only_comment_id_is_provided(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory()
        root = DiscussionFactory(project=project)
        reply = DiscussionFactory(project=project, parent=root)
        NotificationFactory(recipient=user, discussion=root)
        NotificationFactory(recipient=user, discussion=reply)

        response = client.post(
            "/api/notifications/mark-thread-read",
            data=json.dumps({"comment_id": str(reply.id)}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), equal_to({"marked": 2}))

    def test_rejects_request_with_both_fields(self, client, user, auth_headers) -> None:
        project = ProjectFactory()
        root = DiscussionFactory(project=project)
        response = client.post(
            "/api/notifications/mark-thread-read",
            data=json.dumps(
                {
                    "root_discussion_id": str(root.id),
                    "comment_id": str(root.id),
                }
            ),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(422))

    def test_rejects_request_with_neither_field(
        self, client, user, auth_headers
    ) -> None:
        response = client.post(
            "/api/notifications/mark-thread-read",
            data=json.dumps({}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(422))


@pytest.mark.django_db
class TestMarkAllReadEndpoint:
    def test_unauthenticated_returns_401(self, client) -> None:
        response = client.post("/api/notifications/mark-all-read")
        assert_that(response.status_code, equal_to(401))

    def test_marks_all_unread_for_caller(self, client, user, auth_headers) -> None:
        project = ProjectFactory()
        root_a = DiscussionFactory(project=project)
        root_b = DiscussionFactory(project=project)
        NotificationFactory(recipient=user, discussion=root_a)
        NotificationFactory(recipient=user, discussion=root_b)

        response = client.post("/api/notifications/mark-all-read", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), equal_to({"marked": 2}))

    def test_does_not_touch_other_users(
        self, client, user, other_user, auth_headers
    ) -> None:
        from apps.notifications.models import Notification  # noqa: PLC0415

        project = ProjectFactory()
        root = DiscussionFactory(project=project)
        NotificationFactory(recipient=user, discussion=root)
        NotificationFactory(recipient=other_user, discussion=root)

        client.post("/api/notifications/mark-all-read", **auth_headers)

        unread_recipients = set(
            Notification.objects.filter(in_app_read_at__isnull=True).values_list(
                "recipient_id", flat=True
            )
        )
        assert_that(unread_recipients, equal_to({other_user.id}))
