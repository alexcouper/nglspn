"""The fake in test_api.py is only worth as much as its resemblance to the real
API. This drives the snapshot against a live server to keep the two honest."""

import pytest

from apps.projects.models import ProjectStatus
from scripts.taxonomy.api import fetch_snapshot
from tests.factories import ProjectCategoryFactory, ProjectFactory, TagFactory


def snapshot_from(live_server):
    return fetch_snapshot(f"{live_server.url}/api")


def rows_by_title(snapshot):
    return {row["title"]: row for row in snapshot["projects"]}


@pytest.mark.django_db(transaction=True)
def test_snapshot_reflects_what_the_live_api_serves(live_server):
    category = ProjectCategoryFactory(name="Dev Tools", slug="dev-tools")
    project = ProjectFactory(
        title="Grep",
        slug="grep",
        tagline="Finds things",
        description="A command line search tool.",
        status=ProjectStatus.APPROVED,
        category=category,
    )
    project.tags.add(TagFactory(name="cli"))
    ProjectFactory(title="Homeless", slug="homeless", status=ProjectStatus.APPROVED)
    ProjectFactory(title="Waiting", slug="waiting", status=ProjectStatus.PENDING)

    snapshot = snapshot_from(live_server)
    rows = rows_by_title(snapshot)

    assert set(rows) == {"Grep", "Homeless"}
    assert rows["Grep"]["current_category_slug"] == "dev-tools"
    assert rows["Grep"]["description"] == "A command line search tool."
    assert rows["Grep"]["tags"] == ["cli"]
    assert rows["Homeless"]["current_category_slug"] is None
    assert snapshot["current_categories"] == [
        {"slug": "dev-tools", "name": "Dev Tools", "project_count": 1},
        {"slug": None, "name": "(uncategorised)", "project_count": 1},
    ]


@pytest.mark.django_db(transaction=True)
def test_projects_without_a_slug_are_fetched_by_id(live_server):
    ProjectFactory(title="Sluggless", slug=None, status=ProjectStatus.APPROVED)

    assert "Sluggless" in rows_by_title(snapshot_from(live_server))
