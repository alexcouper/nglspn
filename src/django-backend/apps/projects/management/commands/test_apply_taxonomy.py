import json
from io import StringIO
from uuid import uuid4

import pytest
from django.core.management import CommandError, call_command
from hamcrest import (
    assert_that,
    contains_string,
    empty,
    equal_to,
    is_,
    is_not,
    not_none,
)

from apps.projects.models import Project, ProjectCategory, ProjectStatus
from tests.factories import ProjectCategoryFactory, ProjectFactory, UserFactory


def a_report(*, categories, projects, unplaced=None):
    """A taxonomy report in the shape `scripts.taxonomy` writes."""
    return {
        "generated_at": "2026-08-21",
        "source": {"api_url": "https://api.naglasupan.is/api"},
        "current_categories": [],
        "proposed_taxonomy": [
            {
                "slug": slug,
                "name": name,
                "status": "new",
                "replaces": [],
                "rationale": "…",
                "future_example": "…",
            }
            for slug, name in categories
        ],
        "projects": projects,
        "unplaced": unplaced or [],
        "observations": [],
    }


def a_placement(project, *, into, was=None, subcategory=None):
    return {
        "id": str(project.id),
        "slug": project.slug,
        "title": project.title,
        "current_category_slug": was,
        "proposed_category_slug": into,
        "proposed_subcategory_slug": subcategory,
        "alternative_category_slug": None,
        "confidence": "high",
        "rationale": "…",
    }


def report_file(tmp_path, report):
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return str(path)


def run_apply(tmp_path, report, *args):
    buffer = StringIO()
    call_command("apply_taxonomy", report_file(tmp_path, report), *args, stdout=buffer)
    return buffer.getvalue()


def an_approved_project(**kwargs):
    kwargs.setdefault("owner", UserFactory())
    return ProjectFactory(status=ProjectStatus.APPROVED, **kwargs)


def category_slug_of(project):
    project.refresh_from_db()
    return project.category.slug if project.category else None


@pytest.mark.django_db
def test_creates_every_category_the_report_defines(tmp_path):
    report = a_report(
        categories=[
            ("games-puzzles", "Games & Puzzles"),
            ("cost-of-living", "Cost of Living"),
        ],
        projects=[],
    )

    run_apply(tmp_path, report)

    created = ProjectCategory.objects.order_by("display_order")
    assert_that(
        [c.slug for c in created], is_(equal_to(["games-puzzles", "cost-of-living"]))
    )
    assert_that(
        [c.name for c in created], is_(equal_to(["Games & Puzzles", "Cost of Living"]))
    )


@pytest.mark.django_db
def test_orders_categories_by_their_position_in_the_report(tmp_path):
    report = a_report(
        categories=[("first", "First"), ("second", "Second"), ("third", "Third")],
        projects=[],
    )

    run_apply(tmp_path, report)

    orders = {c.slug: c.display_order for c in ProjectCategory.objects.all()}
    assert_that(orders, is_(equal_to({"first": 1, "second": 2, "third": 3})))


@pytest.mark.django_db
def test_assigns_each_project_to_its_proposed_category(tmp_path):
    old = ProjectCategoryFactory(slug="apps-services", name="Apps & Services")
    project = an_approved_project(category=old)
    report = a_report(
        categories=[("games-puzzles", "Games & Puzzles")],
        projects=[a_placement(project, into="games-puzzles", was="apps-services")],
    )

    run_apply(tmp_path, report)

    assert_that(category_slug_of(project), is_(equal_to("games-puzzles")))


@pytest.mark.django_db
def test_reuses_an_existing_category_row_and_updates_its_name(tmp_path):
    existing = ProjectCategoryFactory(slug="developer-tools", name="Dev Tools")
    report = a_report(categories=[("developer-tools", "Developer Tools")], projects=[])

    run_apply(tmp_path, report)

    existing.refresh_from_db()
    assert_that(existing.name, is_(equal_to("Developer Tools")))
    assert_that(ProjectCategory.objects.count(), is_(equal_to(1)))


@pytest.mark.django_db
def test_leaves_a_retired_category_row_in_place(tmp_path):
    retired = ProjectCategoryFactory(slug="apps-services", name="Apps & Services")
    moved = an_approved_project(category=retired)
    report = a_report(
        categories=[("games-puzzles", "Games & Puzzles")],
        projects=[a_placement(moved, into="games-puzzles", was="apps-services")],
    )

    run_apply(tmp_path, report)

    assert_that(
        ProjectCategory.objects.filter(slug="apps-services").first(), is_(not_none())
    )
    assert_that(category_slug_of(moved), is_(equal_to("games-puzzles")))


@pytest.mark.django_db
def test_leaves_an_unapproved_project_pointing_at_a_retired_category(tmp_path):
    retired = ProjectCategoryFactory(slug="apps-services", name="Apps & Services")
    draft = ProjectFactory(
        status=ProjectStatus.DRAFT, category=retired, owner=UserFactory()
    )
    report = a_report(categories=[("games-puzzles", "Games & Puzzles")], projects=[])

    run_apply(tmp_path, report)

    assert_that(category_slug_of(draft), is_(equal_to("apps-services")))


