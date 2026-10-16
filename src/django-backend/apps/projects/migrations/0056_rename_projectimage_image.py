from django.db import migrations


class Migration(migrations.Migration):
    """`ProjectImage` → `Image`: a row can now describe an article without a
    project, so the class and table lose the prefix. Both operations are
    metadata-only on Postgres; the FK columns that point at the table follow
    the rename automatically.
    """

    dependencies = [
        ("projects", "0055_reviewer_group_required"),
    ]

    operations = [
        migrations.RenameModel(old_name="ProjectImage", new_name="Image"),
        migrations.AlterModelTable(name="image", table="images"),
    ]
