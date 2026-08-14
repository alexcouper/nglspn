import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from hamcrest import assert_that, contains_inanyorder, empty, equal_to, is_, none

from apps.projects.models import (
    CompetitionStatus,
    ContributorRole,
    ProjectContributor,
    ProjectStatus,
)
from apps.users.seed import COMMUNITY_USER_ID
from services.project.django_impl import DjangoProjectQuery
from services.project.query_interface import IneligibleReason
from tests.factories import (
    CompetitionEntryFactory,
    CompetitionFactory,
    ProjectFactory,
    UserFactory,
)

query = DjangoProjectQuery()


def open_competition(**kwargs):
    return CompetitionFactory(
        status=CompetitionStatus.ACCEPTING_APPLICATIONS,
        **kwargs,
    )


def published_project(**kwargs):
    return ProjectFactory(status=ProjectStatus.PENDING, **kwargs)


def community_tipoff():
    """`is_community_tipoff` is derived from contributors by a signal, so it is
    made by giving the project the community user as OWNER, not by setting the
    flag."""
    project = ProjectFactory(status=ProjectStatus.PENDING, _contributor=False)
    ProjectContributor.objects.create(
        project=project,
        user_id=COMMUNITY_USER_ID,
        role=ContributorRole.OWNER,
        full_edit=True,
    )
    project.refresh_from_db()
    return project


def opportunity_for(standing, competition):
    return next(
        candidate
        for candidate in standing.opportunities
        if candidate.competition.id == competition.id
    )


def assert_eligible_for(standing, competition):
    assert_that(opportunity_for(standing, competition).eligible, is_(True))


def assert_blocked_for(standing, competition, reason):
    opportunity = opportunity_for(standing, competition)
    assert_that(opportunity.eligible, is_(False))
    assert_that(opportunity.reason, equal_to(reason))


@pytest.mark.django_db
class TestOpportunities:
    def test_published_project_is_eligible_for_an_open_competition(self):
        competition = open_competition()

        standing = query.competition_standing(published_project())

        assert_eligible_for(standing, competition)

    def test_a_draft_cannot_enter_until_it_is_published(self):
        """The endpoint refuses a draft, so the standing has to say so too —
        otherwise every surface offers a control that 400s."""
        competition = open_competition()

        standing = query.competition_standing(
            ProjectFactory(status=ProjectStatus.DRAFT)
        )

        assert_blocked_for(standing, competition, IneligibleReason.PROJECT_DRAFT)

    def test_a_tipoff_draft_reports_the_tipoff_reason(self):
        """Rule order: being somebody else's project outranks being unpublished."""
        competition = open_competition()
        project = community_tipoff()
        project.status = ProjectStatus.DRAFT
        project.save(update_fields=["status"])

        standing = query.competition_standing(project)

        assert_blocked_for(standing, competition, IneligibleReason.COMMUNITY_PROJECT)

    def test_every_open_competition_gets_its_own_opportunity(self):
        monthly = open_competition(entry_series="monthly")
        hackathon = open_competition(entry_series="summer-hackathon")

        standing = query.competition_standing(published_project())

        assert_that(
            [o.competition.id for o in standing.opportunities],
            contains_inanyorder(monthly.id, hackathon.id),
        )
        assert_eligible_for(standing, monthly)
        assert_eligible_for(standing, hackathon)

    def test_an_open_round_the_project_is_in_is_not_an_opportunity(self):
        """The entry is the answer for that round. Reporting it again as an
        opportunity listed it twice and named it as its own blocker."""
        project = published_project()
        entered = open_competition(entry_series="monthly")
        CompetitionEntryFactory(competition=entered, project=project)

        standing = query.competition_standing(project)

        assert_that(
            [entry.competition.id for entry in standing.entries],
            equal_to([entered.id]),
        )
        assert_that(standing.opportunities, is_(empty()))

    def test_a_different_open_round_of_the_same_series_is_still_reported(self):
        project = published_project()
        entered = open_competition(entry_series="monthly")
        CompetitionEntryFactory(competition=entered, project=project)
        other = open_competition(entry_series="monthly")

        standing = query.competition_standing(project)

        assert_blocked_for(standing, other, IneligibleReason.ALREADY_IN_SERIES)
        assert_that(
            opportunity_for(standing, other).blocking_entry.id, equal_to(entered.id)
        )

    def test_the_two_lists_never_name_the_same_competition(self):
        project = published_project()
        CompetitionEntryFactory(
            competition=open_competition(entry_series="summer"), project=project
        )
        open_competition(entry_series="monthly")

        standing = query.competition_standing(project)

        entered_ids = {entry.competition.id for entry in standing.entries}
        offered_ids = {o.competition.id for o in standing.opportunities}
        assert_that(entered_ids & offered_ids, equal_to(set()))

    def test_a_competition_that_is_not_open_is_not_an_opportunity(self):
        CompetitionFactory(status=CompetitionStatus.VOTING)

        standing = query.competition_standing(published_project())

        assert_that(standing.opportunities, is_(empty()))

    def test_no_open_competition_is_an_empty_list_not_a_reason(self):
        standing = query.competition_standing(published_project())

        assert_that(standing.opportunities, is_(empty()))
        assert_that(standing.entries, is_(empty()))


