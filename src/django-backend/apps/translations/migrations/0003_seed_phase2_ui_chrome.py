from django.db import migrations


# Mirror of the keys used by Navigation + Footer in the web-ui.
# Phase 3 replaces this hand-written seed with an auto-generated migration
# produced by `make translate-new-keys`.
IS_CHROME = {
    "nav.projects": "Verkefni",
    "nav.competitions": "Keppnir",
    "nav.continueOnboarding": "Halda áfram með undirbúning",
    "nav.myProjects": "Mín verkefni",
    "nav.myReviews": "Mínar umsagnir",
    "nav.login": "Innskráning",
    "nav.register": "Nýskráning",
    "nav.profile": "Prófíll",
    "nav.logout": "Útskráning",
    "footer.about": "Um okkur",
    "footer.privacy": "Persónuvernd",
    "footer.discord": "Discord",
}


def seed(apps, schema_editor):
    Translation = apps.get_model("translations", "Translation")
    for key, text in IS_CHROME.items():
        Translation.objects.update_or_create(
            locale="is",
            key=key,
            defaults={
                "text": text,
                "source_hash": "",
                "is_machine_translated": True,
                "retired": False,
            },
        )


def unseed(apps, schema_editor):
    Translation = apps.get_model("translations", "Translation")
    Translation.objects.filter(locale="is", key__in=list(IS_CHROME)).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("translations", "0002_translationaudit"),
    ]
    operations = [migrations.RunPython(seed, unseed)]
