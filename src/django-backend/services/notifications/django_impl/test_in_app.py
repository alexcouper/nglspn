from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from hamcrest import assert_that, contains_inanyorder, equal_to, has_length

from api.schemas.article import ArticleOut
from apps.notifications.models import Notification, NotificationCadence
from services.notifications.django_impl.handler import DjangoNotificationHandler
from tests.factories import (
    ArticleFactory,
    DiscussionFactory,
    NotificationFactory,
    ProjectFactory,
    ProjectImageFactory,
    PublishedArticleFactory,
    UserFactory,
    article_image,
)

_SEND_EMAIL = (
    "services.email.django_impl.handler"
    ".DjangoEmailHandler"
    ".send_discussion_notification_email"
)


@pytest.fixture
def handler():
    return DjangoNotificationHandler()


@pytest.mark.django_db
class TestListUnreadGroupsForUser:
    def test_empty_when_no_notifications(self, handler) -> None:
        user = UserFactory()
        assert_that(handler.list_unread_groups_for_user(user.id), equal_to([]))

    def test_groups_replies_with_root(self, handler) -> None:
        user = UserFactory()
        project = ProjectFactory()
        root = DiscussionFactory(project=project)
        reply_a = DiscussionFactory(project=project, parent=root)
        reply_b = DiscussionFactory(project=project, parent=root)

        NotificationFactory(recipient=user, discussion=root)
        NotificationFactory(recipient=user, discussion=reply_a)
        NotificationFactory(recipient=user, discussion=reply_b)

        groups = handler.list_unread_groups_for_user(user.id)

        assert_that(groups, has_length(1))
        group = groups[0]
        assert_that(group.root_discussion_id, equal_to(root.id))
        assert_that(group.unread_count, equal_to(3))
        assert_that(group.headline_kind, equal_to("replied"))
        assert_that(group.latest_comment_id, equal_to(reply_b.id))

    def test_started_kind_for_root_only(self, handler) -> None:
        user = UserFactory()
        project = ProjectFactory()
        root = DiscussionFactory(project=project)
        NotificationFactory(recipient=user, discussion=root)

        [group] = handler.list_unread_groups_for_user(user.id)

        assert_that(group.headline_kind, equal_to("started"))

    def test_excludes_read_rows(self, handler) -> None:
        user = UserFactory()
        project = ProjectFactory()
        d_unread = DiscussionFactory(project=project)
        d_read = DiscussionFactory(project=project)
        NotificationFactory(recipient=user, discussion=d_unread)
        NotificationFactory(
            recipient=user, discussion=d_read, in_app_read_at=timezone.now()
        )

        groups = handler.list_unread_groups_for_user(user.id)

        assert_that(groups, has_length(1))
        assert_that(groups[0].root_discussion_id, equal_to(d_unread.id))

    def test_orders_by_latest_event_desc(self, handler) -> None:
        user = UserFactory()
        project = ProjectFactory()
        old_root = DiscussionFactory(project=project)
        new_root = DiscussionFactory(project=project)
        NotificationFactory(recipient=user, discussion=old_root)
        NotificationFactory(recipient=user, discussion=new_root)

        groups = handler.list_unread_groups_for_user(user.id)

        assert_that(
            [g.root_discussion_id for g in groups],
            equal_to([new_root.id, old_root.id]),
        )

    def test_excludes_other_users(self, handler) -> None:
        user = UserFactory()
        other = UserFactory()
        project = ProjectFactory()
        d = DiscussionFactory(project=project)
        NotificationFactory(recipient=other, discussion=d)

        assert_that(handler.list_unread_groups_for_user(user.id), equal_to([]))


def _group_icon_url(handler, user):
    (group,) = handler.list_unread_groups_for_user(user.id)
    return group.project.image_url


