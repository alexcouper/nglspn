from datetime import date

import pytest
from hamcrest import (
    assert_that,
    contains_exactly,
    equal_to,
    has_length,
    is_,
    is_not,
    none,
)

from apps.projects.models import CompetitionStatus, ProjectStatus, ReviewStatus
from services.review.django_impl.query import DjangoReviewQuery
from services.review.eligibility import REVIEW_ENDED, effective_status
from tests.factories import (
    CompetitionFactory,
    CompetitionReviewerFactory,
    ProjectCategoryFactory,
    ProjectFactory,
    ProjectImageFactory,
    ProjectRankingFactory,
    ReviewerGroupFactory,
    UserFactory,
    review_of,
    voting_competition,
)


@pytest.fixture
def query():
    return DjangoReviewQuery()


def competition_with_projects(count: int, **project_kwargs):
    projects = [ProjectFactory(**project_kwargs) for _ in range(count)]
    return CompetitionFactory(projects=projects), projects


def cast_ballot(competition, reviewer, projects, status=ReviewStatus.COMPLETED):
    CompetitionReviewerFactory(competition=competition, user=reviewer, status=status)
    for position, project in enumerate(projects, start=1):
        ProjectRankingFactory(
            reviewer=reviewer,
            competition=competition,
            project=project,
            position=position,
        )
    return reviewer


def titles(projects) -> list[str]:
    return [p.title for p in projects]


def ballot_titles(items) -> list[str]:
    """Titles of a `ReviewerProjects` list, which holds items, not projects."""
    return [item.project.title for item in items]


def prefetched_images(item) -> list:
    """Image ids the ballot query handed back, without hitting the database.

    Reads `project.images.all()` so it sees the prefetch cache rather than
    re-querying — which is exactly what the image resolution does.
    """
    return [image.id for image in item.project.images.all()]


def flat_order(tally) -> list:
    return [project_id for tier in tally.tiers for project_id in tier]


