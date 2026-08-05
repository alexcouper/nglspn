import pytest
from django.urls import reverse
from hamcrest import assert_that, equal_to, has_length, none

from apps.projects.models import ProjectStatus, ReviewStatus

from .factories import (
    CompetitionFactory,
    CompetitionReviewerFactory,
    ProjectFactory,
    ProjectRankingFactory,
    UserFactory,
)


def _make_competition_with_ballots(
    reviewers_and_ballots, completed=None, projects=None
):
    """Create a competition with projects and ballots.

    reviewers_and_ballots: list of (user, [project, ...]) tuples, each ballot in
        rank order. A ballot may name only some of the competition's projects.
    completed: set of users whose reviews are completed (defaults to all)
    projects: the competition's projects (defaults to the first ballot's)
    """
    if completed is None:
        completed = {u for u, _ in reviewers_and_ballots}
    if projects is None:
        projects = reviewers_and_ballots[0][1]

    competition = CompetitionFactory(projects=projects)

    for user, ballot in reviewers_and_ballots:
        status = (
            ReviewStatus.COMPLETED if user in completed else ReviewStatus.IN_PROGRESS
        )
        CompetitionReviewerFactory(user=user, competition=competition, status=status)
        for position, project in enumerate(ballot, start=1):
            ProjectRankingFactory(
                reviewer=user,
                competition=competition,
                project=project,
                position=position,
            )

    return competition


def _results_url(competition):
    return reverse(
        "admin:projects_competition_voting_results",
        args=[competition.pk],
    )


def _row_for(response, project):
    return next(
        row for row in response.context["results"] if row["project"].id == project.id
    )


def _ranks(response):
    return {row["project"].id: row["rank"] for row in response.context["results"]}


@pytest.mark.django_db
class TestVotingResultsAccess:
    def test_requires_staff_login(self, client):
        competition = CompetitionFactory()

        response = client.get(_results_url(competition))

        assert_that(response.status_code, equal_to(302))
        assert "/login/" in response.url

    def test_accessible_by_staff(self, admin_client):
        competition = CompetitionFactory()

        response = admin_client.get(_results_url(competition))

        assert_that(response.status_code, equal_to(200))


@pytest.mark.django_db
class TestVotingResultsOrdering:
    def test_ranks_projects_by_pairwise_preference(self, admin_client):
        p1, p2, p3 = ProjectFactory.create_batch(3)
        competition = _make_competition_with_ballots(
            [
                (UserFactory(), [p1, p2, p3]),
                (UserFactory(), [p1, p3, p2]),
                (UserFactory(), [p2, p1, p3]),
            ]
        )

        response = admin_client.get(_results_url(competition))

        assert_that(_ranks(response), equal_to({p1.id: 1, p2.id: 2, p3.id: 3}))

    def test_projects_the_rule_cannot_separate_share_a_rank(self, admin_client):
        p1, p2, p3 = ProjectFactory.create_batch(3)
        competition = _make_competition_with_ballots(
            [
                (UserFactory(), [p1, p2, p3]),
                (UserFactory(), [p2, p1, p3]),
            ]
        )

        ranks = _ranks(admin_client.get(_results_url(competition)))

        assert_that(ranks[p1.id], equal_to(1))
        assert_that(ranks[p2.id], equal_to(1))
        assert_that(ranks[p3.id], equal_to(3))

    def test_ignores_in_progress_reviewers(self, admin_client):
        p1, p2 = ProjectFactory.create_batch(2)
        completed_user = UserFactory()
        competition = _make_competition_with_ballots(
            [
                (completed_user, [p1, p2]),
                (UserFactory(), [p2, p1]),
            ],
            completed={completed_user},
        )

        response = admin_client.get(_results_url(competition))

        assert_that(response.context["counted_ballots"], equal_to(1))
        assert_that(_ranks(response), equal_to({p1.id: 1, p2.id: 2}))

    def test_excludes_rejected_and_iceboxed_projects(self, admin_client):
        ranked, rejected = (
            ProjectFactory(),
            ProjectFactory(status=ProjectStatus.REJECTED),
        )
        iceboxed = ProjectFactory(status=ProjectStatus.ICE_BOX)
        competition = _make_competition_with_ballots(
            [(UserFactory(), [rejected, ranked, iceboxed])],
            projects=[ranked, rejected, iceboxed],
        )

        response = admin_client.get(_results_url(competition))

        assert_that(response.context["results"], has_length(1))
        assert_that(_row_for(response, ranked)["rank"], equal_to(1))


