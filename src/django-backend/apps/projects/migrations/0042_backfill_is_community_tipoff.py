from django.db import migrations, transaction


def backfill_is_community_tipoff(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    ProjectContributor = apps.get_model("projects", "ProjectContributor")
    User = apps.get_model("users", "User")

    with transaction.atomic():
        system_user_ids = list(
            User.objects.filter(is_system_user=True).values_list("id", flat=True)
        )
        if not system_user_ids:
            return

        tipoff_project_ids = ProjectContributor.objects.filter(
            role="owner",
            user_id__in=system_user_ids,
        ).values_list("project_id", flat=True)

        Project.objects.filter(id__in=list(tipoff_project_ids)).update(
            is_community_tipoff=True,
        )


def reset_is_community_tipoff(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    Project.objects.update(is_community_tipoff=False)


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0041_project_is_community_tipoff"),
        ("users", "0014_user_is_system_user"),
    ]

    operations = [
        migrations.RunPython(
            backfill_is_community_tipoff,
            reverse_code=reset_is_community_tipoff,
        ),
    ]
