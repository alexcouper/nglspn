import pytest
from hamcrest import assert_that, equal_to, is_

from apps.follows.models import Channel, Follow, FollowChannelPreference
from apps.projects.models import ProjectStatus
from tests.factories import ProjectFactory


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

    def test_post_creates_follow_and_prefs(self, client, user, auth_headers):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="approved-project")
        Channel.objects.create(project=project, name="Releases")

        response = client.post(f"/api/projects/{project.slug}/follow", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        body = response.json()
        assert_that(body["is_followed"], is_(True))
        assert_that(
            Follow.objects.filter(user=user, project=project).exists(), is_(True)
        )
        # Updates (from signal) + Releases (above) = 2 prefs.
        assert_that(
            FollowChannelPreference.objects.filter(follow__user=user).count(),
            equal_to(2),
        )

    def test_post_is_idempotent(self, client, user, auth_headers):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="approved-project")
        client.post(f"/api/projects/{project.slug}/follow", **auth_headers)
        client.post(f"/api/projects/{project.slug}/follow", **auth_headers)
        assert_that(
            Follow.objects.filter(user=user, project=project).count(), equal_to(1)
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
