import pytest
from hamcrest import assert_that, equal_to, has_length, is_

from apps.follows.models import Channel, Follow, FollowedChannel
from apps.projects.models import ProjectStatus
from tests.factories import ProjectFactory, make_followed_channel


@pytest.mark.django_db
class TestFollowEndpoint:
    def test_anonymous_post_returns_401(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="approved-project")
        response = client.post(f"/api/projects/{project.slug}/follow")
        assert_that(response.status_code, equal_to(401))

    def test_anonymous_delete_returns_401(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="approved-project")
        response = client.delete(f"/api/projects/{project.slug}/follow")
        assert_that(response.status_code, equal_to(401))

    def test_post_creates_follow_and_enrols_every_channel(
        self, client, user, auth_headers
    ):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="approved-project")
        Channel.objects.create(project=project, name="Releases")

        response = client.post(f"/api/projects/{project.slug}/follow", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        body = response.json()
        assert_that(body["is_followed"], is_(True))
        assert_that(
            Follow.objects.filter(user=user, project=project).exists(), is_(True)
        )
        # Updates (from signal) + Releases (above) = 2 FollowedChannel rows.
        assert_that(
            FollowedChannel.objects.filter(follow__user=user).count(),
            equal_to(2),
        )

    def test_post_is_idempotent(self, client, user, auth_headers):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="approved-project")
        client.post(f"/api/projects/{project.slug}/follow", **auth_headers)
        client.post(f"/api/projects/{project.slug}/follow", **auth_headers)
        assert_that(
            Follow.objects.filter(user=user, project=project).count(), equal_to(1)
        )

    def test_post_does_not_re_enrol_a_channel_the_user_unfollowed(
        self, client, user, auth_headers
    ):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="approved-project")
        releases = Channel.objects.create(project=project, name="Releases")
        client.post(f"/api/projects/{project.slug}/follow", **auth_headers)
        client.delete(
            f"/api/projects/{project.slug}/follow/channels/{releases.id}",
            **auth_headers,
        )

        client.post(f"/api/projects/{project.slug}/follow", **auth_headers)

        assert_that(
            FollowedChannel.objects.filter(
                follow__user=user, channel=releases
            ).exists(),
            is_(False),
        )

    def test_delete_hard_deletes(self, client, user, auth_headers):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="approved-project")
        client.post(f"/api/projects/{project.slug}/follow", **auth_headers)

        response = client.delete(f"/api/projects/{project.slug}/follow", **auth_headers)

        assert_that(response.status_code, equal_to(204))
        assert_that(
            Follow.objects.filter(user=user, project=project).exists(), is_(False)
        )

    def test_delete_when_not_following_is_204(self, client, auth_headers):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="approved-project")
        response = client.delete(f"/api/projects/{project.slug}/follow", **auth_headers)
        assert_that(response.status_code, equal_to(204))

    def test_post_unknown_slug_returns_404(self, client, auth_headers):
        response = client.post("/api/projects/does-not-exist/follow", **auth_headers)
        assert_that(response.status_code, equal_to(404))


@pytest.mark.django_db
class TestProjectResponseIsFollowed:
    def test_anonymous_sees_false(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="approved-project")
        response = client.get(f"/api/projects/{project.slug}")
        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["is_followed"], is_(False))

    def test_unfollowed_user_sees_false(self, client, auth_headers):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="approved-project")
        response = client.get(f"/api/projects/{project.slug}", **auth_headers)
        assert_that(response.json()["is_followed"], is_(False))

    def test_followed_user_sees_true(self, client, user, auth_headers):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="approved-project")
        Follow.objects.create(user=user, project=project)
        response = client.get(f"/api/projects/{project.slug}", **auth_headers)
        assert_that(response.json()["is_followed"], is_(True))


