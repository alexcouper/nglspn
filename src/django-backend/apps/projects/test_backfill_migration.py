from datetime import timedelta
from importlib import import_module

import pytest
from django.apps import apps as django_apps
from django.utils import timezone

from apps.projects.models import ProjectStatus
from tests.factories import ProjectFactory

migration_module = import_module(
    "apps.projects.migrations.0037_backfill_slug_and_published_at"
)


@pytest.mark.django_db
class TestBackfillMigration:
    def _run_forward(self):
        migration_module.backfill(django_apps, schema_editor=None)

    def test_backfills_slug_and_published_at_for_approved(self):
        approved_at = timezone.now() - timedelta(days=3)
        project = ProjectFactory(
            title="Already Approved",
            status=ProjectStatus.APPROVED,
            approved_at=approved_at,
            slug=None,
            published_at=None,
        )

        self._run_forward()

        project.refresh_from_db()
        assert project.slug == "already-approved"
        assert project.published_at == approved_at

    def test_falls_back_to_created_at_when_no_approved_at(self):
        project = ProjectFactory(
            title="Pending Thing",
            status=ProjectStatus.PENDING,
            approved_at=None,
            slug=None,
            published_at=None,
        )

        self._run_forward()

        project.refresh_from_db()
        assert project.slug == "pending-thing"
        assert project.published_at == project.created_at

    def test_generates_unique_slugs_on_collision(self):
        p1 = ProjectFactory(
            title="Duplicate",
            status=ProjectStatus.APPROVED,
            slug=None,
            published_at=None,
        )
        p2 = ProjectFactory(
            title="Duplicate",
            status=ProjectStatus.REJECTED,
            slug=None,
            published_at=None,
        )
        p3 = ProjectFactory(
            title="Duplicate",
            status=ProjectStatus.ICE_BOX,
            slug=None,
            published_at=None,
        )

        self._run_forward()

        for project in (p1, p2, p3):
            project.refresh_from_db()
        slugs = {p1.slug, p2.slug, p3.slug}
        assert slugs == {"duplicate", "duplicate-2", "duplicate-3"}

    def test_handles_icelandic_titles(self):
        project = ProjectFactory(
            title="Súperþing",
            status=ProjectStatus.APPROVED,
            slug=None,
            published_at=None,
        )

        self._run_forward()

        project.refresh_from_db()
        assert project.slug == "superthing"

    def test_skips_drafts(self):
        project = ProjectFactory(
            title="Draft Thing",
            status=ProjectStatus.DRAFT,
            slug=None,
            published_at=None,
        )

        self._run_forward()

        project.refresh_from_db()
        assert project.slug is None
        assert project.published_at is None

    def test_leaves_already_slugged_projects_alone(self):
        project = ProjectFactory(
            title="Keeps Slug",
            status=ProjectStatus.APPROVED,
            slug="keeps-slug",
            published_at=None,
        )

        self._run_forward()

        project.refresh_from_db()
        assert project.slug == "keeps-slug"

    def test_respects_existing_slugs_when_picking_suffix(self):
        ProjectFactory(
            title="Pinned",
            status=ProjectStatus.APPROVED,
            slug="pinned",
            published_at=timezone.now(),
        )
        new_one = ProjectFactory(
            title="Pinned",
            status=ProjectStatus.APPROVED,
            slug=None,
            published_at=None,
        )

        self._run_forward()

        new_one.refresh_from_db()
        assert new_one.slug == "pinned-2"