@pytest.mark.django_db
def test_reports_a_retired_category_that_still_holds_projects(tmp_path):
    retired = ProjectCategoryFactory(slug="apps-services", name="Apps & Services")
    ProjectFactory(status=ProjectStatus.DRAFT, category=retired, owner=UserFactory())
    report = a_report(categories=[("games-puzzles", "Games & Puzzles")], projects=[])

    output = run_apply(tmp_path, report)

    assert_that(output, contains_string("apps-services"))
    assert_that(output, contains_string("still holds 1"))


@pytest.mark.django_db
def test_dry_run_writes_nothing(tmp_path):
    old = ProjectCategoryFactory(slug="apps-services", name="Apps & Services")
    project = an_approved_project(category=old)
    report = a_report(
        categories=[("games-puzzles", "Games & Puzzles")],
        projects=[a_placement(project, into="games-puzzles", was="apps-services")],
    )

    output = run_apply(tmp_path, report, "--dry-run")

    assert_that(category_slug_of(project), is_(equal_to("apps-services")))
    assert_that(ProjectCategory.objects.filter(slug="games-puzzles"), is_(empty()))
    assert_that(output, contains_string("Dry run"))


@pytest.mark.django_db
def test_aborts_when_the_report_names_a_project_that_is_not_in_the_database(tmp_path):
    report = a_report(
        categories=[("games-puzzles", "Games & Puzzles")],
        projects=[
            {
                "id": str(uuid4()),
                "slug": "ghost",
                "title": "Ghost",
                "current_category_slug": None,
                "proposed_category_slug": "games-puzzles",
                "proposed_subcategory_slug": None,
                "alternative_category_slug": None,
                "confidence": "high",
                "rationale": "…",
            }
        ],
    )

    with pytest.raises(CommandError, match="not in the database"):
        run_apply(tmp_path, report)

    assert_that(ProjectCategory.objects.filter(slug="games-puzzles"), is_(empty()))


@pytest.mark.django_db
def test_aborts_when_a_project_is_placed_in_an_undefined_category(tmp_path):
    project = an_approved_project()
    report = a_report(
        categories=[("games-puzzles", "Games & Puzzles")],
        projects=[a_placement(project, into="food-drink")],
    )

    with pytest.raises(CommandError, match="food-drink"):
        run_apply(tmp_path, report)

    assert_that(ProjectCategory.objects.filter(slug="games-puzzles"), is_(empty()))


@pytest.mark.django_db
def test_leaves_an_unplaced_project_where_it_is(tmp_path):
    old = ProjectCategoryFactory(slug="apps-services", name="Apps & Services")
    project = an_approved_project(category=old)
    report = a_report(
        categories=[("games-puzzles", "Games & Puzzles")],
        projects=[a_placement(project, into=None, was="apps-services")],
        unplaced=[{"id": str(project.id), "reason": "Description is empty."}],
    )

    run_apply(tmp_path, report)

    assert_that(category_slug_of(project), is_(equal_to("apps-services")))


@pytest.mark.django_db
def test_warns_when_the_report_disagrees_about_a_projects_current_category(tmp_path):
    ProjectCategoryFactory(slug="developer-tools", name="Developer Tools")
    actual = ProjectCategoryFactory(slug="productivity-business", name="Productivity")
    project = an_approved_project(category=actual)
    report = a_report(
        categories=[("games-puzzles", "Games & Puzzles")],
        projects=[a_placement(project, into="games-puzzles", was="developer-tools")],
    )

    output = run_apply(tmp_path, report)

    assert_that(output, contains_string("stale"))
    assert_that(category_slug_of(project), is_(equal_to("games-puzzles")))


@pytest.mark.django_db
def test_reports_subcategory_placements_as_not_applied(tmp_path):
    project = an_approved_project()
    report = a_report(
        categories=[("family-wellbeing", "Family & Wellbeing")],
        projects=[
            a_placement(project, into="family-wellbeing", subcategory="kids-parenting")
        ],
    )

    output = run_apply(tmp_path, report)

    assert_that(output, contains_string("subcategory"))
    assert_that(category_slug_of(project), is_(equal_to("family-wellbeing")))


@pytest.mark.django_db
def test_a_second_run_moves_nothing(tmp_path):
    project = an_approved_project()
    report = a_report(
        categories=[("games-puzzles", "Games & Puzzles")],
        projects=[a_placement(project, into="games-puzzles")],
    )
    run_apply(tmp_path, report)

    output = run_apply(tmp_path, report)

    assert_that(output, contains_string("0 moved"))
    assert_that(Project.objects.filter(category__isnull=True), is_(empty()))
    assert_that(category_slug_of(project), is_(not_none()))


@pytest.mark.django_db
def test_does_not_call_a_project_stale_when_it_is_already_where_the_report_wants_it(
    tmp_path,
):
    target = ProjectCategoryFactory(slug="games-puzzles", name="Games & Puzzles")
    project = an_approved_project(category=target)
    report = a_report(
        categories=[("games-puzzles", "Games & Puzzles")],
        projects=[a_placement(project, into="games-puzzles", was="apps-services")],
    )

    output = run_apply(tmp_path, report)

    assert_that(output, is_not(contains_string("stale")))