@pytest.mark.django_db
class TestGroupProjectIcon:
    """`resolve_image_by_purpose` filters nothing, so the bell's prefetch is
    the only thing keeping an article figure or an abandoned upload out of the
    project icon."""

    def test_discussion_group_uses_the_projects_own_image(self, handler) -> None:
        user = UserFactory()
        project = ProjectFactory()
        icon = ProjectImageFactory(project=project, is_icon=True)
        NotificationFactory(
            recipient=user, discussion=DiscussionFactory(project=project)
        )

        assert_that(_group_icon_url(handler, user), equal_to(icon.url))

    def test_discussion_group_icon_ignores_article_uploads(self, handler) -> None:
        user = UserFactory()
        project = ProjectFactory()
        article_image(ArticleFactory(project=project))
        NotificationFactory(
            recipient=user, discussion=DiscussionFactory(project=project)
        )

        assert_that(_group_icon_url(handler, user), equal_to(None))

    def test_discussion_group_icon_ignores_an_upload_that_never_completed(
        self, handler
    ) -> None:
        user = UserFactory()
        project = ProjectFactory()
        ProjectImageFactory(project=project, upload_status="pending")
        NotificationFactory(
            recipient=user, discussion=DiscussionFactory(project=project)
        )

        assert_that(_group_icon_url(handler, user), equal_to(None))

    def test_article_group_uses_the_projects_own_image(self, handler) -> None:
        user = UserFactory()
        project = ProjectFactory()
        icon = ProjectImageFactory(project=project, is_icon=True)
        NotificationFactory(
            recipient=user,
            discussion=None,
            article=PublishedArticleFactory(project=project),
        )

        assert_that(_group_icon_url(handler, user), equal_to(icon.url))

    def test_article_group_icon_ignores_article_uploads(self, handler) -> None:
        user = UserFactory()
        project = ProjectFactory()
        article_image(ArticleFactory(project=project))
        NotificationFactory(
            recipient=user,
            discussion=None,
            article=PublishedArticleFactory(project=project),
        )

        assert_that(_group_icon_url(handler, user), equal_to(None))

    def test_article_group_icon_ignores_an_upload_that_never_completed(
        self, handler
    ) -> None:
        user = UserFactory()
        project = ProjectFactory()
        ProjectImageFactory(project=project, upload_status="pending")
        NotificationFactory(
            recipient=user,
            discussion=None,
            article=PublishedArticleFactory(project=project),
        )

        assert_that(_group_icon_url(handler, user), equal_to(None))


def _article_group_excerpt(handler, user, article) -> str:
    NotificationFactory(recipient=user, discussion=None, article=article)
    [group] = handler.list_unread_groups_for_user(user.id)
    return group.latest_body_excerpt


@pytest.mark.django_db
class TestArticleGroupExcerpt:
    def test_prefers_the_authored_summary(self, handler) -> None:
        article = PublishedArticleFactory(
            body="## Ignored\n\nDerived from the body.",
            summary="The authored summary.",
        )

        excerpt = _article_group_excerpt(handler, UserFactory(), article)

        assert_that(excerpt, equal_to("The authored summary."))

    def test_flattens_markdown_when_there_is_no_summary(self, handler) -> None:
        article = PublishedArticleFactory(
            body=(
                "# Why we rewrote the indexer\n\n"
                "![diagram](https://cdn.example.com/x.png)\n\n"
                "We replaced the crawler."
            ),
        )

        excerpt = _article_group_excerpt(handler, UserFactory(), article)

        assert_that(excerpt, equal_to("We replaced the crawler."))

    @pytest.mark.parametrize(
        ("body", "summary"),
        [
            ("## Ignored\n\nDerived from the body.", "The authored summary."),
            ("# A heading\n\n![x](https://cdn.example.com/x.png)\n\nReal text.", ""),
            ("Plain [link](https://example.com) and `code`.", ""),
        ],
    )
    def test_matches_the_article_detail_summary(self, handler, body, summary) -> None:
        # The bell and the article detail must not grow two spellings of the
        # same rule again. Bodies here are short enough that the differing
        # `limit` values cannot mask a divergence in the derivation itself.
        article = PublishedArticleFactory(body=body, summary=summary)

        excerpt = _article_group_excerpt(handler, UserFactory(), article)

        assert_that(excerpt, equal_to(ArticleOut.resolve_summary_display(article)))

    def test_a_discussion_excerpt_keeps_literal_markdown_characters(
        self, handler
    ) -> None:
        user = UserFactory()
        discussion = DiscussionFactory(body="Try [this](that) with <T> please")
        NotificationFactory(recipient=user, discussion=discussion)

        [group] = handler.list_unread_groups_for_user(user.id)

        assert_that(
            group.latest_body_excerpt, equal_to("Try [this](that) with <T> please")
        )


