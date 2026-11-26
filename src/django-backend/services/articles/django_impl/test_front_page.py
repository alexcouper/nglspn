from datetime import datetime, timedelta

import pytest
from django.utils import timezone
from hamcrest import assert_that, contains_exactly, empty

from apps.articles.models import Article, ArticleGlobalVisibility
from apps.projects.models import ProjectStatus
from services import HANDLERS, REPO
from tests.factories import (
    ProjectFactory,
    PublishedArticleFactory,
    PublishedAuthorArticleFactory,
)


def days_ago(days: float) -> datetime:
    return timezone.now() - timedelta(days=days)


def days_ahead(days: float) -> datetime:
    return timezone.now() + timedelta(days=days)


def front_page_article(
    *,
    published_at: datetime | None = None,
    approved_at: datetime | None = None,
    project_status: str = ProjectStatus.APPROVED,
    **kwargs,
) -> Article:
    """A visible article on an approved project: eligible unless told otherwise.

    `approved_at` defaults to `published_at`, as it is for a trusted author.
    """
    published_at = published_at or days_ago(1)
    return PublishedArticleFactory(
        project=ProjectFactory(status=project_status),
        published_at=published_at,
        approved_at=approved_at or published_at,
        **kwargs,
    )


def assert_ids(articles, *expected: Article) -> None:
    assert_that([a.id for a in articles], contains_exactly(*[e.id for e in expected]))


def assert_none(articles) -> None:
    assert_that(list(articles), empty())


@pytest.mark.django_db
class TestFrontPageOrder:
    def test_orders_by_when_the_article_became_visible(self) -> None:
        approved_late = front_page_article(
            published_at=days_ago(25), approved_at=days_ago(16)
        )
        auto_approved = front_page_article(published_at=days_ago(20))

        assert_ids(REPO.articles.recent(10), approved_late, auto_approved)

    def test_editing_the_publish_date_does_not_move_an_article_up(self) -> None:
        older = front_page_article(published_at=days_ago(25))
        newer = front_page_article(published_at=days_ago(10))

        Article.objects.filter(pk=older.pk).update(published_at=days_ago(0.1))

        assert_ids(REPO.articles.recent(10), newer, older)

    def test_falls_back_to_the_publish_date_without_an_approval_time(self) -> None:
        unstamped = front_page_article(published_at=days_ago(2))
        Article.objects.filter(pk=unstamped.pk).update(approved_at=None)
        stamped = front_page_article(published_at=days_ago(5))

        assert_ids(REPO.articles.recent(10), unstamped, stamped)

    def test_has_no_age_limit(self) -> None:
        old = front_page_article(published_at=days_ago(20))

        assert_ids(REPO.articles.recent(2), old)

    def test_approving_puts_an_article_first(self) -> None:
        held = front_page_article(
            published_at=days_ago(3),
            global_visibility=ArticleGlobalVisibility.PENDING,
        )
        Article.objects.filter(pk=held.pk).update(approved_at=None)
        visible = front_page_article(published_at=days_ago(1))

        HANDLERS.articles.set_global_visibility(
            held.id, ArticleGlobalVisibility.APPROVED
        )

        assert_ids(REPO.articles.recent(10), held, visible)

    def test_limit_returns_the_newest(self) -> None:
        articles = [front_page_article(published_at=days_ago(d)) for d in range(5)]

        assert_ids(REPO.articles.recent(2), articles[0], articles[1])


@pytest.mark.django_db
class TestFrontPageEligibility:
    def test_includes_an_author_owned_article(self) -> None:
        own = PublishedAuthorArticleFactory(
            published_at=days_ago(1), approved_at=days_ago(1)
        )

        assert_ids(REPO.articles.recent(10), own)

    def test_excludes_an_article_awaiting_review(self) -> None:
        front_page_article(global_visibility=ArticleGlobalVisibility.PENDING)

        assert_none(REPO.articles.recent(10))

    def test_excludes_a_demoted_article(self) -> None:
        front_page_article(global_visibility=ArticleGlobalVisibility.DEMOTED)

        assert_none(REPO.articles.recent(10))

    def test_excludes_an_article_on_a_project_that_is_not_approved(self) -> None:
        front_page_article(project_status=ProjectStatus.ICE_BOX)

        assert_none(REPO.articles.recent(10))

    def test_excludes_an_article_scheduled_for_later(self) -> None:
        front_page_article(published_at=days_ahead(2))

        assert_none(REPO.articles.recent(10))

    def test_held_back_spotlighted_article_is_not_spotlighted(self) -> None:
        front_page_article(
            is_spotlight=True, global_visibility=ArticleGlobalVisibility.PENDING
        )

        assert_none(REPO.articles.spotlight(10))


@pytest.mark.django_db
class TestRecentExpiry:
    def test_excludes_an_article_past_its_recent_until(self) -> None:
        front_page_article(recent_until=days_ago(0.5))

        assert_none(REPO.articles.recent(10))

    def test_includes_an_article_before_its_recent_until(self) -> None:
        notice = front_page_article(recent_until=days_ahead(1))

        assert_ids(REPO.articles.recent(10), notice)


@pytest.mark.django_db
class TestSpotlight:
    def test_returns_only_spotlighted_articles(self) -> None:
        spotlighted = front_page_article(is_spotlight=True)
        front_page_article()

        assert_ids(REPO.articles.spotlight(10), spotlighted)

    def test_keeps_an_article_past_its_recent_until(self) -> None:
        expired = front_page_article(is_spotlight=True, recent_until=days_ago(1))

        assert_ids(REPO.articles.spotlight(10), expired)

    def test_uses_the_front_page_order(self) -> None:
        older = front_page_article(is_spotlight=True, published_at=days_ago(4))
        newer = front_page_article(is_spotlight=True, published_at=days_ago(2))

        assert_ids(REPO.articles.spotlight(10), newer, older)