@pytest.mark.django_db
class TestGetCompetitionTally:
    def test_orders_projects_by_the_completed_ballots(self, query) -> None:
        competition, (first, second, third) = competition_with_projects(3)
        for _ in range(3):
            cast_ballot(competition, UserFactory(), [first, second, third])

        tally = query.get_competition_tally(competition.id)

        assert_that(tally.tiers, equal_to([[first.id], [second.id], [third.id]]))
        assert_that(tally.counted_ballots, equal_to(3))

    def test_excludes_reviewers_who_have_not_completed(self, query) -> None:
        competition, (winner, loser) = competition_with_projects(2)
        cast_ballot(competition, UserFactory(), [winner, loser])
        cast_ballot(
            competition,
            UserFactory(),
            [loser, winner],
            status=ReviewStatus.IN_PROGRESS,
        )

        tally = query.get_competition_tally(competition.id)

        assert_that(tally.counted_ballots, equal_to(1))
        assert_that(tally.margins[winner.id][loser.id], equal_to(1))

    def test_excludes_rejected_and_iceboxed_projects(self, query) -> None:
        competition, (kept, other) = competition_with_projects(2)
        rejected = ProjectFactory(status=ProjectStatus.REJECTED)
        iceboxed = ProjectFactory(status=ProjectStatus.ICE_BOX)
        competition.projects.add(rejected, iceboxed)
        cast_ballot(competition, UserFactory(), [rejected, kept, iceboxed, other])

        tally = query.get_competition_tally(competition.id)

        assert_that(sorted(tally.projects), equal_to(sorted([kept.id, other.id])))
        assert_that(flat_order(tally), equal_to([kept.id, other.id]))
        assert_that(tally.margins[kept.id][other.id], equal_to(1))

    def test_partial_ballot_leaves_unranked_pairs_untouched(self, query) -> None:
        competition, (ranked, ignored_one, ignored_two) = competition_with_projects(3)
        cast_ballot(competition, UserFactory(), [ranked])

        tally = query.get_competition_tally(competition.id)

        assert_that(tally.margins[ranked.id][ignored_one.id], equal_to(1))
        assert_that(tally.margins[ignored_one.id][ignored_two.id], equal_to(0))

    def test_reports_support_signals_per_project(self, query) -> None:
        competition, (favourite, runner_up, unloved) = competition_with_projects(3)
        cast_ballot(competition, UserFactory(), [favourite, runner_up])
        cast_ballot(competition, UserFactory(), [runner_up, favourite])
        cast_ballot(competition, UserFactory(), [favourite])

        support = query.get_competition_tally(competition.id).support

        assert_that(support[favourite.id].first_place_count, equal_to(2))
        assert_that(support[favourite.id].ranked_by_count, equal_to(3))
        assert_that(support[favourite.id].mean_position, equal_to(4 / 3))
        assert_that(support[runner_up.id].ranked_by_count, equal_to(2))
        assert_that(support[unloved.id].ranked_by_count, equal_to(0))
        assert_that(support[unloved.id].mean_position, equal_to(None))

    def test_a_completed_reviewer_who_ranked_nothing_still_counts(self, query) -> None:
        competition, _projects = competition_with_projects(2)
        cast_ballot(competition, UserFactory(), [])

        tally = query.get_competition_tally(competition.id)

        assert_that(tally.counted_ballots, equal_to(1))
        assert_that(tally.tiers, has_length(1))

    def test_no_completed_reviewers_yields_no_counted_ballots(self, query) -> None:
        competition, projects = competition_with_projects(2)
        cast_ballot(
            competition, UserFactory(), projects, status=ReviewStatus.IN_PROGRESS
        )

        tally = query.get_competition_tally(competition.id)

        assert_that(tally.counted_ballots, equal_to(0))

    def test_separates_projects_the_ordering_rule_left_tied(self, query) -> None:
        # Four ballots leave `first` and `second` on a margin of exactly 0, so
        # Schulze puts them in one tier. Both are ranked by three reviewers, so
        # breadth is level too and the ladder falls through to mean position:
        # `second` averages 4/3 against `first`'s 5/3.
        competition, (first, second, third) = competition_with_projects(3)
        cast_ballot(competition, UserFactory(), [first, second, third])
        cast_ballot(competition, UserFactory(), [second, first, third])
        cast_ballot(competition, UserFactory(), [third, first])
        cast_ballot(competition, UserFactory(), [second])

        tally = query.get_competition_tally(competition.id)

        assert_that(flat_order(tally)[0], equal_to(second.id))
        assert_that(tally.tie_breaks[second.id].rung, equal_to("better mean position"))
        assert_that(tally.tie_breaks[second.id].tied_with, equal_to((first.id,)))

    def test_reports_no_tie_break_when_the_rule_already_decided(self, query) -> None:
        competition, (first, second) = competition_with_projects(2)
        cast_ballot(competition, UserFactory(), [first, second])

        tally = query.get_competition_tally(competition.id)

        assert_that(tally.tie_breaks, equal_to({}))

    def test_uses_the_ordering_rule_it_was_given(self) -> None:
        competition, (first, second) = competition_with_projects(2)
        cast_ballot(competition, UserFactory(), [first, second])
        reversed_rule = lambda margins: [[p] for p in reversed(list(margins))]  # noqa: E731

        tally = DjangoReviewQuery(ordering_rule=reversed_rule).get_competition_tally(
            competition.id
        )

        assert_that(flat_order(tally), equal_to(list(reversed(list(tally.projects)))))


