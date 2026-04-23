from __future__ import annotations

from django.db import migrations

# (locale, key, text)
SEEDS: list[tuple[str, str, str]] = [
    ("is", "nav.editTranslationsOn", "Þýðingaham: virkur"),
    ("is", "nav.editTranslationsOff", "Breyta þýðingum"),
    ("is", "translatePopover.title", "Breyta þýðingu"),
    ("is", "translatePopover.englishReference", "Enska"),
    ("is", "translatePopover.save", "Vista"),
    ("is", "translatePopover.cancel", "Hætta við"),
    ("is", "translatePopover.saving", "Vistar…"),
    ("is", "translatePopover.history", "Saga"),
    ("is", "translatePopover.revertToThis", "Fara aftur í þetta"),
    ("is", "translatePopover.noHistory", "Engar fyrri breytingar."),
    (
        "is",
        "translatePopover.concurrencyWarning",
        "Þetta var breytt fyrir {seconds} sekúndum af {user}. Vista samt?",
    ),
    ("is", "translatePopover.concurrencyConfirm", "Vista samt"),
    (
        "is",
        "translatePopover.placeholderLost",
        "Ekki breyta eða fjarlægja gulu táknin.",
    ),
    (
        "is",
        "translatePopover.missingTranslationHint",
        "Sýni ensku. Bættu við íslenskri þýðingu með því að breyta þessum streng.",
    ),
]


def seed(apps, schema_editor):
    Translation = apps.get_model("translations", "Translation")
    for locale, key, text in SEEDS:
        Translation.objects.update_or_create(
            locale=locale,
            key=key,
            defaults={
                "text": text,
                "source_hash": "",
                "is_machine_translated": False,
                "retired": False,
            },
        )


def unseed(apps, schema_editor):
    Translation = apps.get_model("translations", "Translation")
    Translation.objects.filter(
        locale="is",
        key__in=[k for _, k, _ in SEEDS],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("translations", "0003_seed_phase2_ui_chrome"),
    ]
    operations = [
        migrations.RunPython(seed, reverse_code=unseed),
    ]
