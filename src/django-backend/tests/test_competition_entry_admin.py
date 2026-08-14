"""Entries are the only record of who is in a round, so staff need to see them
from both sides and provenance has to survive being written by hand."""

import pytest
from django.contrib import admin
from django.test import Client, RequestFactory

from apps.projects.models import (
    Competition,
    CompetitionEntry,
    EntrySource,
    Project,
)
from apps.users.models import User
from tests.factories import (
    CompetitionEntryFactory,
    CompetitionFactory,
    ProjectFactory,
    UserFactory,
)

ENTRY_CHANGELIST = "/admin/projects/competitionentry/"
ENTRY_ADD = "/admin/projects/competitionentry/add/"


@pytest.fixture
def staff_client(db) -> Client:
    client = Client()
    client.force_login(UserFactory(is_staff=True, is_superuser=True))
    return client


@pytest.fixture
def staff_user(db) -> User:
    return UserFactory(is_staff=True, is_superuser=True)


def listed_entry_ids(response) -> list[str]:
    return [str(entry.pk) for entry in response.context["cl"].result_list]


def save_entry_inline(
    competition: Competition,
    project: Project,
    by: User,
    existing: CompetitionEntry | None = None,
) -> None:
    """Put one row through the entry inline on the competition change form.

    Driven at the formset rather than through a POST to the change view: the
    change view wants every field of a Competition alongside, and none of that
    is what `save_formset` is being asked about.
    """
    request = RequestFactory().post("/admin/")
    request.user = by

    competition_admin = admin.site.get_model_admin(Competition)
    inline = next(
        candidate
        for candidate in competition_admin.get_inline_instances(request, competition)
        if candidate.model is CompetitionEntry
    )
    formset_class = inline.get_formset(request, competition)
    prefix = formset_class.get_default_prefix()

    formset = formset_class(
        {
            f"{prefix}-TOTAL_FORMS": "1",
            f"{prefix}-INITIAL_FORMS": "1" if existing else "0",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
            f"{prefix}-0-id": str(existing.pk) if existing else "",
            f"{prefix}-0-competition": str(competition.id),
            f"{prefix}-0-project": str(project.id),
        },
        instance=competition,
    )
    assert formset.is_valid(), formset.errors

    competition_admin.save_formset(request, form=None, formset=formset, change=True)


class TestEntryChangelist:
    def test_filtering_by_competition_shows_only_its_entries(
        self, staff_client
    ) -> None:
        wanted = CompetitionFactory(name="Mars keppni")
        other = CompetitionFactory(name="Sumar keppni")
        mine = CompetitionEntryFactory(competition=wanted)
        CompetitionEntryFactory(competition=other)

        response = staff_client.get(
            ENTRY_CHANGELIST, {"competition__id__exact": str(wanted.id)}
        )

        assert response.status_code == 200
        assert listed_entry_ids(response) == [str(mine.pk)]

    def test_filtering_by_series_shows_only_that_series(self, staff_client) -> None:
        monthly = CompetitionFactory(entry_series="monthly")
        one_off = CompetitionFactory(entry_series="sumar-2025")
        CompetitionEntryFactory(competition=monthly)
        theirs = CompetitionEntryFactory(competition=one_off)

        response = staff_client.get(
            ENTRY_CHANGELIST, {"competition__entry_series": "sumar-2025"}
        )

        assert response.status_code == 200
        assert listed_entry_ids(response) == [str(theirs.pk)]

    def test_searching_by_project_title_finds_its_entries(self, staff_client) -> None:
        project = ProjectFactory(title="Fluglest")
        entries = [
            CompetitionEntryFactory(project=project, competition=CompetitionFactory()),
            CompetitionEntryFactory(project=project, competition=CompetitionFactory()),
        ]
        CompetitionEntryFactory(project=ProjectFactory(title="Bokasafn"))

        response = staff_client.get(ENTRY_CHANGELIST, {"q": "Fluglest"})

        assert response.status_code == 200
        assert sorted(listed_entry_ids(response)) == sorted(
            str(entry.pk) for entry in entries
        )

    def test_searching_by_competition_name_finds_its_entries(
        self, staff_client
    ) -> None:
        competition = CompetitionFactory(name="Mars keppni 2025")
        entry = CompetitionEntryFactory(competition=competition)
        CompetitionEntryFactory(competition=CompetitionFactory(name="Sumar keppni"))

        response = staff_client.get(ENTRY_CHANGELIST, {"q": "Mars keppni"})

        assert response.status_code == 200
        assert listed_entry_ids(response) == [str(entry.pk)]


