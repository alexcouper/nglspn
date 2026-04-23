from __future__ import annotations

from django.db import migrations

SEEDS: list[tuple[str, str, str]] = [
    ("is", "error.loginFailed", "Innskráning tókst ekki"),
    ("is", "error.somethingWentWrong", "Eitthvað fór úrskeiðis"),
    ("is", "error.verificationFailed", "Staðfesting tókst ekki"),
    (
        "is",
        "error.verificationFailedRetry",
        "Staðfesting tókst ekki. Vinsamlegast reyndu aftur.",
    ),
    ("is", "error.registrationFailed", "Skráning tókst ekki"),
    ("is", "error.resetPasswordFailed", "Mistókst að endurstilla lykilorð"),
    ("is", "error.resendCodeFailed", "Mistókst að senda kóða aftur"),
    ("is", "error.saveFailed", "Mistókst að vista. Vinsamlegast reyndu aftur."),
    ("is", "error.updateProfileFailed", "Mistókst að uppfæra prófíl"),
    ("is", "error.submitProjectFailed", "Mistókst að senda inn verkefni"),
    ("is", "error.loadProjectFailed", "Mistókst að sækja verkefni"),
    ("is", "error.saveProjectFailed", "Mistókst að vista verkefni"),
    ("is", "error.publishProjectFailed", "Mistókst að birta verkefni"),
    ("is", "error.deleteProjectFailed", "Mistókst að eyða verkefni"),
    ("is", "error.updateImageRolesFailed", "Mistókst að uppfæra hlutverk mynda"),
    ("is", "error.deleteIconFailed", "Mistókst að eyða tákni"),
    ("is", "error.deleteImageFailed", "Mistókst að eyða mynd"),
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
        ("translations", "0005_seed_phase4_sweep"),
    ]
    operations = [
        migrations.RunPython(seed, reverse_code=unseed),
    ]
