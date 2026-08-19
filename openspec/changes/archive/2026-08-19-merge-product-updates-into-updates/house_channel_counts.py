"""Report house-project channel shape: articles and followers per channel.

Read-only. Run before and after `manage.py migrate` to verify the merge:

    uv run python manage.py shell < house_channel_counts.py
"""

from apps.articles.models import Article
from apps.follows.models import Follow, FollowedChannel
from apps.projects.models import Project

house = Project.objects.filter(is_house_project=True).first()
if house is None:
    print("no house project")
else:
    print(f"house project: {house.slug} ({house.title})")
    for channel in house.channels.order_by("name"):
        print(
            f"  {channel.name!r}: "
            f"articles={Article.objects.filter(channel=channel).count()} "
            f"followers={FollowedChannel.objects.filter(channel=channel).count()}"
        )
    follows = Follow.objects.filter(project=house)
    empty = sum(1 for f in follows if not f.followed_channels.exists())
    print(f"  follows={follows.count()} of which empty={empty}")
