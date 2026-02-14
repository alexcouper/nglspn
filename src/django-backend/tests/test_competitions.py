from unittest.mock import PropertyMock, patch

import pytest
from hamcrest import assert_that, contains_inanyorder, equal_to, has_entries, has_length

from apps.projects.models import Competition, CompetitionStatus, ProjectStatus
from tests.factories import CompetitionFactory, ProjectFactory, TagFactory


@pytest.mark.django_db
class TestListCompetitions:
    def test_list_competitions_returns_overview_without_projects(
        self,
        client,
    ) -> None:
        competition = CompetitionFactory()
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        competition.projects.add(project)

        response = client.get("/api/competitions")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["competitions"], has_length(1))
        assert_that(
            response.json()["competitions"][0],
            has_entries(
                id=str(competition.id),
                name=competition.name,
                project_count=1,
                image_url=None,
            ),
        )
        assert "projects" not in response.json()["competitions"][0]
        assert "winner" not in response.json()["competitions"][0]

    def test_list_competitions_includes_pending_projects_count(
        self,
        client,
    ) -> None:
        ProjectFactory(status=ProjectStatus.PENDING)
        ProjectFactory(status=ProjectStatus.PENDING)
        ProjectFactory(status=ProjectStatus.APPROVED)

        response = client.get("/api/competitions")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["pending_projects_count"], equal_to(2))

    def test_list_competitions_includes_per_competition_pending_count(
        self,
        client,
    ) -> None:
        competition = CompetitionFactory()
        pending = ProjectFactory(status=ProjectStatus.PENDING)
        approved = ProjectFactory(status=ProjectStatus.APPROVED)
        competition.projects.add(pending, approved)

        response = client.get("/api/competitions")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json()["competitions"][0]["pending_projects_count"],
            equal_to(1),
        )

    def test_list_competitions_returns_empty_when_no_competitions(
        self,
        client,
    ) -> None:
        response = client.get("/api/competitions")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["competitions"], has_length(0))


@pytest.mark.django_db
class TestListCompetitionsWithProjects:
    def test_returns_competitions_with_projects(
        self,
        client,
    ) -> None:
        competition = CompetitionFactory()
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        competition.projects.add(project)

        response = client.get("/api/competitions/with-projects")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["competitions"], has_length(1))
        assert_that(
            response.json()["competitions"][0]["projects"],
            has_length(1),
        )

    def test_only_includes_approved_projects(
        self,
        client,
    ) -> None:
        competition = CompetitionFactory()
        approved = ProjectFactory(status=ProjectStatus.APPROVED)
        pending = ProjectFactory(status=ProjectStatus.PENDING)
        rejected = ProjectFactory(status=ProjectStatus.REJECTED)
        competition.projects.add(approved, pending, rejected)

        response = client.get("/api/competitions/with-projects")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["competitions"][0]["project_count"], equal_to(3))
        assert_that(
            response.json()["competitions"][0]["projects"],
            has_length(1),
        )

    def test_excludes_ice_box_projects(
        self,
        client,
    ) -> None:
        competition = CompetitionFactory()
        approved = ProjectFactory(status=ProjectStatus.APPROVED)
        ice_box = ProjectFactory(status=ProjectStatus.ICE_BOX)
        competition.projects.add(approved, ice_box)

        response = client.get("/api/competitions/with-projects")

        assert_that(response.status_code, equal_to(200))
        projects = response.json()["competitions"][0]["projects"]
        assert_that(projects, has_length(1))
        assert_that(projects[0]["id"], equal_to(str(approved.id)))

    def test_includes_pending_projects_count(
        self,
        client,
    ) -> None:
        ProjectFactory(status=ProjectStatus.PENDING)
        ProjectFactory(status=ProjectStatus.PENDING)
        ProjectFactory(status=ProjectStatus.APPROVED)

        response = client.get("/api/competitions/with-projects")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["pending_projects_count"], equal_to(2))


@pytest.mark.django_db
class TestGetCompetition:
    def test_get_competition_returns_competition_with_projects(
        self,
        client,
    ) -> None:
        competition = CompetitionFactory()
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        competition.projects.add(project)

        response = client.get(f"/api/competitions/{competition.id}")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(
                id=str(competition.id),
                name=competition.name,
                project_count=1,
                image_url=None,
            ),
        )
        assert_that(response.json()["projects"], has_length(1))

    def test_get_competition_includes_pending_projects_count(
        self,
        client,
    ) -> None:
        competition = CompetitionFactory()
        pending1 = ProjectFactory(status=ProjectStatus.PENDING)
        pending2 = ProjectFactory(status=ProjectStatus.PENDING)
        pending3 = ProjectFactory(status=ProjectStatus.PENDING)
        approved = ProjectFactory(status=ProjectStatus.APPROVED)
        competition.projects.add(pending1, pending2, pending3, approved)
        ProjectFactory(status=ProjectStatus.PENDING)  # not in competition

        response = client.get(f"/api/competitions/{competition.id}")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["pending_projects_count"], equal_to(3))

    def test_get_nonexistent_competition_returns_404(
        self,
        client,
    ) -> None:
        response = client.get("/api/competitions/00000000-0000-0000-0000-000000000000")

        assert_that(response.status_code, equal_to(404))


