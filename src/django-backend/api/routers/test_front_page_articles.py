from datetime import timedelta

import pytest
from django.utils import timezone
from hamcrest import assert_that, contains_exactly, equal_to, has_entries, has_length

from apps.projects.models import ImageVariant
from tests.factories import (
    PublishedAuthorArticleFactory,
    article_image,
    front_page_article,
    give_avatar,
)

RECENT_URL = "/api/articles/recent"
SPOTLIGHT_URL = "/api/articles/spotlight"


def days_ago(days: float):
    return timezone.now() - timedelta(days=days)


def newest_first(count: int, **kwargs) -> list:
    return [
        front_page_article(published_at=days_ago(day + 1), **kwargs)
        for day in range(count)
    ]


def with_card_image(article):
    """Give `article` a listing image with a `large` variant, as a card shows."""
    image = article_image(article)
    ImageVariant.objects.create(
        image=image,
        size="large",
        storage_key=f"{image.storage_key}-large",
        width=1200,
        height=675,
        file_size=1,
    )
    article.listing_image = image
    article.save(update_fields=["listing_image"])
    return article


def get_cards(client, url, **params) -> list[dict]:
    response = client.get(url, params)
    assert_that(response.status_code, equal_to(200))
    return response.json()


def assert_card_ids(cards, *expected) -> None:
    assert_that(
        [card["id"] for card in cards],
        contains_exactly(*[str(article.id) for article in expected]),
    )


@pytest.mark.django_db
class TestRecent:
    def test_is_public(self, client) -> None:
        article = front_page_article()

        assert_card_ids(get_cards(client, RECENT_URL), article)

    def test_returns_the_two_newest_by_default(self, client) -> None:
        articles = newest_first(5)

        assert_card_ids(get_cards(client, RECENT_URL), articles[0], articles[1])

    def test_excludes_an_article_past_its_recent_until(self, client) -> None:
        front_page_article(recent_until=days_ago(0.5))

        assert_that(get_cards(client, RECENT_URL), has_length(0))

    def test_is_not_read_as_an_article_id(self, client) -> None:
        response = client.get(RECENT_URL)

        assert_that(response.status_code, equal_to(200))


@pytest.mark.django_db
class TestSpotlight:
    def test_is_public(self, client) -> None:
        article = front_page_article(is_spotlight=True)

        assert_card_ids(get_cards(client, SPOTLIGHT_URL), article)

    def test_returns_the_five_newest_by_default(self, client) -> None:
        articles = newest_first(6, is_spotlight=True)

        assert_card_ids(get_cards(client, SPOTLIGHT_URL), *articles[:5])

    def test_keeps_an_article_past_its_recent_until(self, client) -> None:
        expired = front_page_article(is_spotlight=True, recent_until=days_ago(0.5))

        assert_card_ids(get_cards(client, SPOTLIGHT_URL), expired)

    def test_is_not_read_as_an_article_id(self, client) -> None:
        response = client.get(SPOTLIGHT_URL)

        assert_that(response.status_code, equal_to(200))


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("url", "flags"),
    [(RECENT_URL, {}), (SPOTLIGHT_URL, {"is_spotlight": True})],
)
class TestLimit:
    def test_clamps_a_limit_below_one_to_one(self, client, url, flags) -> None:
        articles = newest_first(3, **flags)

        assert_card_ids(get_cards(client, url, limit=0), articles[0])

    def test_clamps_a_limit_above_ten_to_ten(self, client, url, flags) -> None:
        articles = newest_first(12, **flags)

        assert_card_ids(get_cards(client, url, limit=50), *articles[:10])


@pytest.mark.django_db
class TestCardShape:
    def test_project_article_carries_its_project_and_author(self, client) -> None:
        article = with_card_image(front_page_article(title="On the project"))
        article.listing_crop = {"x": 0, "y": 0, "w": 1, "h": 0.5, "ratio": 16 / 9}
        article.save(update_fields=["listing_crop"])

        [card] = get_cards(client, RECENT_URL)

        assert_that(
            card,
            has_entries(
                title="On the project",
                channel_name="Updates",
                project_slug=article.project.slug,
                project_title=article.project.title,
                author_id=str(article.author_id),
                author_name=article.author.full_name,
                listing_image_url=article.listing_image.variants.get().url,
                listing_crop=has_entries(w=1, h=0.5),
            ),
        )

    def test_author_owned_article_has_no_project_fields(self, client) -> None:
        article = PublishedAuthorArticleFactory(
            published_at=days_ago(1), approved_at=days_ago(1)
        )
        give_avatar(article.author)

        [card] = get_cards(client, RECENT_URL)

        assert_that(
            card,
            has_entries(
                project_slug=None,
                project_title=None,
                author_id=str(article.author_id),
                author_name=article.author.full_name,
                author_avatar_url=article.author.avatar_url,
            ),
        )

    def test_article_without_a_cover_has_no_image(self, client) -> None:
        front_page_article()

        [card] = get_cards(client, RECENT_URL)

        assert_that(card, has_entries(listing_image_url=None, listing_crop=None))


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("url", "flags"),
    [(RECENT_URL, {}), (SPOTLIGHT_URL, {"is_spotlight": True})],
)
def test_card_fields_cost_no_query_per_article(
    client, django_assert_max_num_queries, url, flags
) -> None:
    for _ in range(5):
        article = with_card_image(front_page_article(**flags))
        give_avatar(article.author)
    PublishedAuthorArticleFactory(
        published_at=days_ago(2), approved_at=days_ago(2), **flags
    )

    # The articles with their joins, and the listing images' variants.
    with django_assert_max_num_queries(2):
        cards = get_cards(client, url, limit=10)

    assert_that(cards, has_length(6))