@pytest.mark.django_db
class TestGetUnreadSummaryForUser:
    def test_zero(self, handler) -> None:
        user = UserFactory()
        summary = handler.get_unread_summary_for_user(user.id)
        assert_that(summary.has_unread, equal_to(False))
        assert_that(summary.unread_group_count, equal_to(0))

    def test_dedup_across_thread_rows(self, handler) -> None:
        user = UserFactory()
        project = ProjectFactory()
        root = DiscussionFactory(project=project)
        reply = DiscussionFactory(project=project, parent=root)
        NotificationFactory(recipient=user, discussion=root)
        NotificationFactory(recipient=user, discussion=reply)

        summary = handler.get_unread_summary_for_user(user.id)

        assert_that(summary.has_unread, equal_to(True))
        assert_that(summary.unread_group_count, equal_to(1))

    def test_two_threads(self, handler) -> None:
        user = UserFactory()
        project = ProjectFactory()
        d1 = DiscussionFactory(project=project)
        d2 = DiscussionFactory(project=project)
        NotificationFactory(recipient=user, discussion=d1)
        NotificationFactory(recipient=user, discussion=d2)

        summary = handler.get_unread_summary_for_user(user.id)

        assert_that(summary.unread_group_count, equal_to(2))


@pytest.mark.django_db
class TestMarkThreadReadForUser:
    def test_marks_all_unread_rows_for_thread(self, handler) -> None:
        user = UserFactory()
        project = ProjectFactory()
        root = DiscussionFactory(project=project)
        reply = DiscussionFactory(project=project, parent=root)
        other_root = DiscussionFactory(project=project)
        NotificationFactory(recipient=user, discussion=root)
        NotificationFactory(recipient=user, discussion=reply)
        unaffected = NotificationFactory(recipient=user, discussion=other_root)

        marked = handler.mark_thread_read_for_user(user.id, root.id)

        assert_that(marked, equal_to(2))
        unread_ids = list(
            Notification.objects.filter(in_app_read_at__isnull=True).values_list(
                "id", flat=True
            )
        )
        assert_that(unread_ids, equal_to([unaffected.id]))

    def test_idempotent(self, handler) -> None:
        user = UserFactory()
        project = ProjectFactory()
        root = DiscussionFactory(project=project)

        assert_that(handler.mark_thread_read_for_user(user.id, root.id), equal_to(0))

    def test_scoped_to_caller(self, handler) -> None:
        user = UserFactory()
        other = UserFactory()
        project = ProjectFactory()
        root = DiscussionFactory(project=project)
        NotificationFactory(recipient=user, discussion=root)
        other_n = NotificationFactory(recipient=other, discussion=root)

        handler.mark_thread_read_for_user(user.id, root.id)

        other_n.refresh_from_db()
        assert_that(other_n.in_app_read_at is None, equal_to(True))


@pytest.mark.django_db
class TestMarkThreadReadForComment:
    def test_marks_thread_when_comment_is_a_reply(self, handler) -> None:
        user = UserFactory()
        project = ProjectFactory()
        root = DiscussionFactory(project=project)
        reply = DiscussionFactory(project=project, parent=root)
        NotificationFactory(recipient=user, discussion=root)
        NotificationFactory(recipient=user, discussion=reply)

        marked = handler.mark_thread_read_for_comment(user.id, reply.id)

        assert_that(marked, equal_to(2))

    def test_marks_thread_when_comment_is_a_root(self, handler) -> None:
        user = UserFactory()
        project = ProjectFactory()
        root = DiscussionFactory(project=project)
        reply = DiscussionFactory(project=project, parent=root)
        NotificationFactory(recipient=user, discussion=root)
        NotificationFactory(recipient=user, discussion=reply)

        marked = handler.mark_thread_read_for_comment(user.id, root.id)

        assert_that(marked, equal_to(2))

    def test_returns_zero_when_comment_does_not_exist(self, handler) -> None:
        from uuid import uuid4  # noqa: PLC0415

        user = UserFactory()

        assert_that(handler.mark_thread_read_for_comment(user.id, uuid4()), equal_to(0))


