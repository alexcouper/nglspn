from django.db import migrations, models


class Migration(migrations.Migration):
    """State-only rename: FollowChannelPreference → FollowedChannel.

    The underlying table is pinned to `follow_channel_preferences` via
    `Meta.db_table`, so this migration emits no SQL beyond the related-name
    update on the FK. Rows are untouched. Subsequent migrations (0004 sweep,
    0005 column drop) operate on the renamed model.
    """

    dependencies = [
        ("follows", "0002_seed_channels_and_house_follows"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="FollowChannelPreference",
            new_name="FollowedChannel",
        ),
        migrations.AlterField(
            model_name="followedchannel",
            name="follow",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name="followed_channels",
                to="follows.follow",
            ),
        ),
    ]
