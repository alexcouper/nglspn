from pathlib import Path

import pytest
from hamcrest import assert_that, equal_to, has_entries, has_length

from apps.articles.models import Article
from apps.follows.models import Channel
from apps.projects.models import ProjectStatus
from tests.factories import (
    ArticleFactory,
    ChannelFactory,
    ProjectFactory,
)


def _post(client, url, payload, headers=None):
    return client.post(
        url,
        data=payload,
        content_type="application/json",
        **(headers or {}),
    )


def _patch(client, url, payload, headers=None):
    return client.patch(
        url,
        data=payload,
        content_type="application/json",
        **(headers or {}),
    )


@pytest.mark.django_db
class TestListChannels:
    def test_anonymous_can_list(self, client) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        ChannelFactory(project=project, name="News")

        response = client.get(f"/api/projects/{project.id}/channels")

        assert_that(response.status_code, equal_to(200))
        names = sorted(c["name"] for c in response.json())
        assert_that(names, equal_to(["News", "Updates"]))

    def test_unknown_project_returns_404(self, client) -> None:
        response = client.get("/api/projects/does-not-exist/channels")
        assert_that(response.status_code, equal_to(404))

    def test_pending_project_404s_for_anonymous(self, client) -> None:
        project = ProjectFactory(status=ProjectStatus.PENDING)
        ChannelFactory(project=project, name="News")

        response = client.get(f"/api/projects/{project.id}/channels")

        assert_that(response.status_code, equal_to(404))

    def test_pending_project_404s_for_non_editor(self, client, auth_headers) -> None:
        project = ProjectFactory(status=ProjectStatus.PENDING)
        ChannelFactory(project=project, name="News")

        response = client.get(f"/api/projects/{project.id}/channels", **auth_headers)

        assert_that(response.status_code, equal_to(404))

    def test_editor_can_list_on_pending_project(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)
        ChannelFactory(project=project, name="News")

        response = client.get(f"/api/projects/{project.id}/channels", **auth_headers)

        assert_that(response.status_code, equal_to(200))


@pytest.mark.django_db
class TestCreateChannel:
    def test_unauthenticated_returns_401(self, client) -> None:
        project = ProjectFactory()
        response = _post(
            client,
            f"/api/projects/{project.id}/channels",
            {"name": "Press"},
        )
        assert_that(response.status_code, equal_to(401))

    def test_non_full_edit_user_returns_403(self, client, auth_headers) -> None:
        project = ProjectFactory()
        response = _post(
            client,
            f"/api/projects/{project.id}/channels",
            {"name": "Press"},
            auth_headers,
        )
        assert_that(response.status_code, equal_to(403))

    def test_owner_can_create(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user)

        response = _post(
            client,
            f"/api/projects/{project.id}/channels",
            {"name": "Press"},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(201))
        assert_that(response.json(), has_entries(name="Press"))
        assert Channel.objects.filter(project=project, name="Press").exists()

    def test_duplicate_name_returns_409(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user)
        ChannelFactory(project=project, name="Press")

        response = _post(
            client,
            f"/api/projects/{project.id}/channels",
            {"name": "Press"},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(409))


