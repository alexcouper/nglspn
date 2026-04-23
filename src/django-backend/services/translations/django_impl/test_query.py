import pytest
from hamcrest import (
    assert_that,
    equal_to,
    has_entries,
    has_key,
    has_length,
    is_not,
    none,
    not_none,
)

from services.translations.django_impl.query import DjangoTranslationQuery
from tests.factories import TranslationFactory, UserFactory


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


@pytest.mark.django_db
class TestGetDetail:
    def setup_method(self) -> None:
        self.query = DjangoTranslationQuery()

    def test_returns_text_and_updated_at_for_existing_row(self) -> None:
        t = TranslationFactory(locale="is", key="nav.home", text="Heim")

        detail = self.query.get_detail("is", "nav.home")

        assert_that(detail.text, equal_to("Heim"))
        assert_that(detail.updated_at, equal_to(t.updated_at))

    def test_returns_empty_for_missing_row(self) -> None:
        detail = self.query.get_detail("is", "nonexistent.key")

        assert_that(detail.text, equal_to(""))
        assert_that(detail.updated_at, none())
        assert_that(detail.history, equal_to([]))

    def test_history_is_newest_first_and_capped(self) -> None:
        user = UserFactory(first_name="Alice", last_name="A")
        t = TranslationFactory(
            locale="is", key="nav.home", text="Heim", updated_by=user
        )
        # Trigger 3 audits via the .save hook.
        for new_text in ["Forsida", "Forsíða", "Heim"]:
            t.text = new_text
            t.updated_by = user
            t.save()

        detail = self.query.get_detail("is", "nav.home", history_limit=2)

        assert_that(detail.history, has_length(2))
        assert_that(detail.history[0].new_text, equal_to("Heim"))
        assert_that(detail.history[1].new_text, equal_to("Forsíða"))
        assert_that(detail.history[0].changed_by, not_none())

    def test_history_changed_by_null_for_system_edits(self) -> None:
        t = TranslationFactory(locale="is", key="nav.home", text="Heim")
        # No user attached → system edit
        t.text = "Forsíða"
        t.updated_by = None
        t.save()

        detail = self.query.get_detail("is", "nav.home")

        assert_that(detail.history[0].changed_by, none())