@pytest.mark.django_db
class TestGetReviewerProjects:
    def test_unranked_competition_puts_every_project_in_the_pool(self, query) -> None:
        competition, projects = competition_with_projects(4)
        reviewer = UserFactory()

        result = query.get_reviewer_projects(reviewer.id, competition.id)

        assert_that(result.ranked, equal_to([]))
        assert_that(
            sorted(ballot_titles(result.pool)), equal_to(sorted(titles(projects)))
        )

    def test_ranked_projects_come_back_in_saved_position_order(self, query) -> None:
        competition, projects = competition_with_projects(4)
        reviewer = UserFactory()
        third, first, second = projects[0], projects[1], projects[2]
        cast_ballot(competition, reviewer, [first, second, third])

        result = query.get_reviewer_projects(reviewer.id, competition.id)

        assert_that(
            ballot_titles(result.ranked), equal_to(titles([first, second, third]))
        )
        assert_that(ballot_titles(result.pool), equal_to([projects[3].title]))

    def test_excludes_rejected_and_iceboxed_projects(self, query) -> None:
        competition, (kept,) = competition_with_projects(1)
        competition.projects.add(ProjectFactory(status=ProjectStatus.REJECTED))
        competition.projects.add(ProjectFactory(status=ProjectStatus.ICE_BOX))
        reviewer = UserFactory()

        result = query.get_reviewer_projects(reviewer.id, competition.id)

        assert_that(ballot_titles(result.pool), equal_to([kept.title]))

    def test_hides_images_that_are_still_uploading(self, query) -> None:
        competition, (project,) = competition_with_projects(1)
        ProjectImageFactory(project=project, upload_status="pending", is_main=True)
        reviewer = UserFactory()

        result = query.get_reviewer_projects(reviewer.id, competition.id)

        assert_that(prefetched_images(result.pool[0]), equal_to([]))

    def test_keeps_uploaded_images(self, query) -> None:
        competition, (project,) = competition_with_projects(1)
        uploaded = ProjectImageFactory(project=project, is_main=True)
        reviewer = UserFactory()

        result = query.get_reviewer_projects(reviewer.id, competition.id)

        assert_that(prefetched_images(result.pool[0]), equal_to([uploaded.id]))

    def test_resolves_the_category_and_purpose_images_for_the_ballot(
        self, query
    ) -> None:
        competition, (project,) = competition_with_projects(
            1, category=ProjectCategoryFactory(name="Conservation")
        )
        in_use = ProjectImageFactory(project=project, is_usage=True)
        hero = ProjectImageFactory(project=project, is_hero=True)
        reviewer = UserFactory()

        entry = query.get_reviewer_projects(reviewer.id, competition.id).pool[0]

        assert_that(entry.category_name, equal_to("Conservation"))
        assert_that(entry.in_use_image_url, equal_to(in_use.url))
        assert_that(entry.hero_banner_url, equal_to(hero.url))

    def test_resolves_no_image_when_the_only_one_is_still_uploading(
        self, query
    ) -> None:
        competition, (project,) = competition_with_projects(1)
        ProjectImageFactory(project=project, is_main=True, upload_status="pending")
        reviewer = UserFactory()

        entry = query.get_reviewer_projects(reviewer.id, competition.id).pool[0]

        assert_that(entry.in_use_image_url, equal_to(None))
        assert_that(entry.hero_banner_url, equal_to(None))

    def test_resolves_the_images_without_a_query_per_project(
        self, query, django_assert_num_queries
    ) -> None:
        competition, projects = competition_with_projects(4)
        for project in projects:
            ProjectImageFactory(project=project, is_usage=True)
        reviewer = UserFactory()

        result = query.get_reviewer_projects(reviewer.id, competition.id)

        with django_assert_num_queries(0):
            urls = [entry.in_use_image_url for entry in result.pool]
        assert_that(urls, has_length(len(projects)))

    def test_reads_the_category_without_a_query_per_project(
        self, query, django_assert_num_queries
    ) -> None:
        competition, projects = competition_with_projects(
            4, category=ProjectCategoryFactory()
        )
        reviewer = UserFactory()

        result = query.get_reviewer_projects(reviewer.id, competition.id)
        with django_assert_num_queries(0):
            categories = [item.category_name for item in result.pool]

        assert_that(categories, has_length(len(projects)))


