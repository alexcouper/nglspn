import pytest
from django.urls import reverse
from hamcrest import assert_that, contains_string, equal_to, is_

from tests.factories import PublishedArticleFactory

CHANGELIST = reverse("admin:articles_article_changelist")


def _save_spotlight_from_the_list(admin_client, article, *, spotlight: bool):
    """Submit the changelist's inline-edit form for a list holding one article."""
    data = {
        "form-TOTAL_FORMS": "1",
        "form-INITIAL_FORMS": "1",
        "form-0-id": str(article.pk),
        "_save": "Save",
    }
    if spotlight:
        data["form-0-is_spotlight"] = "on"
    return admin_client.post(CHANGELIST, data)


def _is_spotlighted(article) -> bool:
    article.refresh_from_db()
    return article.is_spotlight


@pytest.mark.django_db
class TestSpotlightFromTheList:
    def test_ticking_spotlight_saves(self, admin_client) -> None:
        article = PublishedArticleFactory()

        response = _save_spotlight_from_the_list(admin_client, article, spotlight=True)

        assert_that(response.status_code, equal_to(302))
        assert_that(_is_spotlighted(article), is_(True))

    def test_unticking_spotlight_saves(self, admin_client) -> None:
        article = PublishedArticleFactory(is_spotlight=True)

        _save_spotlight_from_the_list(admin_client, article, spotlight=False)

        assert_that(_is_spotlighted(article), is_(False))

    def test_list_filters_on_spotlight(self, admin_client) -> None:
        response = admin_client.get(CHANGELIST)

        assert_that(response.content.decode(), contains_string("is_spotlight__exact"))


@pytest.mark.django_db
class TestFrontPageFieldset:
    def test_change_form_offers_both_front_page_fields(self, admin_client) -> None:
        article = PublishedArticleFactory()

        response = admin_client.get(
            reverse("admin:articles_article_change", args=[article.pk])
        )

        page = response.content.decode()
        assert_that(page, contains_string("Front page"))
        assert_that(page, contains_string('name="is_spotlight"'))
        assert_that(page, contains_string('name="recent_until_0"'))
