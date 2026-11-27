from importlib import import_module

import pytest
from django.apps import apps as django_apps
from hamcrest import assert_that, is_

from tests.factories import (
    ArticleFactory,
    ChannelFactory,
    PendingArticleFactory,
    ProjectFactory,
    PublishedArticleFactory,
    ensure_house_project,
)

migration_module = import_module(
    "apps.articles.migrations.0013_spotlight_house_reviews"
)


def _run_migration() -> None:
    migration_module.spotlight_house_reviews(django_apps, schema_editor=None)


def _is_spotlighted(article) -> bool:
    article.refresh_from_db()
    return article.is_spotlight


def _reviews_channel(project):
    return ChannelFactory(project=project, name="Reviews")


@pytest.mark.django_db
class TestSpotlightHouseReviews:
    @pytest.fixture
    def house(self):
        return ensure_house_project()

    def test_flags_a_published_house_review(self, house) -> None:
        review = PublishedArticleFactory(project=house, channel=_reviews_channel(house))

        _run_migration()

        assert_that(_is_spotlighted(review), is_(True))

    def test_skips_a_house_review_still_in_draft(self, house) -> None:
        draft = ArticleFactory(project=house, channel=_reviews_channel(house))

        _run_migration()

        assert_that(_is_spotlighted(draft), is_(False))

    def test_skips_a_house_review_awaiting_approval(self, house) -> None:
        pending = PendingArticleFactory(project=house, channel=_reviews_channel(house))

        _run_migration()

        assert_that(_is_spotlighted(pending), is_(False))

    def test_skips_a_house_article_in_updates(self, house) -> None:
        update = PublishedArticleFactory(project=house)

        _run_migration()

        assert_that(_is_spotlighted(update), is_(False))

    def test_skips_a_review_on_another_project(self, house) -> None:
        elsewhere = ProjectFactory()
        review = PublishedArticleFactory(
            project=elsewhere, channel=_reviews_channel(elsewhere)
        )

        _run_migration()

        assert_that(_is_spotlighted(review), is_(False))

    def test_does_nothing_without_a_house_project(self) -> None:
        other = ProjectFactory()
        review = PublishedArticleFactory(project=other, channel=_reviews_channel(other))

        _run_migration()

        assert_that(_is_spotlighted(review), is_(False))
