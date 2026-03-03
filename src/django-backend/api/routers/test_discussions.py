import pytest
from hamcrest import assert_that, equal_to, has_entries, has_length

from apps.projects.models import ProjectStatus
from tests.factories import DiscussionFactory, ProjectFactory, UserFactory


@pytest.mark.django_db
class TestListDiscussions:
    def test_unauthenticated_returns_401(self, client) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        response = client.get(f"/api/projects/{project.id}/discussions")
        assert_that(response.status_code, equal_to(401))

    def test_returns_root_discussions_with_replies(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        root = DiscussionFactory(project=project, author=user)
        DiscussionFactory(project=project, author=user, parent=root)

        response = client.get(f"/api/projects/{project.id}/discussions", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        data = response.json()
        assert_that(data, has_length(1))
        assert_that(data[0]["replies"], has_length(1))

    def test_returns_empty_list_for_no_discussions(self, client, auth_headers) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        response = client.get(f"/api/projects/{project.id}/discussions", **auth_headers)
        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_length(0))


@pytest.mark.django_db
class TestCreateDiscussion:
    def test_unauthenticated_returns_401(self, client) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        response = client.post(
            f"/api/projects/{project.id}/discussions",
            data={"body": "hello"},
            content_type="application/json",
        )
        assert_that(response.status_code, equal_to(401))

    def test_creates_root_discussion(self, client, user, auth_headers) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        response = client.post(
            f"/api/projects/{project.id}/discussions",
            data={"body": "Great project!"},
            content_type="application/json",
            **auth_headers,
        )
        assert_that(response.status_code, equal_to(201))
        assert_that(
            response.json(),
            has_entries(
                body="Great project!",
                author=has_entries(id=str(user.id)),
            ),
        )

    def test_discussion_response_includes_author_info(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        response = client.post(
            f"/api/projects/{project.id}/discussions",
            data={"body": "test"},
            content_type="application/json",
            **auth_headers,
        )
        author = response.json()["author"]
        assert_that(
            author,
            has_entries(
                id=str(user.id),
                first_name=user.first_name,
                last_name=user.last_name,
            ),
        )


@pytest.mark.django_db
class TestReplyToDiscussion:
    def test_creates_reply(self, client, user, auth_headers) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        root = DiscussionFactory(project=project)

        response = client.post(
            f"/api/projects/{project.id}/discussions/{root.id}/replies",
            data={"body": "Nice point!"},
            content_type="application/json",
            **auth_headers,
        )
        assert_that(response.status_code, equal_to(201))
        assert_that(response.json(), has_entries(body="Nice point!"))

    def test_reply_to_nonexistent_discussion_returns_404(
        self, client, auth_headers
    ) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            f"/api/projects/{project.id}/discussions/{fake_id}/replies",
            data={"body": "hello"},
            content_type="application/json",
            **auth_headers,
        )
        assert_that(response.status_code, equal_to(404))


@pytest.mark.django_db
class TestDeleteDiscussion:
    def test_author_can_delete_own_discussion(self, client, user, auth_headers) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        discussion = DiscussionFactory(project=project, author=user)

        response = client.delete(
            f"/api/projects/{project.id}/discussions/{discussion.id}",
            **auth_headers,
        )
        assert_that(response.status_code, equal_to(204))

    def test_other_user_cannot_delete_discussion(self, client, auth_headers) -> None:
        other = UserFactory()
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        discussion = DiscussionFactory(project=project, author=other)

        response = client.delete(
            f"/api/projects/{project.id}/discussions/{discussion.id}",
            **auth_headers,
        )
        assert_that(response.status_code, equal_to(403))

    def test_delete_nonexistent_returns_404(self, client, auth_headers) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.delete(
            f"/api/projects/{project.id}/discussions/{fake_id}",
            **auth_headers,
        )
        assert_that(response.status_code, equal_to(404))

    def test_unauthenticated_returns_401(self, client) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        discussion = DiscussionFactory(project=project)
        response = client.delete(
            f"/api/projects/{project.id}/discussions/{discussion.id}",
        )
        assert_that(response.status_code, equal_to(401))
