import pytest
from hamcrest import (
    assert_that,
    equal_to,
    has_entries,
    has_key,
    has_length,
    is_not,
)

from api.auth.jwt import create_access_token
from apps.translations.models import Translation
from tests.factories import TranslationFactory, UserFactory


def _auth_header(user) -> dict[str, str]:
    token = create_access_token(user.id)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.mark.django_db
class TestGetCatalog:
    def test_returns_key_text_map_for_locale(self, client) -> None:
        TranslationFactory(locale="is", key="custom.key", text="Custom")
        TranslationFactory(locale="en", key="nav.home", text="Home")

        response = client.get("/api/i18n/is")

        assert_that(response.status_code, equal_to(200))
        result = response.json()
        # Should include seeded chrome keys + custom key
        assert_that(
            result,
            has_entries(**{"custom.key": "Custom", "nav.projects": "Verkefni"}),
        )

    def test_excludes_retired_rows(self, client) -> None:
        TranslationFactory(locale="is", key="custom.old", text="Gamalt", retired=True)

        response = client.get("/api/i18n/is")

        assert_that(response.status_code, equal_to(200))
        body = response.json()
        assert_that(body, has_entries(**{"nav.projects": "Verkefni"}))
        assert_that(body, is_not(has_key("custom.old")))

    def test_unknown_locale_returns_empty(self, client) -> None:
        response = client.get("/api/i18n/xx")
        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), equal_to({}))


@pytest.mark.django_db
class TestGetVersion:
    def test_empty_returns_zero(self, client) -> None:
        response = client.get("/api/i18n/xx/version")
        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), equal_to({"version": 0}))

    def test_returns_max_updated_at_as_epoch(self, client) -> None:
        t = TranslationFactory(locale="is", key="nav.home", text="Heim")
        response = client.get("/api/i18n/is/version")
        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["version"], equal_to(int(t.updated_at.timestamp())))


@pytest.mark.django_db
class TestPatchTranslation:
    def test_requires_authentication(self, client) -> None:
        TranslationFactory(locale="is", key="nav.home", text="Heim")
        response = client.patch(
            "/api/i18n/is/nav.home",
            data='{"text":"Forsíða"}',
            content_type="application/json",
        )
        assert_that(response.status_code, equal_to(401))

    def test_updates_row_via_handler(self, client) -> None:
        user = UserFactory()
        TranslationFactory(
            locale="is",
            key="nav.home",
            text="Heim",
            is_machine_translated=True,
        )
        response = client.patch(
            "/api/i18n/is/nav.home",
            data='{"text":"Forsíða"}',
            content_type="application/json",
            **_auth_header(user),
        )
        assert_that(response.status_code, equal_to(200))
        t = Translation.objects.get(locale="is", key="nav.home")
        assert_that(t.text, equal_to("Forsíða"))
        assert_that(t.is_machine_translated, equal_to(False))

    def test_creates_row_if_missing(self, client) -> None:
        user = UserFactory()
        response = client.patch(
            "/api/i18n/is/new.key",
            data='{"text":"Nýtt"}',
            content_type="application/json",
            **_auth_header(user),
        )
        assert_that(response.status_code, equal_to(200))
        assert_that(
            Translation.objects.filter(locale="is", key="new.key").exists(),
            equal_to(True),
        )


@pytest.mark.django_db
class TestGetTranslationDetail:
    def test_returns_existing_row_with_text_and_updated_at(self, client) -> None:
        TranslationFactory(locale="is", key="nav.home", text="Heim")

        response = client.get("/api/i18n/is/nav.home")

        assert_that(response.status_code, equal_to(200))
        body = response.json()
        assert_that(body, has_entries(locale="is", key="nav.home", text="Heim"))
        assert body["updated_at"] is not None

    def test_returns_empty_text_for_missing_row(self, client) -> None:
        response = client.get("/api/i18n/is/no.such.key")

        assert_that(response.status_code, equal_to(200))
        body = response.json()
        assert_that(body["text"], equal_to(""))
        assert_that(body["updated_at"], equal_to(None))
        assert_that(body["history"], equal_to([]))

    def test_history_returned_newest_first(self, client) -> None:
        user = UserFactory(first_name="Alice", last_name="A")
        t = TranslationFactory(
            locale="is", key="nav.home", text="Heim", updated_by=user
        )
        for txt in ["A", "B", "C"]:
            t.text = txt
            t.updated_by = user
            t.save()

        response = client.get("/api/i18n/is/nav.home")

        body = response.json()
        # 1 audit on creation + 3 from the loop = 4
        assert_that(body["history"], has_length(4))
        assert_that(body["history"][0]["new_text"], equal_to("C"))
        assert_that(body["history"][-1]["new_text"], equal_to("Heim"))


@pytest.mark.django_db
class TestPatchTranslationContract:
    def test_response_includes_updated_at(self, client) -> None:
        user = UserFactory()
        TranslationFactory(locale="is", key="nav.home", text="Heim")

        response = client.patch(
            "/api/i18n/is/nav.home",
            data='{"text":"Forsíða"}',
            content_type="application/json",
            **_auth_header(user),
        )

        assert_that(response.status_code, equal_to(200))
        body = response.json()
        assert_that(body["text"], equal_to("Forsíða"))
        # updated_at must be present and ISO-8601-shaped (popover relies on it
        # for concurrency checks).
        assert "updated_at" in body
        assert "T" in body["updated_at"]
