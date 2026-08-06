import pytest
from hamcrest import assert_that, equal_to, has_length, is_not

from apps.projects.models import ProjectStatus, ReviewStatus
from services.review.django_impl.query import DjangoReviewQuery
from tests.factories import (
    CompetitionFactory,
    CompetitionReviewerFactory,
    ProjectCategoryFactory,
    ProjectFactory,
    ProjectImageFactory,
    ProjectRankingFactory,
    UserFactory,
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
        cast_ballot(
            competition, UserFactory(), [loser, winner], status=ReviewStatus.ENDED
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