@pytest.mark.django_db
class TestMarkAllReadForUser:
    def test_marks_all_unread_rows_for_caller(self, handler) -> None:
        user = UserFactory()
        project = ProjectFactory()
        root_a = DiscussionFactory(project=project)
        root_b = DiscussionFactory(project=project)
        reply = DiscussionFactory(project=project, parent=root_a)
        NotificationFactory(recipient=user, discussion=root_a)
        NotificationFactory(recipient=user, discussion=root_b)
        NotificationFactory(recipient=user, discussion=reply)

        marked = handler.mark_all_read_for_user(user.id)

        assert_that(marked, equal_to(3))
        assert_that(
            Notification.objects.filter(
                recipient=user, in_app_read_at__isnull=True
            ).count(),
            equal_to(0),
        )

    def test_does_not_touch_other_users_rows(self, handler) -> None:
        user = UserFactory()
        other = UserFactory()
        project = ProjectFactory()
        d = DiscussionFactory(project=project)
        NotificationFactory(recipient=user, discussion=d)
        other_n = NotificationFactory(recipient=other, discussion=d)

        handler.mark_all_read_for_user(user.id)

        other_n.refresh_from_db()
        assert_that(other_n.in_app_read_at is None, equal_to(True))

    def test_idempotent(self, handler) -> None:
        user = UserFactory()
        project = ProjectFactory()
        d = DiscussionFactory(project=project)
        NotificationFactory(recipient=user, discussion=d)

        handler.mark_all_read_for_user(user.id)
        second = handler.mark_all_read_for_user(user.id)

        assert_that(second, equal_to(0))


@pytest.mark.django_db
class TestDeleteOldReadNotifications:
    def test_deletes_only_old_read_rows(self, handler) -> None:
        user = UserFactory()
        project = ProjectFactory()
        NotificationFactory(
            recipient=user,
            discussion=DiscussionFactory(project=project),
            in_app_read_at=timezone.now() - timedelta(days=31),
        )
        recent_read = NotificationFactory(
            recipient=user,
            discussion=DiscussionFactory(project=project),
            in_app_read_at=timezone.now() - timedelta(days=10),
        )
        old_unread = NotificationFactory(
            recipient=user, discussion=DiscussionFactory(project=project)
        )
        Notification.objects.filter(id=old_unread.id).update(in_app_read_at=None)

        deleted = handler.delete_old_read_notifications()

        assert_that(deleted, equal_to(1))
        remaining = set(Notification.objects.values_list("id", flat=True))
        assert_that(remaining, contains_inanyorder(recent_read.id, old_unread.id))


@pytest.mark.django_db
class TestNeverCadenceCreatesRowNoEmail:
    def test_in_app_delivery_works_for_never(self, handler) -> None:
        from apps.projects.models import ProjectStatus  # noqa: PLC0415

        owner = UserFactory(discussion_email_frequency=NotificationCadence.NEVER)
        project = ProjectFactory(owner=owner, status=ProjectStatus.APPROVED)
        author = UserFactory()
        discussion = DiscussionFactory(project=project, author=author)

        with patch(_SEND_EMAIL) as send:
            handler.create_notifications_for_discussion(discussion.id)

        assert_that(send.called, equal_to(False))
        groups = handler.list_unread_groups_for_user(owner.id)
        assert_that(groups, has_length(1))


@pytest.mark.django_db
class TestBatchDigestExcludesReadInApp:
    @pytest.mark.parametrize("cadence", ["hourly", "daily"])
    def test_excludes_read_in_app(self, handler, cadence) -> None:
        user = UserFactory()
        project = ProjectFactory()
        d_read = DiscussionFactory(project=project)
        d_unread = DiscussionFactory(project=project)
        NotificationFactory(
            recipient=user,
            discussion=d_read,
            email_cadence=cadence,
            in_app_read_at=timezone.now(),
        )
        unread_n = NotificationFactory(
            recipient=user, discussion=d_unread, email_cadence=cadence
        )

        with patch(
            "services.email.django_impl.handler"
            ".DjangoEmailHandler"
            ".send_discussion_digest_email"
        ) as mock_digest:
            handler.send_discussion_digest(cadence)

        sent = mock_digest.call_args[1]["notifications"]
        assert_that([n.id for n in sent], equal_to([unread_n.id]))