@pytest.mark.django_db
class TestSeriesExclusivity:
    def test_an_entry_blocks_another_competition_in_the_same_series(self):
        project = published_project()
        june = CompetitionFactory(
            entry_series="monthly", status=CompetitionStatus.CLOSED
        )
        CompetitionEntryFactory(competition=june, project=project)
        july = open_competition(entry_series="monthly")

        standing = query.competition_standing(project)

        assert_blocked_for(standing, july, IneligibleReason.ALREADY_IN_SERIES)

    def test_the_blocking_competition_is_named(self):
        project = published_project()
        june = CompetitionFactory(
            entry_series="monthly", status=CompetitionStatus.CLOSED
        )
        CompetitionEntryFactory(competition=june, project=project)
        july = open_competition(entry_series="monthly")

        standing = query.competition_standing(project)

        assert_that(
            opportunity_for(standing, july).blocking_entry.id, equal_to(june.id)
        )

    def test_an_entry_does_not_block_a_different_series(self):
        project = published_project()
        CompetitionEntryFactory(
            competition=CompetitionFactory(entry_series="monthly"),
            project=project,
        )
        hackathon = open_competition(entry_series="summer-hackathon")

        standing = query.competition_standing(project)

        assert_eligible_for(standing, hackathon)

    def test_entered_in_one_series_and_eligible_in_another(self):
        project = published_project()
        CompetitionEntryFactory(
            competition=CompetitionFactory(entry_series="monthly"),
            project=project,
        )
        july = open_competition(entry_series="monthly")
        hackathon = open_competition(entry_series="summer-hackathon")

        standing = query.competition_standing(project)

        assert_blocked_for(standing, july, IneligibleReason.ALREADY_IN_SERIES)
        assert_eligible_for(standing, hackathon)


@pytest.mark.django_db
class TestProjectWideReasons:
    def test_community_tipoff_is_never_eligible(self):
        competition = open_competition()
        standing = query.competition_standing(community_tipoff())

        assert_blocked_for(standing, competition, IneligibleReason.COMMUNITY_PROJECT)

    @pytest.mark.parametrize("status", [ProjectStatus.REJECTED, ProjectStatus.ICE_BOX])
    def test_rejected_and_iceboxed_projects_are_not_eligible(self, status):
        competition = open_competition()

        standing = query.competition_standing(ProjectFactory(status=status))

        assert_blocked_for(standing, competition, IneligibleReason.PROJECT_STATUS)

    def test_tipoff_takes_precedence_over_the_series_rule(self):
        project = community_tipoff()
        CompetitionEntryFactory(
            competition=CompetitionFactory(entry_series="monthly"),
            project=project,
        )
        july = open_competition(entry_series="monthly")

        standing = query.competition_standing(project)

        assert_blocked_for(standing, july, IneligibleReason.COMMUNITY_PROJECT)

    def test_a_blocked_project_still_reports_a_reason_per_open_competition(self):
        monthly = open_competition(entry_series="monthly")
        hackathon = open_competition(entry_series="summer-hackathon")
        standing = query.competition_standing(community_tipoff())

        assert_blocked_for(standing, monthly, IneligibleReason.COMMUNITY_PROJECT)
        assert_blocked_for(standing, hackathon, IneligibleReason.COMMUNITY_PROJECT)


