"""The backfill in `0049_backfill_competition_entries` runs once, against live
data, and its output is the entry history for every competition ever run. These
tests drive the real migration rather than a copy of its logic."""

from datetime import UTC, date, datetime

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from hamcrest import assert_that, equal_to, is_not, none

BEFORE_BACKFILL = ("projects", "0048_competitionentry")
AFTER_BACKFILL = ("projects", "0049_backfill_competition_entries")


def _migrate(target):
    """Move the `projects` app to `target` and return the historical models.

    Every other app stays at its leaf: targeting `projects` alone would rewind
    `users` to whatever `projects` depends on, and the historical `User` model
    would no longer match the table.
    """
    app_label, _ = target
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    targets = [
        leaf for leaf in executor.loader.graph.leaf_nodes() if leaf[0] != app_label
    ]
    targets.append(target)

    executor.migrate(targets)
    executor.loader.build_graph()
    return executor.loader.project_state(targets).apps


@pytest.fixture
def at_migration():
    """Rewind the schema for a test, and put it back afterwards.

    Without the restore every later test in the session would run against a
    half-migrated database.
    """
    yield _migrate

    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())


def _make_user(apps, email):
    User = apps.get_model("users", "User")
    return User.objects.create(email=email, is_active=True)


def _make_project(apps, creator, title, published_at=None):
    Project = apps.get_model("projects", "Project")
    return Project.objects.create(
        website_url=f"https://{title.lower()}.test",
        title=title,
        creator=creator,
        published_at=published_at,
    )


def _make_competition(apps, name, start_date):
    Competition = apps.get_model("projects", "Competition")
    return Competition.objects.create(
        name=name,
        slug=name.lower(),
        start_date=start_date,
        submission_deadline=start_date,
    )


@pytest.mark.django_db(transaction=True)
def test_backfill_creates_one_entry_per_existing_membership(at_migration):
    old_apps = at_migration(BEFORE_BACKFILL)
    creator = _make_user(old_apps, "backfill-count@example.com")
    competition = _make_competition(old_apps, "June", date(2026, 6, 1))
    competition.projects.add(
        _make_project(old_apps, creator, "Alpha"),
        _make_project(old_apps, creator, "Beta"),
    )

    new_apps = at_migration(AFTER_BACKFILL)
    CompetitionEntry = new_apps.get_model("projects", "CompetitionEntry")

    assert_that(CompetitionEntry.objects.count(), equal_to(2))
    assert_that(
        set(CompetitionEntry.objects.values_list("entered_via", flat=True)),
        equal_to({"backfill"}),
    )


@pytest.mark.django_db(transaction=True)
def test_backfill_dates_an_entry_from_the_project_publish_time(at_migration):
    old_apps = at_migration(BEFORE_BACKFILL)
    published_at = datetime(2026, 6, 4, 9, 30, tzinfo=UTC)
    creator = _make_user(old_apps, "backfill-published@example.com")
    competition = _make_competition(old_apps, "June", date(2026, 6, 1))
    competition.projects.add(
        _make_project(old_apps, creator, "Alpha", published_at=published_at)
    )

    new_apps = at_migration(AFTER_BACKFILL)
    entry = new_apps.get_model("projects", "CompetitionEntry").objects.get()

    assert_that(entry.entered_at, equal_to(published_at))


@pytest.mark.django_db(transaction=True)
def test_backfill_falls_back_to_the_competition_start_for_an_unpublished_project(
    at_migration,
):
    old_apps = at_migration(BEFORE_BACKFILL)
    creator = _make_user(old_apps, "backfill-unpublished@example.com")
    competition = _make_competition(old_apps, "June", date(2026, 6, 1))
    competition.projects.add(
        _make_project(old_apps, creator, "Alpha", published_at=None)
    )

    new_apps = at_migration(AFTER_BACKFILL)
    entry = new_apps.get_model("projects", "CompetitionEntry").objects.get()

    assert_that(entry.entered_at.date(), equal_to(date(2026, 6, 1)))


@pytest.mark.django_db(transaction=True)
def test_backfill_leaves_the_entering_user_unknown(at_migration):
    old_apps = at_migration(BEFORE_BACKFILL)
    creator = _make_user(old_apps, "backfill-user@example.com")
    competition = _make_competition(old_apps, "June", date(2026, 6, 1))
    competition.projects.add(_make_project(old_apps, creator, "Alpha"))

    new_apps = at_migration(AFTER_BACKFILL)
    entry = new_apps.get_model("projects", "CompetitionEntry").objects.get()

    assert_that(entry.entered_by, none())


@pytest.mark.django_db(transaction=True)
def test_every_pre_existing_competition_joins_the_monthly_series(at_migration):
    old_apps = at_migration(("projects", "0046_orphanedstorageobject"))
    Competition = old_apps.get_model("projects", "Competition")
    Competition.objects.create(
        name="June",
        slug="june",
        start_date=date(2026, 6, 1),
        submission_deadline=date(2026, 6, 30),
    )

    new_apps = at_migration(AFTER_BACKFILL)
    migrated = new_apps.get_model("projects", "Competition").objects.get()

    assert_that(migrated.entry_series, equal_to("monthly"))


@pytest.mark.django_db(transaction=True)
def test_rolling_back_returns_memberships_to_the_join_table(at_migration):
    """The rollback path design.md offers: entries go back where they came
    from rather than being dropped with the table."""
    leaf_apps = at_migration(("projects", "0050_competition_projects_through"))
    CompetitionEntry = leaf_apps.get_model("projects", "CompetitionEntry")
    creator = _make_user(leaf_apps, "rollback@example.com")
    CompetitionEntry.objects.create(
        competition=_make_competition(leaf_apps, "June", date(2026, 6, 1)),
        project=_make_project(leaf_apps, creator, "Alpha"),
        entered_via="manual",
    )

    old_apps = at_migration(BEFORE_BACKFILL)
    competition = old_apps.get_model("projects", "Competition").objects.get()

    assert_that(competition.projects.count(), equal_to(1))
    assert_that(competition.projects.first(), is_not(none()))