@pytest.mark.django_db
class TestListFollows:
    def test_anonymous_returns_401(self, client):
        response = client.get("/api/follows")
        assert_that(response.status_code, equal_to(401))

    def test_empty_for_user_with_no_follows(self, client, user, auth_headers):
        Follow.objects.filter(user=user).delete()
        response = client.get("/api/follows", **auth_headers)
        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), equal_to([]))

    def test_returns_follows_with_channels(self, client, user, auth_headers):
        Follow.objects.filter(user=user).delete()
        p = ProjectFactory(slug="alpha", title="Alpha", status=ProjectStatus.APPROVED)
        follow = Follow.objects.create(user=user, project=p)
        updates = Channel.objects.get(project=p, name="Updates")
        FollowedChannel.objects.create(follow=follow, channel=updates)

        response = client.get("/api/follows", **auth_headers)

        body = response.json()
        assert_that(body, has_length(1))
        assert_that(body[0]["project_slug"], equal_to("alpha"))
        assert_that(body[0]["project_title"], equal_to("Alpha"))
        assert_that(body[0]["channels"], has_length(1))
        assert_that(body[0]["channels"][0]["channel_name"], equal_to("Updates"))
        assert_that(body[0]["channels"][0]["followed"], is_(True))


@pytest.mark.django_db
class TestGetFollowPreferences:
    def test_anonymous_returns_401(self, client):
        p = ProjectFactory(slug="alpha", status=ProjectStatus.APPROVED)
        response = client.get(f"/api/projects/{p.slug}/follow/preferences")
        assert_that(response.status_code, equal_to(401))

    def test_404_when_not_following(self, client, user, auth_headers):
        Follow.objects.filter(user=user).delete()
        p = ProjectFactory(slug="alpha", status=ProjectStatus.APPROVED)
        response = client.get(
            f"/api/projects/{p.slug}/follow/preferences", **auth_headers
        )
        assert_that(response.status_code, equal_to(404))

    def test_200_returns_channel_follow_state(self, client, user, auth_headers):
        Follow.objects.filter(user=user).delete()
        p = ProjectFactory(slug="alpha", title="Alpha", status=ProjectStatus.APPROVED)
        Channel.objects.create(project=p, name="Releases")
        follow = Follow.objects.create(user=user, project=p)
        updates = Channel.objects.get(project=p, name="Updates")
        FollowedChannel.objects.create(follow=follow, channel=updates)

        response = client.get(
            f"/api/projects/{p.slug}/follow/preferences", **auth_headers
        )

        assert_that(response.status_code, equal_to(200))
        body = response.json()
        assert_that(body["project_slug"], equal_to("alpha"))
        channels = {c["channel_name"]: c for c in body["channels"]}
        assert_that(channels["Updates"]["followed"], is_(True))
        assert_that(channels["Releases"]["followed"], is_(False))


