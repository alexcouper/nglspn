import pytest
from hamcrest import assert_that, equal_to, has_entries, has_key, is_not

from services.translations.django_impl.query import DjangoTranslationQuery
from tests.factories import TranslationFactory


@pytest.mark.django_db
class TestGetCatalog:
    def setup_method(self) -> None:
        self.query = DjangoTranslationQuery()

    def test_returns_key_text_map_for_locale(self) -> None:
        TranslationFactory(locale="is", key="custom.key", text="Custom")
        TranslationFactory(locale="en", key="nav.home", text="Home")

        result = self.query.get_catalog("is")

        # Should include seeded chrome keys + custom key
        assert_that(
            result,
            has_entries(**{"custom.key": "Custom", "nav.projects": "Verkefni"}),
        )

    def test_excludes_retired_rows(self) -> None:
        TranslationFactory(locale="is", key="custom.old", text="Gamalt", retired=True)

        result = self.query.get_catalog("is")

        assert_that(result, has_entries(**{"nav.projects": "Verkefni"}))
        assert_that(result, is_not(has_key("custom.old")))

    def test_unknown_locale_returns_empty(self) -> None:
        assert_that(self.query.get_catalog("xx"), equal_to({}))


@pytest.mark.django_db
class TestGetCatalogVersion:
    def setup_method(self) -> None:
        self.query = DjangoTranslationQuery()

    def test_empty_returns_zero(self) -> None:
        assert_that(self.query.get_catalog_version("xx"), equal_to(0))

    def test_returns_max_updated_at_as_epoch(self) -> None:
        t = TranslationFactory(locale="is", key="nav.home", text="Heim")
        assert_that(
            self.query.get_catalog_version("is"),
            equal_to(int(t.updated_at.timestamp())),
        )

    def test_scoped_by_locale(self) -> None:
        TranslationFactory(locale="is", key="a", text="A-is")
        en = TranslationFactory(locale="en", key="b", text="B-en")

        assert_that(
            self.query.get_catalog_version("en"),
            equal_to(int(en.updated_at.timestamp())),
        )
