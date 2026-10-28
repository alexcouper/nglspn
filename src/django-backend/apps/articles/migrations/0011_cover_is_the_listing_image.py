from django.db import migrations


def drop_derived_listing_images(apps, schema_editor):
    """An article's listing image is now the cover its author picked. One that
    `auto` mode derived from the first upload was never a choice, and it is
    usually the first image in the body, so those articles go to no cover —
    a text-only card and a page that opens with the body."""
    Article = apps.get_model("articles", "Article")
    Article.objects.filter(listing_image_mode="auto").update(
        listing_image=None, listing_crop=None
    )


class Migration(migrations.Migration):
    dependencies = [
        ("articles", "0010_author_owned_articles"),
    ]

    operations = [
        migrations.RunPython(drop_derived_listing_images, migrations.RunPython.noop),
        migrations.RemoveField(model_name="article", name="listing_image_mode"),
    ]
