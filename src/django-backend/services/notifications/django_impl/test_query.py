import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from hamcrest import assert_that, equal_to

from services.notifications.django_impl.query import DjangoNotificationQuery
from tests.factories import (
    DiscussionFactory,
    NotificationFactory,
    ProjectFactory,
    UserFactory,
)


@pytest.fixture
def query():
    return DjangoNotificationQuery()


def _read():
    return timezone.now()


@pytest.mark.django_db
class TestListUnreadForUser:
    def test_returns_only_users_unread_rows(self, query) -> None:
        user = UserFactory()
        other = UserFactory()
        project = ProjectFactory()
        d1 = DiscussionFactory(project=project)
        d2 = DiscussionFactory(project=project)
        mine_unread = NotificationFactory(recipient=user, discussion=d1)
        NotificationFactory(recipient=user, discussion=d2, in_app_read_at=_read())
        NotificationFactory(recipient=other, discussion=d1)

        rows = list(query.list_unread_for_user(user.id))

        assert_that([r.id for r in rows], equal_to([mine_unread.id]))

    def test_orders_by_discussion_created_desc(self, query) -> None:
        user = UserFactory()
        project = ProjectFactory()
        old = DiscussionFactory(project=project)
        new = DiscussionFactory(project=project)
        n_old = NotificationFactory(recipient=user, discussion=old)
        n_new = NotificationFactory(recipient=user, discussion=new)

        rows = list(query.list_unread_for_user(user.id))

        assert_that([r.id for r in rows], equal_to([n_new.id, n_old.id]))


@pytest.mark.django_db
class TestCountUnreadGroupsForUser:
    def test_zero_when_no_rows(self, query) -> None:
        user = UserFactory()
        assert_that(query.count_unread_groups_for_user(user.id), equal_to(0))

    def test_groups_replies_under_root_discussion(self, query) -> None:
        user = UserFactory()
        project = ProjectFactory()
        root = DiscussionFactory(project=project)
        reply_a = DiscussionFactory(project=project, parent=root)
        reply_b = DiscussionFactory(project=project, parent=root)
        other_root = DiscussionFactory(project=project)

        NotificationFactory(recipient=user, discussion=root)
        NotificationFactory(recipient=user, discussion=reply_a)
        NotificationFactory(recipient=user, discussion=reply_b)
        NotificationFactory(recipient=user, discussion=other_root)

        assert_that(query.count_unread_groups_for_user(user.id), equal_to(2))

    def test_excludes_read_rows(self, query) -> None:
        user = UserFactory()
        project = ProjectFactory()
        d = DiscussionFactory(project=project)
        NotificationFactory(recipient=user, discussion=d, in_app_read_at=_read())

        assert_that(query.count_unread_groups_for_user(user.id), equal_to(0))

    def test_count_query_runs_in_one_query_with_distinct(self, query) -> None:
        user = UserFactory()
        project = ProjectFactory()
        root = DiscussionFactory(project=project)
        NotificationFactory(recipient=user, discussion=root)
        for _ in range(50):
            reply = DiscussionFactory(project=project, parent=root)
            NotificationFactory(recipient=user, discussion=reply)

        with CaptureQueriesContext(connection) as ctx:
            result = query.count_unread_groups_for_user(user.id)

        assert_that(result, equal_to(1))
        assert_that(len(ctx.captured_queries), equal_to(1))
        sql = ctx.captured_queries[0]["sql"].lower()
        assert "distinct" in sql or "group by" in sql, sql


@pytest.mark.django_db
class TestUnreadRowsForThread:
    def test_returns_root_and_replies_for_user(self, query) -> None:
        user = UserFactory()
        project = ProjectFactory()
        root = DiscussionFactory(project=project)
        reply = DiscussionFactory(project=project, parent=root)
        other_root = DiscussionFactory(project=project)

        n_root = NotificationFactory(recipient=user, discussion=root)
        n_reply = NotificationFactory(recipient=user, discussion=reply)
        NotificationFactory(recipient=user, discussion=other_root)

        rows = list(query.unread_rows_for_thread(user.id, root.id))

        assert_that(
            sorted(r.id for r in rows), equal_to(sorted([n_root.id, n_reply.id]))
        )

    def test_excludes_other_users(self, query) -> None:
        user = UserFactory()
        other = UserFactory()
        project = ProjectFactory()
        root = DiscussionFactory(project=project)

        mine = NotificationFactory(recipient=user, discussion=root)
        NotificationFactory(recipient=other, discussion=root)

        rows = list(query.unread_rows_for_thread(user.id, root.id))

        assert_that([r.id for r in rows], equal_to([mine.id]))

    def test_excludes_read_rows(self, query) -> None:
        user = UserFactory()
        project = ProjectFactory()
        root = DiscussionFactory(project=project)
        NotificationFactory(recipient=user, discussion=root, in_app_read_at=_read())

        rows = list(query.unread_rows_for_thread(user.id, root.id))

        assert_that(rows, equal_to([]))
