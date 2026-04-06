import pytest
from django.urls import reverse

from apps.projects.models import ReviewStatus

from .factories import (
    CompetitionFactory,
    CompetitionReviewerFactory,
    ProjectFactory,
    ProjectRankingFactory,
    UserFactory,
)


def _make_competition_with_rankings(reviewers_and_orders, completed=None):
    """Create a competition with projects and rankings.

    reviewers_and_orders: list of (user, [project, project, ...]) tuples
        where the project list is in rank order (1st, 2nd, 3rd, ...)
    completed: set of users whose reviews are completed (defaults to all)
    """
    if completed is None:
        completed = {u for u, _ in reviewers_and_orders}

    all_projects = reviewers_and_orders[0][1]
    competition = CompetitionFactory(projects=all_projects)

    for user, ranked_projects in reviewers_and_orders:
        status = (
            ReviewStatus.COMPLETED if user in completed else ReviewStatus.IN_PROGRESS
        )
        CompetitionReviewerFactory(user=user, competition=competition, status=status)
        for position, project in enumerate(ranked_projects, start=1):
            ProjectRankingFactory(
                reviewer=user,
                competition=competition,
                project=project,
                position=position,
            )

    return competition


@pytest.mark.django_db
class TestVotingResultsView:
    def _url(self, competition):
        return reverse(
            "admin:projects_competition_voting_results",
            args=[competition.pk],
        )

    def test_requires_staff_login(self, client):
        competition = CompetitionFactory()
        response = client.get(self._url(competition))
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_accessible_by_staff(self, admin_client):
        competition = CompetitionFactory()
        response = admin_client.get(self._url(competition))
        assert response.status_code == 200

    def test_scoring_formula_single_reviewer(self, admin_client):
        p1, p2, p3 = ProjectFactory.create_batch(3)
        user = UserFactory()
        competition = _make_competition_with_rankings(
            [(user, [p1, p2, p3])],
        )

        response = admin_client.get(self._url(competition))
        assert response.status_code == 200

        results = response.context["results"]
        scores = {r["project"].id: r["total_score"] for r in results}
        assert scores[p1.id] == 3  # 1st place = 3 pts
        assert scores[p2.id] == 2  # 2nd place = 2 pts
        assert scores[p3.id] == 1  # 3rd place = 1 pt

    def test_multiple_reviewers_sum_scores(self, admin_client):
        p1, p2, p3 = ProjectFactory.create_batch(3)
        u1, u2 = UserFactory.create_batch(2)
        competition = _make_competition_with_rankings(
            [
                (u1, [p1, p2, p3]),  # u1: p1=3, p2=2, p3=1
                (u2, [p2, p1, p3]),  # u2: p2=3, p1=2, p3=1
            ]
        )

        response = admin_client.get(self._url(competition))
        results = response.context["results"]
        scores = {r["project"].id: r["total_score"] for r in results}

        assert scores[p1.id] == 5  # 3 + 2
        assert scores[p2.id] == 5  # 2 + 3
        assert scores[p3.id] == 2  # 1 + 1

    def test_ignores_in_progress_reviewers(self, admin_client):
        p1, p2 = ProjectFactory.create_batch(2)
        completed_user = UserFactory()
        in_progress_user = UserFactory()
        competition = _make_competition_with_rankings(
            [
                (completed_user, [p1, p2]),
                (in_progress_user, [p2, p1]),
            ],
            completed={completed_user},
        )

        response = admin_client.get(self._url(competition))
        results = response.context["results"]
        scores = {r["project"].id: r["total_score"] for r in results}

        # Only completed_user's rankings count
        assert scores[p1.id] == 2  # 1st = 2 pts
        assert scores[p2.id] == 1  # 2nd = 1 pt

    def test_tie_gives_same_rank(self, admin_client):
        p1, p2, p3 = ProjectFactory.create_batch(3)
        u1, u2 = UserFactory.create_batch(2)
        competition = _make_competition_with_rankings(
            [
                (u1, [p1, p2, p3]),
                (u2, [p2, p1, p3]),
            ]
        )

        response = admin_client.get(self._url(competition))
        results = response.context["results"]
        ranks = {r["project"].id: r["rank"] for r in results}

        # p1 and p2 are tied at 5 points, both rank 1
        assert ranks[p1.id] == 1
        assert ranks[p2.id] == 1
        # p3 is rank 3 (not 2, because two projects share rank 1)
        assert ranks[p3.id] == 3

    def test_first_place_vote_counts(self, admin_client):
        p1, p2, p3 = ProjectFactory.create_batch(3)
        u1, u2, u3 = UserFactory.create_batch(3)
        competition = _make_competition_with_rankings(
            [
                (u1, [p1, p2, p3]),
                (u2, [p1, p3, p2]),
                (u3, [p2, p1, p3]),
            ]
        )

        response = admin_client.get(self._url(competition))
        results = response.context["results"]
        first_place = {r["project"].id: r["position_counts"][1] for r in results}

        assert first_place[p1.id] == 2  # p1 got 1st place twice
        assert first_place[p2.id] == 1  # p2 got 1st place once
        assert first_place[p3.id] == 0  # p3 never got 1st place

    def test_empty_no_completed_reviewers(self, admin_client):
        p1, p2 = ProjectFactory.create_batch(2)
        user = UserFactory()
        competition = _make_competition_with_rankings(
            [(user, [p1, p2])],
            completed=set(),  # none completed
        )

        response = admin_client.get(self._url(competition))
        assert response.status_code == 200
        assert response.context["total_voters"] == 0
        results = response.context["results"]
        assert all(r["total_score"] == 0 for r in results)

    def test_shows_winner_when_set(self, admin_client):
        p1, p2 = ProjectFactory.create_batch(2)
        competition = CompetitionFactory(projects=[p1, p2], winner=p1)

        response = admin_client.get(self._url(competition))
        assert response.status_code == 200
        assert p1.title.encode() in response.content

    def test_position_distribution(self, admin_client):
        p1, p2 = ProjectFactory.create_batch(2)
        u1, u2, u3 = UserFactory.create_batch(3)
        competition = _make_competition_with_rankings(
            [
                (u1, [p1, p2]),
                (u2, [p1, p2]),
                (u3, [p2, p1]),
            ]
        )

        response = admin_client.get(self._url(competition))
        results = response.context["results"]
        dist = {r["project"].id: dict(r["position_counts"]) for r in results}

        assert dist[p1.id] == {1: 2, 2: 1}  # p1: twice 1st, once 2nd
        assert dist[p2.id] == {1: 1, 2: 2}  # p2: once 1st, twice 2nd


@pytest.mark.django_db
class TestVotingResultsButton:
    def test_change_form_has_voting_results_link(self, admin_client):
        p1 = ProjectFactory()
        competition = CompetitionFactory(projects=[p1])

        url = reverse(
            "admin:projects_competition_change",
            args=[competition.pk],
        )
        response = admin_client.get(url)

        assert response.status_code == 200
        expected_url = reverse(
            "admin:projects_competition_voting_results",
            args=[competition.pk],
        )
        assert expected_url in response.content.decode()
        assert "View Voting Results" in response.content.decode()
