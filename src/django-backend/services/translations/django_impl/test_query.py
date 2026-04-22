import pytest
from hamcrest import assert_that, equal_to, has_entries, has_key, is_not

from services.translations.django_impl.query import DjangoTranslationQuery
from tests.factories import TranslationFactory


@pytest.mark.django_db
class TestGetCatalog:
    def setup_method(self) -> None:
        self.query = DjangoTranslationQuery()

    def test_returns_key_text_map_for_locale(self) -> None:
        TranslationFactory(locale="is", key="nav.home", text="Heim")
        TranslationFactory(locale="is", key="nav.about", text="Um okkur")
        TranslationFactory(locale="en", key="nav.home", text="Home")

        result = self.query.get_catalog("is")

        assert_that(result, equal_to({"nav.home": "Heim", "nav.about": "Um okkur"}))

    def test_excludes_retired_rows(self) -> None:
        TranslationFactory(locale="is", key="nav.home", text="Heim")
        TranslationFactory(locale="is", key="old.key", text="Gamalt", retired=True)

        result = self.query.get_catalog("is")

        assert_that(result, has_entries(**{"nav.home": "Heim"}))
        assert_that(result, is_not(has_key("old.key")))

    def test_unknown_locale_returns_empty(self) -> None:
        assert_that(self.query.get_catalog("xx"), equal_to({}))


@pytest.mark.django_db
class TestGetCatalogVersion:
    def setup_method(self) -> None:
        self.query = DjangoTranslationQuery()

    def test_empty_returns_zero(self) -> None:
        assert_that(self.query.get_catalog_version("is"), equal_to(0))

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
