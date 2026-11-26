from django.db import migrations

# Duplicated rather than imported from apps.articles.models, as in 0008: the
# migration keeps the vocabulary it shipped with.
GLOBALLY_VISIBLE_STATES = ("auto", "approved")
REVIEWS_CHANNEL_NAME = "Reviews"


def spotlight_house_reviews(apps, schema_editor):
    Article = apps.get_model("articles", "Article")
    Project = apps.get_model("projects", "Project")

    house = Project.objects.filter(is_house_project=True).first()
    if house is None:
        return
    Article.objects.filter(
        project=house,
        channel__name=REVIEWS_CHANNEL_NAME,
        state="published",
        global_visibility__in=GLOBALLY_VISIBLE_STATES,
    ).update(is_spotlight=True)


class Migration(migrations.Migration):
    dependencies = [
        ("articles", "0012_article_front_page_fields"),
        ("follows", "0007_channel_owner_follow_followed_user"),
        ("projects", "0057_image_project_nullable"),
    ]

    operations = [
        # Reversing leaves the flags; dropping the field removes them.
        migrations.RunPython(spotlight_house_reviews, migrations.RunPython.noop),
    ]