@pytest.mark.django_db
class TestVotingResultsSupportSignals:
    def test_shows_how_many_ballots_ranked_each_project(self, admin_client):
        popular, thin = ProjectFactory.create_batch(2)
        competition = _make_competition_with_ballots(
            [
                (UserFactory(), [popular]),
                (UserFactory(), [popular]),
                (UserFactory(), [thin, popular]),
            ],
            projects=[popular, thin],
        )

        response = admin_client.get(_results_url(competition))

        assert_that(response.context["counted_ballots"], equal_to(3))
        assert_that(_row_for(response, popular)["ranked_by_count"], equal_to(3))
        assert_that(_row_for(response, thin)["ranked_by_count"], equal_to(1))

    def test_thin_support_is_visible_in_the_page(self, admin_client):
        ranked, ignored = ProjectFactory.create_batch(2)
        competition = _make_competition_with_ballots(
            [
                (UserFactory(), [ranked]),
                (UserFactory(), []),
                (UserFactory(), []),
            ],
            projects=[ranked, ignored],
        )

        response = admin_client.get(_results_url(competition))

        assert_that(_row_for(response, ranked)["ranked_by_count"], equal_to(1))
        assert "1 / 3" in response.content.decode()

    def test_counts_first_place_votes(self, admin_client):
        p1, p2, p3 = ProjectFactory.create_batch(3)
        competition = _make_competition_with_ballots(
            [
                (UserFactory(), [p1, p2, p3]),
                (UserFactory(), [p1, p3, p2]),
                (UserFactory(), [p2, p1, p3]),
            ]
        )

        response = admin_client.get(_results_url(competition))

        assert_that(_row_for(response, p1)["first_place_count"], equal_to(2))
        assert_that(_row_for(response, p2)["first_place_count"], equal_to(1))
        assert_that(_row_for(response, p3)["first_place_count"], equal_to(0))

    def test_mean_position_covers_only_ballots_that_ranked_the_project(
        self, admin_client
    ):
        p1, p2 = ProjectFactory.create_batch(2)
        competition = _make_competition_with_ballots(
            [
                (UserFactory(), [p1, p2]),
                (UserFactory(), [p2]),
                (UserFactory(), []),
            ]
        )

        response = admin_client.get(_results_url(competition))

        assert_that(_row_for(response, p1)["mean_position"], equal_to(1.0))
        assert_that(_row_for(response, p2)["mean_position"], equal_to(1.5))

    def test_mean_position_is_blank_for_an_unranked_project(self, admin_client):
        ranked, never_ranked = ProjectFactory.create_batch(2)
        competition = _make_competition_with_ballots(
            [(UserFactory(), [ranked])],
            projects=[ranked, never_ranked],
        )

        response = admin_client.get(_results_url(competition))

        assert_that(_row_for(response, never_ranked)["mean_position"], none())


@pytest.mark.django_db
class TestVotingResultsPairwiseGrid:
    def test_shows_a_margin_for_every_ordered_pair(self, admin_client):
        projects = ProjectFactory.create_batch(4)
        competition = _make_competition_with_ballots(
            [(UserFactory(), projects)],
        )

        response = admin_client.get(_results_url(competition))

        assert_that(response.context["grid_headers"], has_length(4))
        for row in response.context["results"]:
            assert_that(row["margins"], has_length(4))

    def test_margin_is_positive_for_the_preferred_project(self, admin_client):
        winner, loser = ProjectFactory.create_batch(2)
        competition = _make_competition_with_ballots(
            [
                (UserFactory(), [winner, loser]),
                (UserFactory(), [winner, loser]),
                (UserFactory(), [loser, winner]),
            ]
        )

        response = admin_client.get(_results_url(competition))

        assert_that(_row_for(response, winner)["margins"], equal_to([None, 1]))
        assert_that(_row_for(response, loser)["margins"], equal_to([-1, None]))

    def test_partial_ballots_leave_unranked_pairs_at_zero(self, admin_client):
        ranked, ignored_one, ignored_two = ProjectFactory.create_batch(3)
        competition = _make_competition_with_ballots(
            [(UserFactory(), [ranked])],
            projects=[ranked, ignored_one, ignored_two],
        )

        response = admin_client.get(_results_url(competition))

        others = _row_for(response, ignored_one)["margins"]
        assert_that([m for m in others if m is not None], equal_to([-1, 0]))


@pytest.mark.django_db
class TestVotingResultsWithoutBallots:
    def test_reports_no_counted_ballots_when_nobody_completed(self, admin_client):
        p1, p2 = ProjectFactory.create_batch(2)
        competition = _make_competition_with_ballots(
            [(UserFactory(), [p1, p2])],
            completed=set(),
        )

        response = admin_client.get(_results_url(competition))

        assert_that(response.status_code, equal_to(200))
        assert_that(response.context["counted_ballots"], equal_to(0))
        assert "No counted ballots yet" in response.content.decode()

    def test_shows_winner_when_set(self, admin_client):
        p1, p2 = ProjectFactory.create_batch(2)
        competition = CompetitionFactory(projects=[p1, p2], winner=p1)

        response = admin_client.get(_results_url(competition))

        assert_that(response.status_code, equal_to(200))
        assert p1.title.encode() in response.content


@pytest.mark.django_db
class TestVotingResultsIsAdvisory:
    def test_viewing_results_does_not_pick_a_winner(self, admin_client):
        clear_winner, other = ProjectFactory.create_batch(2)
        competition = _make_competition_with_ballots(
            [
                (UserFactory(), [clear_winner, other]),
                (UserFactory(), [clear_winner, other]),
            ]
        )

        response = admin_client.get(_results_url(competition))

        assert_that(_row_for(response, clear_winner)["rank"], equal_to(1))
        competition.refresh_from_db()
        assert_that(competition.winner, none())


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

        assert_that(response.status_code, equal_to(200))
        expected_url = reverse(
            "admin:projects_competition_voting_results",
            args=[competition.pk],
        )
        assert expected_url in response.content.decode()
        assert "View Voting Results" in response.content.decode()
