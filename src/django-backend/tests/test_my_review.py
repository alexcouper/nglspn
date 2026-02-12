import json
import uuid

import pytest
from hamcrest import assert_that, contains_inanyorder, equal_to, has_entries, has_length

from api.auth.jwt import create_access_token
from apps.projects.models import (
    CompetitionReviewer,
    ProjectRanking,
    ProjectStatus,
    ReviewStatus,
)
from tests.factories import (
    CompetitionFactory,
    CompetitionReviewerFactory,
    ProjectFactory,
    ProjectImageFactory,
    ProjectRankingFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestListMyReviewCompetitions:
    def test_returns_empty_list_when_not_assigned_to_any_competition(
        self, client, user, auth_headers
    ) -> None:
        CompetitionFactory()  # Competition exists but user not assigned

        response = client.get("/api/my/reviews/competitions", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(competitions=[]))

    def test_returns_competitions_user_is_assigned_to(
        self, client, user, auth_headers
    ) -> None:
        competition1 = CompetitionFactory(name="Competition A")
        competition2 = CompetitionFactory(name="Competition B")
        CompetitionFactory(name="Competition C")  # Not assigned

        CompetitionReviewerFactory(user=user, competition=competition1)
        CompetitionReviewerFactory(user=user, competition=competition2)

        response = client.get("/api/my/reviews/competitions", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        competitions = response.json()["competitions"]
        assert_that(competitions, has_length(2))
        names = [c["name"] for c in competitions]
        assert_that(names, contains_inanyorder("Competition A", "Competition B"))

    def test_returns_image_url_when_competition_has_image(
        self, client, user, auth_headers
    ) -> None:
        competition = CompetitionFactory(name="Competition With Image")
        # Set image field directly (simulates uploaded file path in DB)
        competition.image = "test-competition-id/test-image.jpg"
        competition.save()

        CompetitionReviewerFactory(user=user, competition=competition)

        response = client.get("/api/my/reviews/competitions", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        competitions = response.json()["competitions"]
        assert_that(competitions, has_length(1))
        assert competitions[0]["image_url"] is not None
        assert "test-image.jpg" in competitions[0]["image_url"]

    def test_returns_401_when_not_authenticated(self, client) -> None:
        response = client.get("/api/my/reviews/competitions")

        assert_that(response.status_code, equal_to(401))

    def test_includes_my_review_status_in_response(
        self, client, user, auth_headers
    ) -> None:
        competition = CompetitionFactory()
        CompetitionReviewerFactory(
            user=user, competition=competition, status=ReviewStatus.IN_PROGRESS
        )

        response = client.get("/api/my/reviews/competitions", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        competitions = response.json()["competitions"]
        assert_that(competitions[0]["my_review_status"], equal_to("in_progress"))

    def test_includes_completed_status_in_response(
        self, client, user, auth_headers
    ) -> None:
        competition = CompetitionFactory()
        CompetitionReviewerFactory(
            user=user, competition=competition, status=ReviewStatus.COMPLETED
        )

        response = client.get("/api/my/reviews/competitions", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        competitions = response.json()["competitions"]
        assert_that(competitions[0]["my_review_status"], equal_to("completed"))


@pytest.mark.django_db
class TestGetMyReviewCompetition:
    def test_returns_404_when_not_assigned_to_competition(
        self, client, user, auth_headers
    ) -> None:
        competition = CompetitionFactory()

        response = client.get(
            f"/api/my/reviews/competitions/{competition.id}", **auth_headers
        )

        assert_that(response.status_code, equal_to(404))

    def test_cannot_see_projects_from_unassigned_competition(
        self, client, user, auth_headers
    ) -> None:
        # User is assigned to competition1 but not competition2
        project1 = ProjectFactory(title="Project in my competition")
        project2 = ProjectFactory(title="Project in other competition")

        competition1 = CompetitionFactory(name="My Competition", projects=[project1])
        competition2 = CompetitionFactory(name="Other Competition", projects=[project2])

        CompetitionReviewerFactory(user=user, competition=competition1)
        # Note: user is NOT assigned to competition2

        # Trying to access competition2 should return 404
        response = client.get(
            f"/api/my/reviews/competitions/{competition2.id}", **auth_headers
        )

        assert_that(response.status_code, equal_to(404))
        assert_that(response.json(), has_entries(detail="Competition not found"))

    def test_returns_competition_with_projects_when_assigned(
        self, client, user, auth_headers
    ) -> None:
        project1 = ProjectFactory(title="Project A")
        project2 = ProjectFactory(title="Project B")
        competition = CompetitionFactory(projects=[project1, project2])
        CompetitionReviewerFactory(user=user, competition=competition)

        response = client.get(
            f"/api/my/reviews/competitions/{competition.id}", **auth_headers
        )

        assert_that(response.status_code, equal_to(200))
        data = response.json()
        assert_that(data["name"], equal_to(competition.name))
        assert_that(data["projects"], has_length(2))

    def test_includes_my_rankings_for_projects(
        self, client, user, auth_headers
    ) -> None:
        project1 = ProjectFactory(title="Project A")
        project2 = ProjectFactory(title="Project B")
        competition = CompetitionFactory(projects=[project1, project2])
        CompetitionReviewerFactory(user=user, competition=competition)

        # User has ranked project1 but not project2
        ProjectRankingFactory(
            reviewer=user, competition=competition, project=project1, position=1
        )

        response = client.get(
            f"/api/my/reviews/competitions/{competition.id}", **auth_headers
        )

        assert_that(response.status_code, equal_to(200))
        projects = response.json()["projects"]

        project1_data = next(p for p in projects if p["id"] == str(project1.id))
        project2_data = next(p for p in projects if p["id"] == str(project2.id))

        assert_that(project1_data["my_ranking"], equal_to(1))
        assert_that(project2_data["my_ranking"], equal_to(None))

    def test_does_not_show_other_reviewers_rankings(self, client, db) -> None:
        reviewer1 = UserFactory()
        reviewer2 = UserFactory()
        project = ProjectFactory()
        competition = CompetitionFactory(projects=[project])

        CompetitionReviewerFactory(user=reviewer1, competition=competition)
        CompetitionReviewerFactory(user=reviewer2, competition=competition)

        # Reviewer2 has ranked the project
        ProjectRankingFactory(
            reviewer=reviewer2, competition=competition, project=project, position=1
        )

        # Reviewer1 requests the competition
        token = create_access_token(reviewer1.id)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

        response = client.get(
            f"/api/my/reviews/competitions/{competition.id}", **headers
        )

        assert_that(response.status_code, equal_to(200))
        projects = response.json()["projects"]

        # Reviewer1 should not see reviewer2's ranking
        assert_that(projects[0]["my_ranking"], equal_to(None))

    def test_returns_401_when_not_authenticated(self, client) -> None:
        competition = CompetitionFactory()

        response = client.get(f"/api/my/reviews/competitions/{competition.id}")

        assert_that(response.status_code, equal_to(401))

    def test_includes_my_review_status_in_response(
        self, client, user, auth_headers
    ) -> None:
        competition = CompetitionFactory()
        CompetitionReviewerFactory(
            user=user, competition=competition, status=ReviewStatus.COMPLETED
        )

        response = client.get(
            f"/api/my/reviews/competitions/{competition.id}", **auth_headers
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["my_review_status"], equal_to("completed"))


@pytest.mark.django_db
class TestUpdateRankings:
    def test_returns_404_when_not_assigned_to_competition(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory()
        competition = CompetitionFactory(projects=[project])

        response = client.put(
            f"/api/my/reviews/competitions/{competition.id}/rankings",
            data=json.dumps({"project_ids": [str(project.id)]}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(404))

    def test_returns_400_when_project_not_in_competition(
        self, client, user, auth_headers
    ) -> None:
        project_in_competition = ProjectFactory()
        project_not_in_competition = ProjectFactory()
        competition = CompetitionFactory(projects=[project_in_competition])
        CompetitionReviewerFactory(user=user, competition=competition)

        response = client.put(
            f"/api/my/reviews/competitions/{competition.id}/rankings",
            data=json.dumps({"project_ids": [str(project_not_in_competition.id)]}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))
        assert_that(
            response.json()["detail"],
            equal_to("One or more projects do not belong to this competition"),
        )

    def test_returns_400_when_review_is_completed(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory()
        competition = CompetitionFactory(projects=[project])
        CompetitionReviewerFactory(
            user=user, competition=competition, status=ReviewStatus.COMPLETED
        )

        response = client.put(
            f"/api/my/reviews/competitions/{competition.id}/rankings",
            data=json.dumps({"project_ids": [str(project.id)]}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))
        assert_that(
            response.json()["detail"],
            equal_to("Cannot update rankings for a completed review"),
        )

    def test_successfully_creates_rankings(self, client, user, auth_headers) -> None:
        project1 = ProjectFactory()
        project2 = ProjectFactory()
        project3 = ProjectFactory()
        competition = CompetitionFactory(projects=[project1, project2, project3])
        CompetitionReviewerFactory(user=user, competition=competition)

        response = client.put(
            f"/api/my/reviews/competitions/{competition.id}/rankings",
            data=json.dumps(
                {"project_ids": [str(project2.id), str(project1.id), str(project3.id)]}
            ),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))

        # Verify rankings were created in database
        rankings = ProjectRanking.objects.filter(
            reviewer=user, competition=competition
        ).order_by("position")

        assert_that(
            list(rankings.values_list("project_id", "position")),
            equal_to(
                [
                    (project2.id, 1),
                    (project1.id, 2),
                    (project3.id, 3),
                ]
            ),
        )

    def test_replaces_existing_rankings(self, client, user, auth_headers) -> None:
        project1 = ProjectFactory()
        project2 = ProjectFactory()
        competition = CompetitionFactory(projects=[project1, project2])
        CompetitionReviewerFactory(user=user, competition=competition)

        # Create initial rankings
        ProjectRankingFactory(
            reviewer=user, competition=competition, project=project1, position=1
        )
        ProjectRankingFactory(
            reviewer=user, competition=competition, project=project2, position=2
        )

        # Update with reversed order
        response = client.put(
            f"/api/my/reviews/competitions/{competition.id}/rankings",
            data=json.dumps({"project_ids": [str(project2.id), str(project1.id)]}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))

        # Verify rankings were replaced
        rankings = ProjectRanking.objects.filter(
            reviewer=user, competition=competition
        ).order_by("position")

        assert_that(
            list(rankings.values_list("project_id", "position")),
            equal_to(
                [
                    (project2.id, 1),
                    (project1.id, 2),
                ]
            ),
        )

    def test_returns_success_response(self, client, user, auth_headers) -> None:
        project = ProjectFactory()
        competition = CompetitionFactory(projects=[project])
        CompetitionReviewerFactory(user=user, competition=competition)

        response = client.put(
            f"/api/my/reviews/competitions/{competition.id}/rankings",
            data=json.dumps({"project_ids": [str(project.id)]}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), equal_to({"success": True}))

    def test_returns_401_when_not_authenticated(self, client) -> None:
        competition = CompetitionFactory()

        response = client.put(
            f"/api/my/reviews/competitions/{competition.id}/rankings",
            data=json.dumps({"project_ids": []}),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(401))


@pytest.mark.django_db
class TestUpdateReviewStatus:
    def test_returns_404_when_not_assigned_to_competition(
        self, client, user, auth_headers
    ) -> None:
        competition = CompetitionFactory()

        response = client.put(
            f"/api/my/reviews/competitions/{competition.id}/status",
            data=json.dumps({"status": "completed"}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(404))

    def test_successfully_updates_status_to_completed(
        self, client, user, auth_headers
    ) -> None:
        competition = CompetitionFactory()
        CompetitionReviewerFactory(
            user=user, competition=competition, status=ReviewStatus.IN_PROGRESS
        )

        response = client.put(
            f"/api/my/reviews/competitions/{competition.id}/status",
            data=json.dumps({"status": "completed"}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))

        # Verify status was updated in database
        assignment = CompetitionReviewer.objects.get(user=user, competition=competition)
        assert_that(assignment.status, equal_to(ReviewStatus.COMPLETED))

    def test_successfully_updates_status_to_in_progress(
        self, client, user, auth_headers
    ) -> None:
        competition = CompetitionFactory()
        CompetitionReviewerFactory(
            user=user, competition=competition, status=ReviewStatus.COMPLETED
        )

        response = client.put(
            f"/api/my/reviews/competitions/{competition.id}/status",
            data=json.dumps({"status": "in_progress"}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))

        # Verify status was updated in database
        assignment = CompetitionReviewer.objects.get(user=user, competition=competition)
        assert_that(assignment.status, equal_to(ReviewStatus.IN_PROGRESS))

    def test_returns_success_response(self, client, user, auth_headers) -> None:
        competition = CompetitionFactory()
        CompetitionReviewerFactory(
            user=user, competition=competition, status=ReviewStatus.IN_PROGRESS
        )

        response = client.put(
            f"/api/my/reviews/competitions/{competition.id}/status",
            data=json.dumps({"status": "completed"}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), equal_to({"success": True}))

    def test_returns_401_when_not_authenticated(self, client) -> None:
        competition = CompetitionFactory()

        response = client.put(
            f"/api/my/reviews/competitions/{competition.id}/status",
            data=json.dumps({"status": "completed"}),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(401))


@pytest.mark.django_db
class TestGetReviewProject:
    def test_returns_404_when_project_does_not_exist(
        self, client, user, auth_headers
    ) -> None:
        response = client.get(
            f"/api/my/reviews/projects/{uuid.uuid4()}", **auth_headers
        )

        assert_that(response.status_code, equal_to(404))
        assert_that(response.json(), has_entries(detail="Project not found"))

    def test_returns_404_when_user_not_assigned_to_review_competition_with_project(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(status=ProjectStatus.PENDING)
        # Competition exists but user not assigned
        CompetitionFactory(projects=[project])

        response = client.get(f"/api/my/reviews/projects/{project.id}", **auth_headers)

        assert_that(response.status_code, equal_to(404))
        assert_that(response.json(), has_entries(detail="Project not found"))

    def test_returns_project_when_user_is_assigned_reviewer(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(
            title="Test Project",
            description="Test description",
            status=ProjectStatus.PENDING,
        )
        competition = CompetitionFactory(projects=[project])
        CompetitionReviewerFactory(user=user, competition=competition)

        response = client.get(f"/api/my/reviews/projects/{project.id}", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        data = response.json()
        assert_that(data["id"], equal_to(str(project.id)))
        assert_that(data["title"], equal_to("Test Project"))
        assert_that(data["description"], equal_to("Test description"))

    def test_returns_project_images(self, client, user, auth_headers) -> None:
        project = ProjectFactory(status=ProjectStatus.PENDING)
        image = ProjectImageFactory(project=project, upload_status="uploaded")
        competition = CompetitionFactory(projects=[project])
        CompetitionReviewerFactory(user=user, competition=competition)

        response = client.get(f"/api/my/reviews/projects/{project.id}", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["images"], has_length(1))
        assert_that(response.json()["images"][0]["id"], equal_to(str(image.id)))

    def test_returns_401_when_not_authenticated(self, client) -> None:
        project = ProjectFactory()

        response = client.get(f"/api/my/reviews/projects/{project.id}")

        assert_that(response.status_code, equal_to(401))

    def test_user_in_multiple_competitions_can_access_project(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(status=ProjectStatus.PENDING)
        competition1 = CompetitionFactory(projects=[project])
        # Different competition without this project
        competition2 = CompetitionFactory()

        CompetitionReviewerFactory(user=user, competition=competition1)
        CompetitionReviewerFactory(user=user, competition=competition2)

        response = client.get(f"/api/my/reviews/projects/{project.id}", **auth_headers)

        assert_that(response.status_code, equal_to(200))

    def test_cannot_access_project_from_different_competition(
        self, client, user, auth_headers
    ) -> None:
        project_in_other_competition = ProjectFactory(status=ProjectStatus.PENDING)
        my_competition = CompetitionFactory()
        CompetitionFactory(projects=[project_in_other_competition])

        CompetitionReviewerFactory(user=user, competition=my_competition)
        # Note: user is NOT assigned to competition containing the project

        response = client.get(
            f"/api/my/reviews/projects/{project_in_other_competition.id}",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(404))

    def test_returns_404_for_rejected_project(self, client, user, auth_headers) -> None:
        project = ProjectFactory(status=ProjectStatus.REJECTED)
        competition = CompetitionFactory(projects=[project])
        CompetitionReviewerFactory(user=user, competition=competition)

        response = client.get(f"/api/my/reviews/projects/{project.id}", **auth_headers)

        assert_that(response.status_code, equal_to(404))

    def test_returns_404_for_ice_box_project(self, client, user, auth_headers) -> None:
        project = ProjectFactory(status=ProjectStatus.ICE_BOX)
        competition = CompetitionFactory(projects=[project])
        CompetitionReviewerFactory(user=user, competition=competition)

        response = client.get(f"/api/my/reviews/projects/{project.id}", **auth_headers)

        assert_that(response.status_code, equal_to(404))


@pytest.mark.django_db
class TestMyReviewProjectExclusions:
    def test_competition_list_excludes_rejected_projects_from_count(
        self, client, user, auth_headers
    ) -> None:
        approved_project = ProjectFactory(status=ProjectStatus.APPROVED)
        pending_project = ProjectFactory(status=ProjectStatus.PENDING)
        rejected_project = ProjectFactory(status=ProjectStatus.REJECTED)
        competition = CompetitionFactory(
            projects=[approved_project, pending_project, rejected_project]
        )
        CompetitionReviewerFactory(user=user, competition=competition)

        response = client.get("/api/my/reviews/competitions", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        # Only approved and pending should be counted (rejected excluded)
        assert_that(response.json()["competitions"][0]["project_count"], equal_to(2))

    def test_competition_list_excludes_ice_box_projects_from_count(
        self, client, user, auth_headers
    ) -> None:
        approved_project = ProjectFactory(status=ProjectStatus.APPROVED)
        ice_box_project = ProjectFactory(status=ProjectStatus.ICE_BOX)
        competition = CompetitionFactory(projects=[approved_project, ice_box_project])
        CompetitionReviewerFactory(user=user, competition=competition)

        response = client.get("/api/my/reviews/competitions", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        # Only approved should be counted (ice_box excluded)
        assert_that(response.json()["competitions"][0]["project_count"], equal_to(1))

    def test_competition_detail_excludes_rejected_projects(
        self, client, user, auth_headers
    ) -> None:
        approved_project = ProjectFactory(
            title="Approved", status=ProjectStatus.APPROVED
        )
        rejected_project = ProjectFactory(
            title="Rejected", status=ProjectStatus.REJECTED
        )
        competition = CompetitionFactory(projects=[approved_project, rejected_project])
        CompetitionReviewerFactory(user=user, competition=competition)

        response = client.get(
            f"/api/my/reviews/competitions/{competition.id}", **auth_headers
        )

        assert_that(response.status_code, equal_to(200))
        projects = response.json()["projects"]
        assert_that(projects, has_length(1))
        assert_that(projects[0]["title"], equal_to("Approved"))

    def test_competition_detail_excludes_ice_box_projects(
        self, client, user, auth_headers
    ) -> None:
        pending_project = ProjectFactory(title="Pending", status=ProjectStatus.PENDING)
        ice_box_project = ProjectFactory(title="IceBox", status=ProjectStatus.ICE_BOX)
        competition = CompetitionFactory(projects=[pending_project, ice_box_project])
        CompetitionReviewerFactory(user=user, competition=competition)

        response = client.get(
            f"/api/my/reviews/competitions/{competition.id}", **auth_headers
        )

        assert_that(response.status_code, equal_to(200))
        projects = response.json()["projects"]
        assert_that(projects, has_length(1))
        assert_that(projects[0]["title"], equal_to("Pending"))

    def test_cannot_rank_rejected_project(self, client, user, auth_headers) -> None:
        approved_project = ProjectFactory(status=ProjectStatus.APPROVED)
        rejected_project = ProjectFactory(status=ProjectStatus.REJECTED)
        competition = CompetitionFactory(projects=[approved_project, rejected_project])
        CompetitionReviewerFactory(user=user, competition=competition)

        response = client.put(
            f"/api/my/reviews/competitions/{competition.id}/rankings",
            data=json.dumps({"project_ids": [str(rejected_project.id)]}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))
        assert_that(
            response.json()["detail"],
            equal_to("One or more projects do not belong to this competition"),
        )

    def test_cannot_rank_ice_box_project(self, client, user, auth_headers) -> None:
        approved_project = ProjectFactory(status=ProjectStatus.APPROVED)
        ice_box_project = ProjectFactory(status=ProjectStatus.ICE_BOX)
        competition = CompetitionFactory(projects=[approved_project, ice_box_project])
        CompetitionReviewerFactory(user=user, competition=competition)

        response = client.put(
            f"/api/my/reviews/competitions/{competition.id}/rankings",
            data=json.dumps({"project_ids": [str(ice_box_project.id)]}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))
        assert_that(
            response.json()["detail"],
            equal_to("One or more projects do not belong to this competition"),
        )
