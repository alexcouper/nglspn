import pytest
from hamcrest import assert_that, equal_to, has_entries, has_key, is_not

from api.auth.jwt import create_access_token
from apps.translations.models import Translation
from tests.factories import TranslationFactory, UserFactory


def _auth_header(user) -> dict[str, str]:
    token = create_access_token(user.id)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.mark.django_db
class TestGetCatalog:
    def test_returns_key_text_map_for_locale(self, client) -> None:
        TranslationFactory(locale="is", key="nav.home", text="Heim")
        TranslationFactory(locale="is", key="nav.about", text="Um okkur")
        TranslationFactory(locale="en", key="nav.home", text="Home")

        response = client.get("/api/i18n/is")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            equal_to({"nav.home": "Heim", "nav.about": "Um okkur"}),
        )

    def test_excludes_retired_rows(self, client) -> None:
        TranslationFactory(locale="is", key="nav.home", text="Heim")
        TranslationFactory(locale="is", key="old.key", text="Gamalt", retired=True)

        response = client.get("/api/i18n/is")

        assert_that(response.status_code, equal_to(200))
        body = response.json()
        assert_that(body, has_entries(**{"nav.home": "Heim"}))
        assert_that(body, is_not(has_key("old.key")))

    def test_unknown_locale_returns_empty(self, client) -> None:
        response = client.get("/api/i18n/xx")
        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), equal_to({}))


@pytest.mark.django_db
class TestGetVersion:
    def test_empty_returns_zero(self, client) -> None:
        response = client.get("/api/i18n/is/version")
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
