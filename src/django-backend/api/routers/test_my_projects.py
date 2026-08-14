import json
from unittest.mock import patch

from hamcrest import (
    assert_that,
    contains_inanyorder,
    equal_to,
    has_entries,
    has_key,
    has_length,
    is_,
    none,
)

from apps.projects.models import (
    CompetitionEntry,
    CompetitionStatus,
    ContributorRole,
    EntrySource,
    Project,
    ProjectContributor,
    ProjectStatus,
)
from apps.users.seed import COMMUNITY_USER_ID
from services import REPO
from services.project.django_impl import DjangoProjectQuery
from services.project.query_interface import (
    CompetitionOpportunity,
    CompetitionStanding,
)
from tests.factories import (
    CompetitionEntryFactory,
    CompetitionFactory,
    ProjectFactory,
    ProjectImageFactory,
)


def _ready_draft(**kwargs):
    project = ProjectFactory(
        status=ProjectStatus.DRAFT,
        title=kwargs.pop("title", "Ready Draft"),
        description=kwargs.pop("description", "A description"),
        submission_month="",
        slug=None,
        published_at=None,
        **kwargs,
    )
    ProjectImageFactory(project=project, is_main=True, upload_status="uploaded")
    return project


class TestListMyProjects:
    def test_list_my_projects_returns_owned_projects(
        self,
        client,
        user,
        auth_headers,
    ) -> None:
        ProjectFactory.create_batch(3, owner=user)
        ProjectFactory()  # Another user's project

        response = client.get("/api/my/projects", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_length(3))

    def test_excludes_projects_where_user_is_only_tipster(
        self,
        client,
        user,
        auth_headers,
    ) -> None:
        # /my-projects is creator-scoped; TIPSTER-only projects belong in
        # /tip-offs.
        project = ProjectFactory()  # owned by someone else
        ProjectContributor.objects.create(
            project=project,
            user=user,
            role=ContributorRole.TIPSTER,
            full_edit=True,
        )

        response = client.get("/api/my/projects", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_length(0))