@pytest.mark.django_db
class TestUnrankedPoolOrdering:
    def test_is_stable_for_the_same_reviewer(self, query) -> None:
        competition, _projects = competition_with_projects(8)
        reviewer = UserFactory()

        first_load = query.get_reviewer_projects(reviewer.id, competition.id)
        second_load = query.get_reviewer_projects(reviewer.id, competition.id)

        assert_that(
            ballot_titles(first_load.pool), equal_to(ballot_titles(second_load.pool))
        )

    def test_differs_between_reviewers(self, query) -> None:
        competition, _projects = competition_with_projects(8)

        one = query.get_reviewer_projects(UserFactory().id, competition.id)
        other = query.get_reviewer_projects(UserFactory().id, competition.id)

        assert_that(
            ballot_titles(one.pool), is_not(equal_to(ballot_titles(other.pool)))
        )

    def test_differs_between_competitions_for_one_reviewer(self, query) -> None:
        projects = [ProjectFactory() for _ in range(8)]
        one = CompetitionFactory(projects=projects)
        other = CompetitionFactory(projects=projects)
        reviewer = UserFactory()

        first_pool = query.get_reviewer_projects(reviewer.id, one.id)
        second_pool = query.get_reviewer_projects(reviewer.id, other.id)

        assert_that(
            ballot_titles(first_pool.pool),
            is_not(equal_to(ballot_titles(second_pool.pool))),
        )

    def test_ignores_creation_order(self, query) -> None:
        competition, projects = competition_with_projects(8)
        reviewer = UserFactory()

        pool = query.get_reviewer_projects(reviewer.id, competition.id).pool

        assert_that(ballot_titles(pool), is_not(equal_to(titles(projects))))
        assert_that(
            ballot_titles(pool), is_not(equal_to(titles(list(reversed(projects)))))
        )

    def test_does_not_reorder_the_ranked_projects(self, query) -> None:
        competition, projects = competition_with_projects(8)
        reviewer = UserFactory()
        cast_ballot(competition, reviewer, projects)

        result = query.get_reviewer_projects(reviewer.id, competition.id)

        assert_that(ballot_titles(result.ranked), equal_to(titles(projects)))
        assert_that(result.pool, equal_to([]))


NOT_VOTING = [
    CompetitionStatus.PENDING,
    CompetitionStatus.ACCEPTING_APPLICATIONS,
    CompetitionStatus.CLOSED,
]


def listed(query, user) -> list[tuple[str, str, bool]]:
    return [
        (entry.competition.name, entry.status, entry.can_write)
        for entry in query.review_competitions_for(user.id)
    ]


@pytest.mark.django_db
class TestCanReview:
    def test_any_active_user_can_review_a_voting_competition_for_everyone(
        self, query
    ) -> None:
        competition = voting_competition()

        assert_that(query.can_review(UserFactory().id, competition.id), is_(True))

    @pytest.mark.parametrize("status", NOT_VOTING)
    def test_nobody_can_review_a_competition_that_is_not_voting(
        self, query, status
    ) -> None:
        competition = CompetitionFactory(status=status)

        assert_that(query.can_review(UserFactory().id, competition.id), is_(False))

    def test_an_inactive_user_cannot_review(self, query) -> None:
        competition = voting_competition()
        user = UserFactory(is_active=False)

        assert_that(query.can_review(user.id, competition.id), is_(False))

    def test_a_system_user_cannot_review(self, query) -> None:
        competition = voting_competition()
        user = UserFactory(is_system_user=True)

        assert_that(query.can_review(user.id, competition.id), is_(False))

    def test_a_panel_member_can_review_the_panels_competition(self, query) -> None:
        member = UserFactory()
        competition = voting_competition(group=ReviewerGroupFactory(members=[member]))

        assert_that(query.can_review(member.id, competition.id), is_(True))

    def test_a_non_member_cannot_review_a_panels_competition(self, query) -> None:
        panel = ReviewerGroupFactory(members=[UserFactory(), UserFactory()])
        competition = voting_competition(group=panel)

        assert_that(query.can_review(UserFactory().id, competition.id), is_(False))

    def test_an_inactive_panel_member_cannot_review(self, query) -> None:
        member = UserFactory(is_active=False)
        competition = voting_competition(group=ReviewerGroupFactory(members=[member]))

        assert_that(query.can_review(member.id, competition.id), is_(False))