@pytest.mark.django_db
class TestCompetitionWinner:
    def test_list_with_projects_includes_winner_details(
        self,
        client,
    ) -> None:
        winner_project = ProjectFactory(status=ProjectStatus.APPROVED, title="Winner")
        competition = CompetitionFactory(winner=winner_project)
        competition.projects.add(winner_project)

        response = client.get("/api/competitions/with-projects")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json()["competitions"][0],
            has_entries(
                winner=has_entries(
                    id=str(winner_project.id),
                    title="Winner",
                ),
            ),
        )

    def test_list_with_projects_returns_null_winner_when_no_winner(
        self,
        client,
    ) -> None:
        CompetitionFactory(winner=None)

        response = client.get("/api/competitions/with-projects")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["competitions"][0]["winner"], equal_to(None))

    def test_get_competition_includes_winner_details(
        self,
        client,
    ) -> None:
        winner_project = ProjectFactory(status=ProjectStatus.APPROVED, title="Winner")
        competition = CompetitionFactory(winner=winner_project)
        competition.projects.add(winner_project)

        response = client.get(f"/api/competitions/{competition.id}")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json()["winner"],
            has_entries(
                id=str(winner_project.id),
                title="Winner",
            ),
        )


@pytest.mark.django_db
class TestCompetitionProjectTags:
    def test_list_with_projects_includes_project_tags(
        self,
        client,
    ) -> None:
        tag1 = TagFactory(name="SaaS", slug="saas")
        tag2 = TagFactory(name="E-commerce", slug="e-commerce")
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        project.tags.add(tag1, tag2)
        competition = CompetitionFactory()
        competition.projects.add(project)

        response = client.get("/api/competitions/with-projects")

        assert_that(response.status_code, equal_to(200))
        project_data = response.json()["competitions"][0]["projects"][0]
        assert_that(project_data["tags"], has_length(2))
        assert_that(
            [t["slug"] for t in project_data["tags"]],
            contains_inanyorder("saas", "e-commerce"),
        )

    def test_get_competition_includes_project_tags(
        self,
        client,
    ) -> None:
        tag = TagFactory(name="Developer Tools", slug="dev-tools")
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        project.tags.add(tag)
        competition = CompetitionFactory()
        competition.projects.add(project)

        response = client.get(f"/api/competitions/{competition.id}")

        assert_that(response.status_code, equal_to(200))
        project_data = response.json()["projects"][0]
        assert_that(project_data["tags"], has_length(1))
        assert_that(project_data["tags"][0]["slug"], equal_to("dev-tools"))


@pytest.mark.django_db
class TestCompetitionImage:
    def test_list_competitions_includes_image_url_when_image_exists(
        self,
        client,
    ) -> None:
        CompetitionFactory()

        with patch.object(
            Competition,
            "image_url",
            new_callable=PropertyMock,
            return_value="https://example.com/image.jpg",
        ):
            response = client.get("/api/competitions")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json()["competitions"][0]["image_url"],
            equal_to("https://example.com/image.jpg"),
        )

    def test_get_competition_includes_image_url_when_image_exists(
        self,
        client,
    ) -> None:
        competition = CompetitionFactory()

        with patch.object(
            Competition,
            "image_url",
            new_callable=PropertyMock,
            return_value="https://example.com/comp-image.png",
        ):
            response = client.get(f"/api/competitions/{competition.id}")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json()["image_url"],
            equal_to("https://example.com/comp-image.png"),
        )


@pytest.mark.django_db
class TestCompetitionStatus:
    def test_list_competitions_includes_status(
        self,
        client,
    ) -> None:
        CompetitionFactory(status=CompetitionStatus.ACCEPTING_APPLICATIONS)

        response = client.get("/api/competitions")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json()["competitions"][0],
            has_entries(status="accepting_applications"),
        )

    def test_get_competition_includes_status(
        self,
        client,
    ) -> None:
        competition = CompetitionFactory(status=CompetitionStatus.PENDING)

        response = client.get(f"/api/competitions/{competition.id}")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["status"], equal_to("pending"))

    def test_competition_defaults_to_pending_status(
        self,
        client,
    ) -> None:
        competition = CompetitionFactory()

        response = client.get(f"/api/competitions/{competition.id}")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["status"], equal_to("pending"))

    def test_setting_winner_sets_status_to_closed(
        self,
        client,
    ) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        competition = CompetitionFactory(
            status=CompetitionStatus.ACCEPTING_APPLICATIONS
        )
        competition.projects.add(project)

        competition.winner = project
        competition.save()

        response = client.get(f"/api/competitions/{competition.id}")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["status"], equal_to("closed"))

    def test_setting_winner_on_creation_sets_status_to_closed(
        self,
        client,
    ) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        competition = CompetitionFactory(winner=project)

        response = client.get(f"/api/competitions/{competition.id}")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["status"], equal_to("closed"))