class TestListMyTipOffs:
    def test_empty_when_no_tip_offs(self, client, user, auth_headers) -> None:
        ProjectFactory(owner=user)  # self-owned

        response = client.get("/api/my/projects/tip-offs", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_length(0))

    def test_returns_community_tip_off_projects(
        self, client, user, auth_headers
    ) -> None:
        # A community tip-off: seed user is OWNER, calling user is TIPSTER.
        seed = REPO.users.get_community_user()
        project = ProjectFactory(creator=user, _contributor=False)
        ProjectContributor.objects.create(
            project=project, user=seed, role=ContributorRole.OWNER, full_edit=True
        )
        ProjectContributor.objects.create(
            project=project,
            user=user,
            role=ContributorRole.TIPSTER,
            full_edit=True,
        )

        response = client.get("/api/my/projects/tip-offs", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_length(1))
        assert_that(
            response.json()[0],
            has_entries(id=str(project.id)),
        )

    def test_excludes_tipster_with_full_edit_disabled(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory()  # owned by someone else
        ProjectContributor.objects.create(
            project=project,
            user=user,
            role=ContributorRole.TIPSTER,
            full_edit=False,
        )

        response = client.get("/api/my/projects/tip-offs", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_length(0))

    def test_requires_authentication(self, client, db) -> None:
        response = client.get("/api/my/projects/tip-offs")

        assert_that(response.status_code, equal_to(401))


class TestCommunityTipoffCreate:
    def test_tipoff_flag_creates_seed_owner_and_tipster(
        self, client, user, auth_headers
    ) -> None:
        payload = {
            "website_url": "https://made-by-someone-else.com",
            "description": "A cool community tip-off project",
            "is_community_tipoff": True,
        }

        response = client.post(
            "/api/my/projects",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(201))
        body = response.json()
        seed = REPO.users.get_community_user()
        roles = {c["user"]["id"]: c["role"] for c in body["contributors"]}
        assert_that(roles[str(seed.id)], equal_to("owner"))
        assert_that(roles[str(user.id)], equal_to("tipster"))
        assert_that(body["creator"]["id"], equal_to(str(user.id)))

    def test_default_omitted_creates_self_owned(
        self, client, user, auth_headers
    ) -> None:
        payload = {
            "website_url": "https://my-own-project.com",
            "description": "Self-owned",
        }

        response = client.post(
            "/api/my/projects",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(201))
        body = response.json()
        assert_that(body["contributors"], has_length(1))
        assert_that(body["contributors"][0]["role"], equal_to("owner"))
        assert_that(body["contributors"][0]["user"]["id"], equal_to(str(user.id)))


class TestCreateProject:
    def test_create_project_with_url(self, client, user, auth_headers) -> None:
        payload = {"website_url": "https://example.com", "description": "My project"}

        response = client.post(
            "/api/my/projects",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(201))
        body = response.json()
        assert_that(
            body,
            has_entries(
                website_url="https://example.com",
                title="example.com",
                owner=has_entries(id=str(user.id)),
                creator=has_entries(id=str(user.id)),
            ),
        )
        assert_that(body["contributors"], has_length(1))
        assert_that(
            body["contributors"][0],
            has_entries(
                user=has_entries(id=str(user.id)),
                role="owner",
                full_edit=True,
            ),
        )

    def test_create_project_with_all_fields(
        self,
        client,
        user,
        auth_headers,
        tags,
    ) -> None:
        payload = {
            "website_url": "https://myproject.com",
            "title": "My Project",
            "description": "A great project",
            "tag_ids": [str(t.id) for t in tags],
        }

        response = client.post(
            "/api/my/projects",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(201))
        assert_that(
            response.json(),
            has_entries(
                title="My Project",
                description="A great project",
                tags=has_length(3),
            ),
        )


class TestGetMyProject:
    def test_get_my_project(self, client, project, auth_headers) -> None:
        response = client.get(f"/api/my/projects/{project.id}", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(id=str(project.id)))


class TestUpdateProject:
    def test_update_project(self, client, project, auth_headers) -> None:
        payload = {
            "website_url": "https://updated.com",
            "title": "Updated Title",
            "description": "Updated description",
        }

        response = client.put(
            f"/api/my/projects/{project.id}",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(title="Updated Title", website_url="https://updated.com"),
        )

    def test_update_rejected_project_resets_status(
        self,
        client,
        user,
        auth_headers,
    ) -> None:
        project = ProjectFactory(
            owner=user,
            status=ProjectStatus.REJECTED,
            rejection_reason="Bad project",
        )
        payload = {
            "website_url": "https://fixed.com",
            "title": "Fixed Project",
            "description": "Updated",
        }

        response = client.put(
            f"/api/my/projects/{project.id}",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        project.refresh_from_db()
        assert_that(project.status, equal_to(ProjectStatus.PENDING))
        assert_that(project.rejection_reason, is_(none()))


class TestDeleteProject:
    def test_delete_project(self, client, project, auth_headers) -> None:
        project_id = project.id

        response = client.delete(f"/api/my/projects/{project_id}", **auth_headers)

        assert_that(response.status_code, equal_to(204))
        assert_that(Project.objects.filter(id=project_id).exists(), is_(False))


class TestResubmitProject:
    def test_resubmit_rejected_project(self, client, user, auth_headers) -> None:
        project = ProjectFactory(
            owner=user,
            status=ProjectStatus.REJECTED,
            rejection_reason="Try again",
        )

        response = client.post(
            f"/api/my/projects/{project.id}/resubmit",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        project.refresh_from_db()
        assert_that(project.status, equal_to(ProjectStatus.PENDING))
        assert_that(project.rejection_reason, is_(none()))

    def test_resubmit_non_rejected_project_fails(
        self,
        client,
        project,
        auth_headers,
    ) -> None:
        response = client.post(
            f"/api/my/projects/{project.id}/resubmit",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))


class TestPublishProject:
    def test_publish_ready_draft_returns_200_with_slug(
        self, client, user, auth_headers
    ) -> None:
        project = _ready_draft(owner=user, title="Shiny App")

        with patch("api.tasks.email.send_new_project_notification"):
            response = client.post(
                f"/api/my/projects/{project.id}/publish",
                **auth_headers,
            )

        assert_that(response.status_code, equal_to(200))
        body = response.json()
        assert_that(body, has_entries(slug="shiny-app", status="pending"))
        assert_that(body, has_key("published_at"))
        assert body["published_at"] is not None

    def test_publish_missing_description_returns_400_with_missing(
        self, client, user, auth_headers
    ) -> None:
        project = _ready_draft(owner=user, description="")

        response = client.post(
            f"/api/my/projects/{project.id}/publish",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))
        assert "description" in response.json()["missing"]
        project.refresh_from_db()
        assert_that(project.status, equal_to(ProjectStatus.DRAFT))

    def test_publish_missing_main_image_returns_400(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(
            owner=user,
            status=ProjectStatus.DRAFT,
            title="No Image",
            description="A description",
            submission_month="",
            slug=None,
            published_at=None,
        )

        response = client.post(
            f"/api/my/projects/{project.id}/publish",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))
        assert_that(response.json()["missing"], equal_to(["main_image"]))

    def test_publish_lists_all_missing(self, client, user, auth_headers) -> None:
        project = ProjectFactory(
            owner=user,
            status=ProjectStatus.DRAFT,
            title="",
            description="",
            submission_month="",
            slug=None,
            published_at=None,
        )

        response = client.post(
            f"/api/my/projects/{project.id}/publish",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))
        assert_that(
            response.json()["missing"],
            contains_inanyorder("title", "description", "main_image"),
        )

    def test_publish_non_draft_returns_400(self, client, user, auth_headers) -> None:
        project = ProjectFactory(
            owner=user, status=ProjectStatus.PENDING, title="Already Published"
        )

        response = client.post(
            f"/api/my/projects/{project.id}/publish",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))

    def test_publish_non_owner_returns_404(self, client, auth_headers) -> None:
        project = _ready_draft()  # owned by a different user

        response = client.post(
            f"/api/my/projects/{project.id}/publish",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(404))

    def test_publish_requires_auth(self, client) -> None:
        response = client.post(
            "/api/my/projects/00000000-0000-0000-0000-000000000000/publish"
        )

        assert_that(response.status_code, equal_to(401))