@pytest.mark.django_db
class TestEntries:
    def test_entries_list_every_competition_the_project_is_in(self):
        project = published_project()
        june = CompetitionFactory(entry_series="monthly")
        hackathon = CompetitionFactory(entry_series="summer-hackathon")
        CompetitionEntryFactory(competition=june, project=project)
        CompetitionEntryFactory(competition=hackathon, project=project)

        standing = query.competition_standing(project)

        assert_that(
            [entry.competition.id for entry in standing.entries],
            contains_inanyorder(june.id, hackathon.id),
        )

    def test_entries_are_newest_first(self):
        project = published_project()
        older = CompetitionEntryFactory(project=project)
        newer = CompetitionEntryFactory(project=project)
        older.entered_at = older.entered_at.replace(year=2020)
        older.save(update_fields=["entered_at"])

        standing = query.competition_standing(project)

        assert_that(
            [entry.competition.id for entry in standing.entries],
            equal_to([newer.competition.id, older.competition.id]),
        )

    def test_an_entry_carries_how_it_came_about(self):
        project = published_project()
        entry = CompetitionEntryFactory(project=project)

        standing = query.competition_standing(project)

        assert_that(standing.entries[0].entered_via, equal_to(entry.entered_via))
        assert_that(standing.entries[0].entered_at, equal_to(entry.entered_at))

    def test_another_projects_entry_is_not_reported(self):
        competition = CompetitionFactory(entry_series="monthly")
        CompetitionEntryFactory(competition=competition, project=ProjectFactory())

        standing = query.competition_standing(published_project())

        assert_that(standing.entries, is_(empty()))


@pytest.mark.django_db
class TestStampingAList:
    def test_each_project_gets_its_own_standing(self):
        user = UserFactory()
        entered = published_project(owner=user)
        eligible = published_project(owner=user)
        competition = open_competition(entry_series="monthly")
        CompetitionEntryFactory(competition=competition, project=entered)

        stamped = {
            project.id: project._competition_standing  # noqa: SLF001
            for project in query.with_competition_standing(
                [entered, eligible],
            )
        }

        # The entered project holds the round; the other is offered it. Two
        # different answers from one pass, which is the point of stamping.
        assert_that(
            [entry.competition.id for entry in stamped[entered.id].entries],
            equal_to([competition.id]),
        )
        assert_that(stamped[entered.id].opportunities, is_(empty()))
        assert_eligible_for(stamped[eligible.id], competition)

    def test_stamping_does_not_issue_a_query_per_project(self):
        """The reason `with_competition_standing` exists rather than resolving
        the field per instance."""
        user = UserFactory()
        open_competition()
        one = [published_project(owner=user)]
        five = [published_project(owner=user) for _ in range(5)]

        with CaptureQueriesContext(connection) as for_one:
            query.with_competition_standing(one)

        with CaptureQueriesContext(connection) as for_five:
            query.with_competition_standing(five)

        assert_that(len(for_five), equal_to(len(for_one)))

    def test_stamping_an_empty_list_is_not_an_error(self):
        assert_that(query.with_competition_standing([]), equal_to([]))

    def test_an_unstamped_project_reports_no_standing(self):
        assert_that(
            getattr(published_project(), "_competition_standing", None), is_(none())
        )
