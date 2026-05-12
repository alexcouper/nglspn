from django.db import migrations, models
from django.utils import timezone


def mark_existing_read_and_dedupe(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")

    seen: set[tuple[str, str]] = set()
    duplicate_ids: list = []
    for row in Notification.objects.order_by("created_at", "id").values_list(
        "id", "recipient_id", "discussion_id"
    ):
        notif_id, recipient_id, discussion_id = row
        key = (str(recipient_id), str(discussion_id))
        if key in seen:
            duplicate_ids.append(notif_id)
        else:
            seen.add(key)
    if duplicate_ids:
        Notification.objects.filter(id__in=duplicate_ids).delete()

    Notification.objects.filter(in_app_read_at__isnull=True).update(
        in_app_read_at=timezone.now()
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0002_in_app_notifications"),
    ]

    operations = [
        migrations.RunPython(mark_existing_read_and_dedupe, noop_reverse),
        migrations.AddConstraint(
            model_name="notification",
            constraint=models.UniqueConstraint(
                fields=("recipient", "discussion"),
                name="notifications_recip_disc_uniq",
            ),
        ),
    ]