@pytest.mark.django_db
class TestFollowChannelEndpoint:
    def test_anonymous_post_returns_401(self, client):
        p = ProjectFactory(slug="alpha", status=ProjectStatus.APPROVED)
        c = Channel.objects.get(project=p, name="Updates")
        response = client.post(f"/api/projects/{p.slug}/follow/channels/{c.id}")
        assert_that(response.status_code, equal_to(401))

    def test_anonymous_delete_returns_401(self, client):
        p = ProjectFactory(slug="alpha", status=ProjectStatus.APPROVED)
        c = Channel.objects.get(project=p, name="Updates")
        response = client.delete(f"/api/projects/{p.slug}/follow/channels/{c.id}")
        assert_that(response.status_code, equal_to(401))

    def test_post_adds_followed_channel_row(self, client, user, auth_headers):
        Follow.objects.filter(user=user).delete()
        p = ProjectFactory(slug="alpha", status=ProjectStatus.APPROVED)
        Follow.objects.create(user=user, project=p)
        c = Channel.objects.get(project=p, name="Updates")

        response = client.post(
            f"/api/projects/{p.slug}/follow/channels/{c.id}", **auth_headers
        )

        assert_that(response.status_code, equal_to(200))
        body = response.json()
        assert_that(body["followed"], is_(True))
        assert_that(
            FollowedChannel.objects.filter(follow__user=user, channel=c).exists(),
            is_(True),
        )

    def test_post_is_idempotent(self, client, user, auth_headers):
        Follow.objects.filter(user=user).delete()
        p = ProjectFactory(slug="alpha", status=ProjectStatus.APPROVED)
        Follow.objects.create(user=user, project=p)
        c = Channel.objects.get(project=p, name="Updates")

        client.post(f"/api/projects/{p.slug}/follow/channels/{c.id}", **auth_headers)
        client.post(f"/api/projects/{p.slug}/follow/channels/{c.id}", **auth_headers)

        assert_that(
            FollowedChannel.objects.filter(follow__user=user, channel=c).count(),
            equal_to(1),
        )

    def test_delete_removes_followed_channel_row(self, client, user, auth_headers):
        Follow.objects.filter(user=user).delete()
        p = ProjectFactory(slug="alpha", status=ProjectStatus.APPROVED)
        follow = Follow.objects.create(user=user, project=p)
        c = Channel.objects.get(project=p, name="Updates")
        # "Releases" is created after the Follow, so the channel post_save
        # receiver has already enrolled the user in it; the helper is
        # idempotent where a plain create would hit the unique constraint.
        other = Channel.objects.create(project=p, name="Releases")
        make_followed_channel(user, p, c)
        make_followed_channel(user, p, other)

        response = client.delete(
            f"/api/projects/{p.slug}/follow/channels/{c.id}", **auth_headers
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["is_followed"], is_(True))
        assert_that(
            FollowedChannel.objects.filter(follow=follow, channel=c).exists(),
            is_(False),
        )
        # Another channel is still followed, so the Follow row stays.
        assert_that(Follow.objects.filter(user=user, project=p).exists(), is_(True))

    def test_delete_of_last_channel_unfollows_the_project(
        self, client, user, auth_headers
    ):
        Follow.objects.filter(user=user).delete()
        p = ProjectFactory(slug="alpha", status=ProjectStatus.APPROVED)
        follow = Follow.objects.create(user=user, project=p)
        c = Channel.objects.get(project=p, name="Updates")
        FollowedChannel.objects.create(follow=follow, channel=c)

        response = client.delete(
            f"/api/projects/{p.slug}/follow/channels/{c.id}", **auth_headers
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["is_followed"], is_(False))
        assert_that(Follow.objects.filter(user=user, project=p).exists(), is_(False))

    def test_delete_is_idempotent_while_other_channels_remain(
        self, client, user, auth_headers
    ):
        Follow.objects.filter(user=user).delete()
        p = ProjectFactory(slug="alpha", status=ProjectStatus.APPROVED)
        Follow.objects.create(user=user, project=p)
        c = Channel.objects.get(project=p, name="Updates")
        # Enrolled in "Releases" only: it postdates the Follow so the receiver
        # covers it, while "Updates" predates the Follow and stays unfollowed.
        other = Channel.objects.create(project=p, name="Releases")
        make_followed_channel(user, p, other)

        client.delete(f"/api/projects/{p.slug}/follow/channels/{c.id}", **auth_headers)
        response = client.delete(
            f"/api/projects/{p.slug}/follow/channels/{c.id}", **auth_headers
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["is_followed"], is_(True))

    def test_delete_after_project_unfollowed_returns_404(
        self, client, user, auth_headers
    ):
        Follow.objects.filter(user=user).delete()
        p = ProjectFactory(slug="alpha", status=ProjectStatus.APPROVED)
        follow = Follow.objects.create(user=user, project=p)
        c = Channel.objects.get(project=p, name="Updates")
        FollowedChannel.objects.create(follow=follow, channel=c)

        client.delete(f"/api/projects/{p.slug}/follow/channels/{c.id}", **auth_headers)
        response = client.delete(
            f"/api/projects/{p.slug}/follow/channels/{c.id}", **auth_headers
        )

        assert_that(response.status_code, equal_to(404))

    def test_post_when_not_following_returns_404(self, client, user, auth_headers):
        Follow.objects.filter(user=user).delete()
        p = ProjectFactory(slug="alpha", status=ProjectStatus.APPROVED)
        c = Channel.objects.get(project=p, name="Updates")

        response = client.post(
            f"/api/projects/{p.slug}/follow/channels/{c.id}", **auth_headers
        )

        assert_that(response.status_code, equal_to(404))

    def test_post_when_channel_on_wrong_project_returns_404(
        self, client, user, auth_headers
    ):
        Follow.objects.filter(user=user).delete()
        p = ProjectFactory(slug="alpha", status=ProjectStatus.APPROVED)
        other = ProjectFactory(slug="beta", status=ProjectStatus.APPROVED)
        Follow.objects.create(user=user, project=p)
        wrong = Channel.objects.get(project=other, name="Updates")

        response = client.post(
            f"/api/projects/{p.slug}/follow/channels/{wrong.id}", **auth_headers
        )

        assert_that(response.status_code, equal_to(404))