class TestEntryProvenance:
    def test_adding_an_entry_records_admin_and_the_acting_user(
        self, staff_client
    ) -> None:
        competition = CompetitionFactory()
        project = ProjectFactory()

        response = staff_client.post(
            ENTRY_ADD,
            {"competition": str(competition.id), "project": str(project.id)},
        )

        assert response.status_code == 302, response.context["errors"]
        entry = CompetitionEntry.objects.get(competition=competition, project=project)
        assert entry.entered_via == EntrySource.ADMIN
        assert entry.entered_by == response.wsgi_request.user

    def test_provenance_is_not_offered_as_an_editable_field(self, staff_client) -> None:
        """Provenance that can be typed cannot be trusted."""
        response = staff_client.get(ENTRY_ADD)

        assert response.status_code == 200
        fields = response.context["adminform"].form.fields
        assert "entered_via" not in fields
        assert "entered_by" not in fields

    def test_a_posted_provenance_is_ignored(self, staff_client) -> None:
        competition = CompetitionFactory()
        project = ProjectFactory()

        staff_client.post(
            ENTRY_ADD,
            {
                "competition": str(competition.id),
                "project": str(project.id),
                "entered_via": EntrySource.MANUAL,
            },
        )

        entry = CompetitionEntry.objects.get(competition=competition, project=project)
        assert entry.entered_via == EntrySource.ADMIN

    def test_the_competition_inline_still_offers_no_provenance_fields(self) -> None:
        competition_admin = admin.site.get_model_admin(Competition)
        inline = next(
            candidate
            for candidate in competition_admin.inlines
            if candidate.model is CompetitionEntry
        )

        assert set(inline.readonly_fields) >= {"entered_via", "entered_by"}

    def test_the_competition_inline_stamps_provenance_on_a_new_entry(
        self, staff_user
    ) -> None:
        """The fields being readonly is why this is needed, not a substitute
        for it: readonly means the row arrives with `entered_via` blank, which
        the database accepts. `save_formset` is the only thing filling it in."""
        competition = CompetitionFactory()
        project = ProjectFactory()

        save_entry_inline(competition, project, by=staff_user)

        entry = CompetitionEntry.objects.get()
        assert entry.competition == competition
        assert entry.project == project
        assert entry.entered_via == EntrySource.ADMIN
        assert entry.entered_by == staff_user

    def test_the_competition_inline_leaves_an_existing_entry_alone(
        self, staff_user
    ) -> None:
        """Re-saving the competition must not rewrite who entered a project."""
        entered_by = UserFactory()
        entry = CompetitionEntryFactory(
            entered_via=EntrySource.MANUAL, entered_by=entered_by
        )

        save_entry_inline(
            entry.competition, entry.project, by=staff_user, existing=entry
        )

        entry.refresh_from_db()
        assert entry.entered_via == EntrySource.MANUAL
        assert entry.entered_by == entered_by


class TestEntryRemoval:
    def test_deleting_an_entry_takes_the_project_out_of_the_competition(
        self, staff_client
    ) -> None:
        entry = CompetitionEntryFactory()
        competition = entry.competition
        project = entry.project

        response = staff_client.post(
            f"/admin/projects/competitionentry/{entry.pk}/delete/", {"post": "yes"}
        )

        assert response.status_code == 302
        assert project not in competition.projects.all()


class TestEntriesOnTheProjectForm:
    def test_the_project_form_lists_its_competitions(self, staff_client) -> None:
        project = ProjectFactory()
        competition = CompetitionFactory(name="Mars keppni 2025")
        CompetitionEntryFactory(project=project, competition=competition)

        response = staff_client.get(f"/admin/projects/project/{project.id}/change/")

        assert response.status_code == 200
        assert "Mars keppni 2025" in response.content.decode()

    def test_the_project_form_does_not_offer_to_edit_entries(self, db) -> None:
        project_admin = admin.site.get_model_admin(Project)
        inline_class = next(
            candidate
            for candidate in project_admin.inlines
            if candidate.model is CompetitionEntry
        )
        request = RequestFactory().get("/admin/")
        request.user = UserFactory(is_staff=True, is_superuser=True)

        inline = inline_class(Project, admin.site)

        assert inline.has_add_permission(request, None) is False
        assert inline.can_delete is False