@pytest.mark.django_db
class TestReviewCompetitionsFor:
    def test_lists_an_open_competition_the_user_has_not_started(self, query) -> None:
        voting_competition(name="Open")

        assert_that(
            listed(query, UserFactory()),
            contains_exactly(("Open", ReviewStatus.IN_PROGRESS, True)),
        )

    def test_lists_a_closed_competition_the_user_reviewed(self, query) -> None:
        user = UserFactory()
        closed = CompetitionFactory(name="Past", status=CompetitionStatus.CLOSED)
        review_of(user, closed, status=ReviewStatus.COMPLETED)

        assert_that(
            listed(query, user),
            contains_exactly(("Past", ReviewStatus.COMPLETED, False)),
        )

    def test_omits_a_closed_competition_the_user_never_reviewed(self, query) -> None:
        CompetitionFactory(status=CompetitionStatus.CLOSED)

        assert_that(listed(query, UserFactory()), equal_to([]))

    def test_omits_a_panel_competition_the_user_is_not_on(self, query) -> None:
        voting_competition(group=ReviewerGroupFactory(members=[UserFactory()]))

        assert_that(listed(query, UserFactory()), equal_to([]))

    def test_an_unfinished_review_reads_as_ended_once_closed(self, query) -> None:
        user = UserFactory()
        closed = CompetitionFactory(name="Past", status=CompetitionStatus.CLOSED)
        review_of(user, closed, status=ReviewStatus.IN_PROGRESS)

        assert_that(
            listed(query, user), contains_exactly(("Past", REVIEW_ENDED, False))
        )

    def test_lists_a_started_open_competition_once(self, query) -> None:
        user = UserFactory()
        competition = voting_competition(name="Open")
        review_of(user, competition)

        assert_that(listed(query, user), has_length(1))

    def test_lists_newest_first(self, query) -> None:
        voting_competition(name="Older", start_date=date(2025, 1, 1))
        voting_competition(name="Newer", start_date=date(2025, 6, 1))

        names = [name for name, _, _ in listed(query, UserFactory())]

        assert_that(names, equal_to(["Newer", "Older"]))


@pytest.mark.django_db
class TestGetReviewCompetition:
    def test_is_none_for_a_closed_competition_without_a_review(self, query) -> None:
        closed = CompetitionFactory(status=CompetitionStatus.CLOSED)

        assert_that(
            query.get_review_competition(UserFactory().id, closed.id), is_(none())
        )

    def test_is_read_only_for_a_past_reviewer(self, query) -> None:
        user = UserFactory()
        closed = CompetitionFactory(status=CompetitionStatus.CLOSED)
        review_of(user, closed, status=ReviewStatus.COMPLETED)

        entry = query.get_review_competition(user.id, closed.id)

        assert_that(entry.can_write, is_(False))
        assert_that(entry.status, equal_to(ReviewStatus.COMPLETED))


@pytest.mark.django_db
class TestCanViewReviewProject:
    def test_allows_a_project_in_an_open_competition(self, query) -> None:
        project = ProjectFactory()
        voting_competition(projects=[project])

        assert_that(
            query.can_view_review_project(UserFactory().id, project.id), is_(True)
        )

    def test_allows_a_project_in_a_closed_competition_the_user_reviewed(
        self, query
    ) -> None:
        user, project = UserFactory(), ProjectFactory()
        closed = CompetitionFactory(status=CompetitionStatus.CLOSED, projects=[project])
        review_of(user, closed)

        assert_that(query.can_view_review_project(user.id, project.id), is_(True))

    def test_refuses_a_project_in_a_closed_competition_the_user_never_reviewed(
        self, query
    ) -> None:
        project = ProjectFactory()
        CompetitionFactory(status=CompetitionStatus.CLOSED, projects=[project])

        assert_that(
            query.can_view_review_project(UserFactory().id, project.id), is_(False)
        )


VOTING, CLOSED = CompetitionStatus.VOTING, CompetitionStatus.CLOSED
IN_PROGRESS, COMPLETED = ReviewStatus.IN_PROGRESS, ReviewStatus.COMPLETED


class TestEffectiveStatus:
    @pytest.mark.parametrize(
        ("row_status", "competition_status", "expected"),
        [
            (None, VOTING, IN_PROGRESS),
            (IN_PROGRESS, VOTING, IN_PROGRESS),
            (COMPLETED, VOTING, COMPLETED),
            (None, CLOSED, REVIEW_ENDED),
            (IN_PROGRESS, CLOSED, REVIEW_ENDED),
            (COMPLETED, CLOSED, COMPLETED),
            (IN_PROGRESS, CompetitionStatus.PENDING, REVIEW_ENDED),
        ],
    )
    def test_reads_ended_only_when_voting_is_over_and_unfinished(
        self, row_status, competition_status, expected
    ) -> None:
        assert_that(
            effective_status(row_status, competition_status), equal_to(expected)
        )