@pytest.mark.django_db
class TestRenameChannel:
    def test_unauthenticated_returns_401(self, client) -> None:
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="News")
        response = _patch(
            client,
            f"/api/projects/{project.id}/channels/{channel.id}",
            {"name": "Press"},
        )
        assert_that(response.status_code, equal_to(401))

    def test_non_full_edit_user_returns_403(self, client, auth_headers) -> None:
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="News")
        response = _patch(
            client,
            f"/api/projects/{project.id}/channels/{channel.id}",
            {"name": "Press"},
            auth_headers,
        )
        assert_that(response.status_code, equal_to(403))

    def test_owner_can_rename(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user)
        channel = ChannelFactory(project=project, name="News")

        response = _patch(
            client,
            f"/api/projects/{project.id}/channels/{channel.id}",
            {"name": "Press"},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(name="Press"))
        channel.refresh_from_db()
        assert_that(channel.name, equal_to("Press"))

    def test_duplicate_name_returns_409(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user)
        ChannelFactory(project=project, name="Press")
        channel = ChannelFactory(project=project, name="News")

        response = _patch(
            client,
            f"/api/projects/{project.id}/channels/{channel.id}",
            {"name": "Press"},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(409))

    def test_channel_on_other_project_returns_404(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        other = ProjectFactory()
        foreign = ChannelFactory(project=other, name="News")

        response = _patch(
            client,
            f"/api/projects/{project.id}/channels/{foreign.id}",
            {"name": "Press"},
            auth_headers,
        )
        assert_that(response.status_code, equal_to(404))


@pytest.mark.django_db
class TestDeleteChannel:
    def test_unauthenticated_returns_401(self, client) -> None:
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="News")
        response = client.delete(f"/api/projects/{project.id}/channels/{channel.id}")
        assert_that(response.status_code, equal_to(401))

    def test_non_full_edit_user_returns_403(self, client, auth_headers) -> None:
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="News")
        response = client.delete(
            f"/api/projects/{project.id}/channels/{channel.id}",
            **auth_headers,
        )
        assert_that(response.status_code, equal_to(403))

    def test_owner_can_delete_empty_non_last_channel(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        channel = ChannelFactory(project=project, name="News")
        # "Updates" is also present from project auto-seed.

        response = client.delete(
            f"/api/projects/{project.id}/channels/{channel.id}",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(204))
        assert not Channel.objects.filter(pk=channel.id).exists()

    def test_delete_channel_with_articles_returns_409(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        channel = ChannelFactory(project=project, name="News")
        ArticleFactory(project=project, channel=channel)

        response = client.delete(
            f"/api/projects/{project.id}/channels/{channel.id}",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(409))
        assert_that(response.json(), has_entries(article_count=1))

    def test_delete_only_channel_returns_409(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user)
        # Drop the auto-seeded sibling to leave one channel.
        Channel.objects.filter(project=project).exclude(name="Updates").delete()
        channel = Channel.objects.get(project=project, name="Updates")

        response = client.delete(
            f"/api/projects/{project.id}/channels/{channel.id}",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(409))


@pytest.mark.django_db
class TestReassignChannel:
    def test_unauthenticated_returns_401(self, client) -> None:
        project = ProjectFactory()
        src = ChannelFactory(project=project, name="News")
        tgt = ChannelFactory(project=project, name="Updates")
        response = _post(
            client,
            f"/api/projects/{project.id}/channels/{src.id}/reassign",
            {"target_channel_id": str(tgt.id)},
        )
        assert_that(response.status_code, equal_to(401))

    def test_non_full_edit_user_returns_403(self, client, auth_headers) -> None:
        project = ProjectFactory()
        src = ChannelFactory(project=project, name="News")
        tgt = ChannelFactory(project=project, name="Updates")
        response = _post(
            client,
            f"/api/projects/{project.id}/channels/{src.id}/reassign",
            {"target_channel_id": str(tgt.id)},
            auth_headers,
        )
        assert_that(response.status_code, equal_to(403))

    def test_owner_can_reassign(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user)
        src = ChannelFactory(project=project, name="News")
        tgt = ChannelFactory(project=project, name="Updates")
        ArticleFactory(project=project, channel=src)
        ArticleFactory(project=project, channel=src)

        response = _post(
            client,
            f"/api/projects/{project.id}/channels/{src.id}/reassign",
            {"target_channel_id": str(tgt.id)},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(reassigned=2))
        assert_that(Article.objects.filter(channel=src), has_length(0))
        assert_that(Article.objects.filter(channel=tgt), has_length(2))

    def test_target_on_other_project_returns_422(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        src = ChannelFactory(project=project, name="News")
        other = ProjectFactory()
        foreign_tgt = ChannelFactory(project=other, name="Updates")

        response = _post(
            client,
            f"/api/projects/{project.id}/channels/{src.id}/reassign",
            {"target_channel_id": str(foreign_tgt.id)},
            auth_headers,
        )
        assert_that(response.status_code, equal_to(422))

    def test_source_on_other_project_returns_404(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        tgt = ChannelFactory(project=project, name="Updates")
        other = ProjectFactory()
        foreign_src = ChannelFactory(project=other, name="News")

        response = _post(
            client,
            f"/api/projects/{project.id}/channels/{foreign_src.id}/reassign",
            {"target_channel_id": str(tgt.id)},
            auth_headers,
        )
        assert_that(response.status_code, equal_to(404))


class TestRouterHasNoOrmAccess:
    """Spec invariant — no direct ORM access in api/routers/channels.py.

    `get_object_or_404` is banned alongside `<Model>.objects` because it takes
    the model class and reaches `_default_manager` itself, so a router can
    query the database without ever writing `.objects`.
    """

    def test_no_direct_orm_access(self) -> None:
        src = Path(__file__).resolve().parent.parent / "routers" / "channels.py"
        text = src.read_text()
        for forbidden in (
            "Article.objects",
            "Channel.objects",
            "FollowedChannel.objects",
            "ProjectImage.objects",
            "get_object_or_404",
        ):
            assert forbidden not in text, (
                f"{forbidden} must not appear in api/routers/channels.py"
            )