class TestAuthentication:
    """401 tests - unauthenticated users should not access any endpoints."""

    def test_list_projects_requires_auth(self, client) -> None:
        response = client.get("/api/my/projects")
        assert_that(response.status_code, equal_to(401))

    def test_create_project_requires_auth(self, client) -> None:
        response = client.post(
            "/api/my/projects",
            data=json.dumps({"url": "https://example.com"}),
            content_type="application/json",
        )
        assert_that(response.status_code, equal_to(401))

    def test_get_project_requires_auth(self, client, project) -> None:
        response = client.get(f"/api/my/projects/{project.id}")
        assert_that(response.status_code, equal_to(401))

    def test_update_project_requires_auth(self, client, project) -> None:
        response = client.put(
            f"/api/my/projects/{project.id}",
            data=json.dumps({"url": "https://example.com"}),
            content_type="application/json",
        )
        assert_that(response.status_code, equal_to(401))

    def test_delete_project_requires_auth(self, client, project) -> None:
        response = client.delete(f"/api/my/projects/{project.id}")
        assert_that(response.status_code, equal_to(401))

    def test_resubmit_project_requires_auth(self, client, project) -> None:
        response = client.post(f"/api/my/projects/{project.id}/resubmit")
        assert_that(response.status_code, equal_to(401))


class TestAuthorization:
    """403/404 tests - users should not access other users' projects."""

    def test_get_other_users_project_returns_404(
        self,
        client,
        other_project,
        auth_headers,
    ) -> None:
        response = client.get(f"/api/my/projects/{other_project.id}", **auth_headers)
        assert_that(response.status_code, equal_to(404))

    def test_update_other_users_project_returns_404(
        self,
        client,
        other_project,
        auth_headers,
    ) -> None:
        response = client.put(
            f"/api/my/projects/{other_project.id}",
            data=json.dumps({"website_url": "https://hacked.com"}),
            content_type="application/json",
            **auth_headers,
        )
        assert_that(response.status_code, equal_to(404))

    def test_delete_other_users_project_returns_404(
        self,
        client,
        other_project,
        auth_headers,
    ) -> None:
        response = client.delete(f"/api/my/projects/{other_project.id}", **auth_headers)

        assert_that(response.status_code, equal_to(404))
        assert_that(Project.objects.filter(id=other_project.id).exists(), is_(True))

    def test_resubmit_other_users_project_returns_404(
        self,
        client,
        other_user,
        auth_headers,
    ) -> None:
        project = ProjectFactory(owner=other_user, status=ProjectStatus.REJECTED)

        response = client.post(
            f"/api/my/projects/{project.id}/resubmit",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(404))


