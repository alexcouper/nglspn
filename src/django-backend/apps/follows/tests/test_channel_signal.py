import pytest

from apps.follows.models import Channel
from tests.factories import ProjectFactory


@pytest.mark.django_db
class TestDefaultChannelSignal:
    def test_new_project_gets_updates_channel(self):
        project = ProjectFactory()
        channels = list(Channel.objects.filter(project=project))
        assert len(channels) == 1
        assert channels[0].name == "Updates"

    def test_re_saving_project_does_not_duplicate_channel(self):
        project = ProjectFactory()
        project.title = "Renamed"
        project.save()
        assert Channel.objects.filter(project=project, name="Updates").count() == 1

    def test_str_returns_project_title_and_channel_name(self):
        project = ProjectFactory(title="Demo Project")
        channel = Channel.objects.get(project=project, name="Updates")
        assert str(channel) == "Demo Project: Updates"