@pytest.mark.django_db
class TestCompetitionSlug:
    def test_slug_is_auto_generated_from_name(self) -> None:
        competition = CompetitionFactory(name="Laukur 2025")

        assert_that(competition.slug, equal_to("laukur-2025"))

    def test_slug_handles_icelandic_characters(self) -> None:
        competition = CompetitionFactory(name="Þórsmörk Ævintýri")

        assert_that(competition.slug, equal_to("thorsmork-aevintyri"))

    def test_slug_can_be_explicitly_set(self) -> None:
        competition = CompetitionFactory(name="Some Competition", slug="custom-slug")

        assert_that(competition.slug, equal_to("custom-slug"))

    def test_list_competitions_includes_slug(self, client) -> None:
        CompetitionFactory(name="My Competition")

        response = client.get("/api/competitions")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json()["competitions"][0],
            has_entries(slug="my-competition"),
        )

    def test_get_competition_by_slug(self, client) -> None:
        competition = CompetitionFactory(name="Laukur 2025")

        response = client.get("/api/competitions/laukur-2025")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(
                id=str(competition.id),
                name="Laukur 2025",
                slug="laukur-2025",
            ),
        )

    def test_get_competition_by_uuid_still_works(self, client) -> None:
        competition = CompetitionFactory(name="Some Competition")

        response = client.get(f"/api/competitions/{competition.id}")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(
                id=str(competition.id),
                name="Some Competition",
            ),
        )

    def test_get_nonexistent_slug_returns_404(self, client) -> None:
        response = client.get("/api/competitions/nonexistent-slug")

        assert_that(response.status_code, equal_to(404))


@pytest.mark.django_db
class TestActiveOrMostRecent:
    def test_returns_active_competition(self, client) -> None:
        competition = CompetitionFactory(
            status=CompetitionStatus.ACCEPTING_APPLICATIONS,
            name="Active Comp",
            prize_amount=100000,
        )

        response = client.get("/api/competitions/active-or-most-recent")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json()["active"],
            has_entries(
                name="Active Comp",
                slug=competition.slug,
                status="accepting_applications",
                prize_amount="100000",
                project_count=0,
            ),
        )
        assert_that(response.json()["recent"], equal_to(None))

    def test_returns_most_recent_closed_competition(self, client) -> None:
        CompetitionFactory(
            status=CompetitionStatus.CLOSED,
            name="Older",
            end_date="2024-06-01",
        )
        CompetitionFactory(
            status=CompetitionStatus.CLOSED,
            name="Newest",
            end_date="2025-01-31",
        )

        response = client.get("/api/competitions/active-or-most-recent")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["recent"]["name"], equal_to("Newest"))

    def test_returns_both_active_and_recent(self, client) -> None:
        CompetitionFactory(status=CompetitionStatus.ACCEPTING_APPLICATIONS)
        CompetitionFactory(status=CompetitionStatus.CLOSED)

        response = client.get("/api/competitions/active-or-most-recent")

        assert_that(response.status_code, equal_to(200))
        assert response.json()["active"] is not None
        assert response.json()["recent"] is not None

    def test_returns_nulls_when_no_competitions(self, client) -> None:
        response = client.get("/api/competitions/active-or-most-recent")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), equal_to({"active": None, "recent": None}))

    def test_includes_project_count_not_full_projects(self, client) -> None:
        competition = CompetitionFactory(
            status=CompetitionStatus.ACCEPTING_APPLICATIONS
        )
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        competition.projects.add(project)

        response = client.get("/api/competitions/active-or-most-recent")

        active = response.json()["active"]
        assert_that(active["project_count"], equal_to(1))
        assert "projects" not in active

    def test_does_not_include_winner_or_pending_count(self, client) -> None:
        winner = ProjectFactory(status=ProjectStatus.APPROVED)
        competition = CompetitionFactory(status=CompetitionStatus.CLOSED, winner=winner)
        competition.projects.add(winner)

        response = client.get("/api/competitions/active-or-most-recent")

        recent = response.json()["recent"]
        assert "winner" not in recent
        assert "pending_projects_count" not in recent