class TestNonCreatorContributorAccess:
    # `/my-projects` is creator-scoped (see TestListMyProjects above);
    # TIPSTER-only listings live at `/my-projects/tip-offs`. This class
    # asserts that contributor-scoped *write* access still works.
    def test_full_edit_contributor_can_get_project(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory()
        ProjectContributor.objects.create(
            project=project,
            user=user,
            role=ContributorRole.TIPSTER,
            full_edit=True,
        )

        response = client.get(f"/api/my/projects/{project.id}", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(id=str(project.id)))

    def test_full_edit_contributor_can_update_project(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(title="Original")
        ProjectContributor.objects.create(
            project=project,
            user=user,
            role=ContributorRole.TIPSTER,
            full_edit=True,
        )
        payload = {
            "website_url": "https://updated.com",
            "title": "Suggested Edit",
            "description": "Updated description",
        }

        response = client.put(
            f"/api/my/projects/{project.id}",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        project.refresh_from_db()
        assert_that(project.title, equal_to("Suggested Edit"))

    def test_contributor_without_full_edit_returns_404(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory()
        ProjectContributor.objects.create(
            project=project,
            user=user,
            role=ContributorRole.TIPSTER,
            full_edit=False,
        )

        response = client.get(f"/api/my/projects/{project.id}", **auth_headers)

        assert_that(response.status_code, equal_to(404))

    def test_contributor_without_full_edit_cannot_update(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(title="Original")
        ProjectContributor.objects.create(
            project=project,
            user=user,
            role=ContributorRole.TIPSTER,
            full_edit=False,
        )

        response = client.put(
            f"/api/my/projects/{project.id}",
            data=json.dumps({"website_url": "https://hacked.com", "title": "Hacked"}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(404))
        project.refresh_from_db()
        assert_that(project.title, equal_to("Original"))


def _open_competition(**kwargs):
    return CompetitionFactory(
        status=CompetitionStatus.ACCEPTING_APPLICATIONS,
        **kwargs,
    )


def _enter(client, project, competition, headers):
    return client.post(
        f"/api/my/projects/{project.id}/competition-entry",
        data=json.dumps({"competition_id": str(competition.id)}),
        content_type="application/json",
        **headers,
    )


def _standing(response):
    return response.json()["competition_standing"]


def _opportunity_for(response, competition):
    return next(
        candidate
        for candidate in _standing(response)["opportunities"]
        if candidate["competition"]["id"] == str(competition.id)
    )


def _entered_competition_ids(response):
    return [entry["competition"]["id"] for entry in _standing(response)["entries"]]


class TestPublishDoesNotEnterCompetitions:
    def test_publishing_with_an_open_round_creates_no_entry(
        self, client, user, auth_headers
    ) -> None:
        competition = _open_competition()
        project = _ready_draft(owner=user)

        with patch("api.tasks.email.send_new_project_notification"):
            response = client.post(
                f"/api/my/projects/{project.id}/publish", **auth_headers
            )

        assert_that(response.status_code, equal_to(200))
        assert_that(CompetitionEntry.objects.count(), equal_to(0))
        assert_that(_opportunity_for(response, competition)["eligible"], is_(True))

    def test_publishing_a_community_project_behaves_the_same(
        self, client, user, auth_headers
    ) -> None:
        _open_competition()
        project = _ready_draft(owner=user)
        ProjectContributor.objects.filter(
            project=project, role=ContributorRole.OWNER
        ).delete()
        ProjectContributor.objects.create(
            project=project,
            user_id=COMMUNITY_USER_ID,
            role=ContributorRole.OWNER,
            full_edit=True,
        )
        ProjectContributor.objects.create(
            project=project,
            user=user,
            role=ContributorRole.TIPSTER,
            full_edit=True,
        )

        with patch("api.tasks.email.send_new_project_notification"):
            response = client.post(
                f"/api/my/projects/{project.id}/publish", **auth_headers
            )

        assert_that(response.status_code, equal_to(200))
        assert_that(CompetitionEntry.objects.count(), equal_to(0))

    def test_a_failed_publish_creates_no_entry(
        self, client, user, auth_headers
    ) -> None:
        _open_competition()
        project = ProjectFactory(
            owner=user, status=ProjectStatus.DRAFT, description="", slug=None
        )

        response = client.post(f"/api/my/projects/{project.id}/publish", **auth_headers)

        assert_that(response.status_code, equal_to(400))
        assert_that(CompetitionEntry.objects.count(), equal_to(0))


class TestEnterCompetition:
    def test_entering_an_open_competition_returns_200(
        self, client, user, auth_headers
    ) -> None:
        competition = _open_competition()
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)

        response = _enter(client, project, competition, auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(_entered_competition_ids(response), equal_to([str(competition.id)]))

    def test_the_entry_records_who_entered_it_and_how(
        self, client, user, auth_headers
    ) -> None:
        competition = _open_competition()
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)

        _enter(client, project, competition, auth_headers)

        entry = CompetitionEntry.objects.get()
        assert_that(entry.entered_via, equal_to(EntrySource.MANUAL))
        assert_that(entry.entered_by_id, equal_to(user.id))

    def test_a_project_published_between_rounds_enters_the_next_one(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)
        assert_that(CompetitionEntry.objects.count(), equal_to(0))
        competition = _open_competition()

        response = _enter(client, project, competition, auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(project.competitions.count(), equal_to(1))

    def test_a_past_entrant_may_enter_a_different_series(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)
        CompetitionEntryFactory(
            project=project,
            competition=CompetitionFactory(
                entry_series="monthly", status=CompetitionStatus.CLOSED
            ),
        )
        hackathon = _open_competition(entry_series="summer-hackathon")

        response = _enter(client, project, hackathon, auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(project.competitions.count(), equal_to(2))

    def test_entering_the_same_series_twice_returns_400(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)
        CompetitionEntryFactory(
            project=project,
            competition=CompetitionFactory(
                entry_series="monthly", status=CompetitionStatus.CLOSED
            ),
        )
        july = _open_competition(entry_series="monthly")

        response = _enter(client, project, july, auth_headers)

        assert_that(response.status_code, equal_to(400))
        assert_that(CompetitionEntry.objects.count(), equal_to(1))

    def test_entering_a_competition_that_is_not_open_returns_400(
        self, client, user, auth_headers
    ) -> None:
        competition = CompetitionFactory(status=CompetitionStatus.VOTING)
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)

        response = _enter(client, project, competition, auth_headers)

        assert_that(response.status_code, equal_to(400))
        assert_that(CompetitionEntry.objects.count(), equal_to(0))

    def test_entering_an_unknown_competition_returns_400(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)

        response = client.post(
            f"/api/my/projects/{project.id}/competition-entry",
            data=json.dumps({"competition_id": "00000000-0000-0000-0000-000000000000"}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))

    def test_a_request_without_a_competition_id_is_rejected(
        self, client, user, auth_headers
    ) -> None:
        _open_competition()
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)

        response = client.post(
            f"/api/my/projects/{project.id}/competition-entry",
            data=json.dumps({}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(422))
        assert_that(CompetitionEntry.objects.count(), equal_to(0))

    def test_a_draft_cannot_enter(self, client, user, auth_headers) -> None:
        competition = _open_competition()
        project = ProjectFactory(owner=user, status=ProjectStatus.DRAFT)

        response = _enter(client, project, competition, auth_headers)

        assert_that(response.status_code, equal_to(400))
        assert_that(CompetitionEntry.objects.count(), equal_to(0))
        project.refresh_from_db()
        assert_that(project.status, equal_to(ProjectStatus.DRAFT))

    def test_a_community_tipoff_cannot_enter(self, client, user, auth_headers) -> None:
        competition = _open_competition()
        project = ProjectFactory(
            owner=user, status=ProjectStatus.PENDING, _contributor=False
        )
        ProjectContributor.objects.create(
            project=project,
            user_id=COMMUNITY_USER_ID,
            role=ContributorRole.OWNER,
            full_edit=True,
        )
        ProjectContributor.objects.create(
            project=project,
            user=user,
            role=ContributorRole.TIPSTER,
            full_edit=True,
        )

        response = _enter(client, project, competition, auth_headers)

        assert_that(response.status_code, equal_to(400))
        assert_that(CompetitionEntry.objects.count(), equal_to(0))

    def test_a_non_contributor_gets_404(self, client, auth_headers) -> None:
        competition = _open_competition()
        project = ProjectFactory(status=ProjectStatus.PENDING)

        response = _enter(client, project, competition, auth_headers)

        assert_that(response.status_code, equal_to(404))

    def test_entry_requires_auth(self, client, db) -> None:
        competition = _open_competition()
        project = ProjectFactory(status=ProjectStatus.PENDING)

        response = client.post(
            f"/api/my/projects/{project.id}/competition-entry",
            data=json.dumps({"competition_id": str(competition.id)}),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(401))

    def test_a_round_that_closed_since_the_page_loaded_returns_400(
        self, client, user, auth_headers
    ) -> None:
        competition = _open_competition()
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)
        competition.status = CompetitionStatus.VOTING
        competition.save(update_fields=["status"])

        response = _enter(client, project, competition, auth_headers)

        assert_that(response.status_code, equal_to(400))
        assert_that(CompetitionEntry.objects.count(), equal_to(0))

    def test_a_second_entry_into_the_same_competition_returns_409(
        self, client, user, auth_headers
    ) -> None:
        """The loser of a concurrent entry: the row already exists by the time
        this request's create lands."""
        competition = _open_competition()
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)

        with patch.object(
            DjangoProjectQuery,
            "competition_standing",
            side_effect=lambda p: _standing_ignoring_entries(p, competition),
        ):
            first = _enter(client, project, competition, auth_headers)
            response = _enter(client, project, competition, auth_headers)

        assert_that(first.status_code, equal_to(200))
        assert_that(response.status_code, equal_to(409))
        assert_that(CompetitionEntry.objects.count(), equal_to(1))


def _standing_ignoring_entries(project, competition):
    """A standing that still offers `competition` however many entries exist —
    what a request that read the page before a competing write would have."""
    return CompetitionStanding(
        entries=[],
        opportunities=[CompetitionOpportunity(competition=competition, eligible=True)],
    )


class TestCompetitionStandingOnResponses:
    def test_the_public_project_response_omits_standing(self, client, user) -> None:
        _open_competition()
        project = ProjectFactory(owner=user, status=ProjectStatus.APPROVED)

        response = client.get(f"/api/projects/{project.id}")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["competition_standing"], is_(none()))

    def test_an_owner_sees_standing_on_their_project(
        self, client, user, auth_headers
    ) -> None:
        competition = _open_competition()
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)

        response = client.get(f"/api/my/projects/{project.id}", **auth_headers)

        assert_that(_opportunity_for(response, competition)["eligible"], is_(True))

    def test_a_blocked_opportunity_names_the_competition_in_the_way(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)
        june = CompetitionFactory(
            entry_series="monthly", status=CompetitionStatus.CLOSED
        )
        CompetitionEntryFactory(project=project, competition=june)
        july = _open_competition(entry_series="monthly")

        response = client.get(f"/api/my/projects/{project.id}", **auth_headers)

        opportunity = _opportunity_for(response, july)
        assert_that(opportunity["eligible"], is_(False))
        assert_that(opportunity["reason"], equal_to("already_in_series"))
        assert_that(opportunity["blocking_entry"]["id"], equal_to(str(june.id)))

    def test_no_open_round_is_an_empty_opportunity_list(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)

        response = client.get(f"/api/my/projects/{project.id}", **auth_headers)

        assert_that(_standing(response)["opportunities"], equal_to([]))
        assert_that(_standing(response)["entries"], equal_to([]))
