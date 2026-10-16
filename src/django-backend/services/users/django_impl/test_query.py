from uuid import uuid4

import pytest

from apps.articles.models import ArticleGlobalVisibility
from apps.projects.models import ProjectStatus
from services.users.django_impl import DjangoUserQuery
from services.users.exceptions import UserNotFoundError
from tests.factories import (
    AuthorArticleFactory,
    ProjectFactory,
    PublishedArticleFactory,
    PublishedAuthorArticleFactory,
    UserFactory,
    make_broadcast_follower,
    make_house_channel_follower,
)

query = DjangoUserQuery()


@pytest.mark.django_db
class TestGetById:
    def test_returns_existing_user(self):
        user = UserFactory()

        result = query.get_by_id(user.id)

        assert result.id == user.id
        assert result.email == user.email

    def test_raises_for_nonexistent_user(self):
        with pytest.raises(UserNotFoundError):
            query.get_by_id(uuid4())


@pytest.mark.django_db
class TestGetActiveById:
    def test_returns_active_user(self):
        user = UserFactory(is_active=True)

        result = query.get_active_by_id(user.id)

        assert result is not None
        assert result.id == user.id

    def test_returns_none_for_inactive_user(self):
        user = UserFactory(is_active=False)

        result = query.get_active_by_id(user.id)

        assert result is None

    def test_returns_none_for_nonexistent_user(self):
        result = query.get_active_by_id(uuid4())

        assert result is None


@pytest.mark.django_db
class TestEmailExists:
    def test_true_when_email_registered(self):
        user = UserFactory(email="exists@example.com")

        assert query.email_exists(user.email) is True

    def test_false_when_email_not_registered(self):
        assert query.email_exists("nobody@example.com") is False


@pytest.mark.django_db
class TestKennitalaExists:
    def test_true_when_kennitala_registered(self):
        user = UserFactory(kennitala="1234567890")

        assert query.kennitala_exists(user.kennitala) is True

    def test_false_when_kennitala_not_registered(self):
        assert query.kennitala_exists("9999999999") is False


@pytest.mark.django_db
class TestListOptedInForBroadcastType:
    def test_returns_channel_followers_for_competition_results(self):
        follower = make_broadcast_follower("competition_results")
        # System user — auto-follow signal skips them.
        UserFactory(is_system_user=True)

        result = query.list_opted_in_for_broadcast_type("competition_results")

        assert list(result) == [follower]

    def test_excludes_users_on_never_article_cadence(self):
        from apps.users.models import ArticleEmailFrequency  # noqa: PLC0415

        make_broadcast_follower(
            "competition_results",
            article_email_frequency=ArticleEmailFrequency.NEVER,
        )

        result = query.list_opted_in_for_broadcast_type("competition_results")

        assert result.count() == 0

    def test_returns_empty_for_unknown_type(self):
        make_broadcast_follower("competition_results")

        result = query.list_opted_in_for_broadcast_type("unknown_type")

        assert result.count() == 0

    def test_returns_empty_for_retired_platform_updates_type(self):
        make_house_channel_follower("Updates")

        result = query.list_opted_in_for_broadcast_type("platform_updates")

        assert result.count() == 0

    def test_returns_empty_when_no_house_project(self):
        UserFactory()

        result = query.list_opted_in_for_broadcast_type("competition_results")

        assert result.count() == 0

    def test_excludes_inactive_users(self):
        make_broadcast_follower("competition_results", is_active=False)

        result = query.list_opted_in_for_broadcast_type("competition_results")

        assert result.count() == 0

    def test_excludes_system_users(self):
        make_broadcast_follower("competition_results", is_system_user=True)

        result = query.list_opted_in_for_broadcast_type("competition_results")

        assert result.count() == 0


@pytest.mark.django_db
class TestListPublicArticlesFor:
    def test_mixes_author_owned_and_approved_project_articles(self):
        author = UserFactory()
        on_project = PublishedArticleFactory(
            project=ProjectFactory(owner=author, status=ProjectStatus.APPROVED),
            author=author,
        )
        owned = PublishedAuthorArticleFactory(author=author)

        assert set(query.list_public_articles_for(author.id)) == {on_project, owned}

    def test_hides_an_author_owned_article_that_is_not_visible(self):
        author = UserFactory()
        PublishedAuthorArticleFactory(
            author=author, global_visibility=ArticleGlobalVisibility.PENDING
        )
        AuthorArticleFactory(author=author)

        assert list(query.list_public_articles_for(author.id)) == []

    def test_still_hides_articles_on_unapproved_projects(self):
        author = UserFactory()
        PublishedArticleFactory(project=ProjectFactory(owner=author), author=author)

        assert list(query.list_public_articles_for(author.id)) == []


@pytest.mark.django_db
class TestListOwnArticlesFor:
    def test_returns_every_state_of_both_kinds_drafts_first(self):
        author = UserFactory()
        pending = PublishedAuthorArticleFactory(
            author=author, global_visibility=ArticleGlobalVisibility.PENDING
        )
        on_project = PublishedArticleFactory(author=author)
        draft = AuthorArticleFactory(author=author)

        listed = list(query.list_own_articles_for(author.id))

        assert listed[0] == draft
        assert set(listed) == {draft, pending, on_project}

    def test_excludes_other_peoples_articles(self):
        author = UserFactory()
        AuthorArticleFactory()

        assert list(query.list_own_articles_for(author.id)) == []
