from unittest.mock import patch

import pytest
from hamcrest import assert_that, equal_to

from apps.translations.models import Translation, TranslationAudit
from services.translations.django_impl.handler import DjangoTranslationHandler
from tests.factories import TranslationFactory, UserFactory


@pytest.mark.django_db
class TestUpdateText:
    def setup_method(self) -> None:
        self.handler = DjangoTranslationHandler()

    def test_updates_existing_row_and_flips_mt_flag(self) -> None:
        user = UserFactory()
        t = TranslationFactory(
            locale="is",
            key="nav.home",
            text="Heim",
            is_machine_translated=True,
        )
        with patch("services.translations.django_impl.handler.notify_web_ui") as notify:
            result = self.handler.update_text(
                locale="is", key="nav.home", text="Forsíða", user=user
            )

        t.refresh_from_db()
        assert_that(t.text, equal_to("Forsíða"))
        assert_that(t.is_machine_translated, equal_to(False))
        assert_that(t.updated_by, equal_to(user))
        assert_that(result.pk, equal_to(t.pk))
        notify.assert_called_once_with("is")

    def test_writes_audit_entry(self) -> None:
        user = UserFactory()
        t = TranslationFactory(locale="is", key="nav.home", text="Heim")
        with patch("services.translations.django_impl.handler.notify_web_ui"):
            self.handler.update_text(
                locale="is", key="nav.home", text="Forsíða", user=user
            )
        audit = (
            TranslationAudit.objects.filter(translation=t)
            .order_by("-changed_at")
            .first()
        )
        assert_that(audit.old_text, equal_to("Heim"))
        assert_that(audit.new_text, equal_to("Forsíða"))
        assert_that(audit.changed_by, equal_to(user))

    def test_creates_row_if_missing(self) -> None:
        user = UserFactory()
        with patch("services.translations.django_impl.handler.notify_web_ui"):
            result = self.handler.update_text(
                locale="is", key="new.key", text="Nýtt", user=user
            )
        t = Translation.objects.get(locale="is", key="new.key")
        assert_that(t.text, equal_to("Nýtt"))
        assert_that(t.updated_by, equal_to(user))
        assert_that(t.is_machine_translated, equal_to(False))
        assert_that(result.pk, equal_to(t.pk))

    def test_webhook_failure_does_not_fail_update(self) -> None:
        user = UserFactory()
        TranslationFactory(locale="is", key="nav.home", text="Heim")
        with patch(
            "services.translations.django_impl.handler.notify_web_ui",
            side_effect=Exception("boom"),
        ):
            self.handler.update_text(
                locale="is", key="nav.home", text="Forsíða", user=user
            )
        t = Translation.objects.get(locale="is", key="nav.home")
        assert_that(t.text, equal_to("Forsíða"))
