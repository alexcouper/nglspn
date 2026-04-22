import hashlib

import pytest
from django.db.utils import IntegrityError
from hamcrest import assert_that, equal_to, is_not, none

from apps.translations.models import Translation, TranslationAudit
from tests.factories import TranslationFactory, UserFactory


@pytest.mark.django_db
class TestTranslationModel:
    def test_create_translation(self) -> None:
        t = Translation.objects.create(
            locale="is",
            key="home.hero.title",
            text="Velkomin",
            source_hash=hashlib.sha256(b"Welcome").hexdigest(),
        )
        assert_that(t.pk, is_not(none()))
        assert_that(t.is_machine_translated, equal_to(False))
        assert_that(t.retired, equal_to(False))

    def test_locale_key_uniqueness(self) -> None:
        Translation.objects.create(
            locale="is", key="nav.home", text="Heim", source_hash="abc"
        )
        with pytest.raises(IntegrityError):
            Translation.objects.create(
                locale="is", key="nav.home", text="Aftur heim", source_hash="abc"
            )

    def test_same_key_different_locales_allowed(self) -> None:
        Translation.objects.create(
            locale="en", key="nav.home", text="Home", source_hash="abc"
        )
        Translation.objects.create(
            locale="is", key="nav.home", text="Heim", source_hash="abc"
        )
        assert_that(Translation.objects.count(), equal_to(2))


@pytest.mark.django_db
class TestAuditWriteOnSave:
    def test_create_writes_audit_with_null_old_text(self) -> None:
        user = UserFactory()
        t = Translation.objects.create(
            locale="is",
            key="nav.home",
            text="Heim",
            source_hash="abc",
            updated_by=user,
        )
        audits = TranslationAudit.objects.filter(translation=t)
        assert_that(audits.count(), equal_to(1))
        entry = audits.get()
        assert_that(entry.old_text, equal_to(""))
        assert_that(entry.new_text, equal_to("Heim"))
        assert_that(entry.changed_by, equal_to(user))
        assert_that(entry.locale, equal_to("is"))
        assert_that(entry.key, equal_to("nav.home"))

    def test_update_writes_audit_with_previous_text(self) -> None:
        user1 = UserFactory()
        user2 = UserFactory()
        t = TranslationFactory(text="Heim", updated_by=user1)
        t.text = "Forsíða"
        t.updated_by = user2
        t.save()

        audits = TranslationAudit.objects.filter(translation=t).order_by("changed_at")
        assert_that(audits.count(), equal_to(2))
        latest = audits.last()
        assert_that(latest.old_text, equal_to("Heim"))
        assert_that(latest.new_text, equal_to("Forsíða"))
        assert_that(latest.changed_by, equal_to(user2))

    def test_no_audit_when_text_unchanged(self) -> None:
        t = TranslationFactory(text="Heim")
        t.is_machine_translated = True
        t.save()
        assert_that(TranslationAudit.objects.filter(translation=t).count(), equal_to(1))
