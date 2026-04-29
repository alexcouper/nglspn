from importlib import import_module

import pytest
from django.apps import apps as django_apps

from apps.projects.models import ContributorRole, ProjectContributor
from tests.factories import ProjectFactory, UserFactory

migration_module = import_module("apps.projects.migrations.0038_projectcontributor")


@pytest.mark.django_db
class TestContributorBackfillMigration:
    def _run_forward(self):
        migration_module.backfill_owner_contributors(django_apps, schema_editor=None)

    def test_inserts_one_owner_contributor_per_existing_project(self):
        owner_a = UserFactory()
        owner_b = UserFactory()
        project_a = ProjectFactory(owner=owner_a)
        project_b = ProjectFactory(owner=owner_b)
        ProjectContributor.objects.all().delete()

        self._run_forward()

        assert ProjectContributor.objects.count() == 2
        for project, user in [(project_a, owner_a), (project_b, owner_b)]:
            row = ProjectContributor.objects.get(project=project, user=user)
            assert row.role == ContributorRole.OWNER
            assert row.full_edit is True

    def test_is_idempotent(self):
        owner = UserFactory()
        ProjectFactory(owner=owner)
        ProjectContributor.objects.all().delete()

        self._run_forward()
        self._run_forward()

        assert ProjectContributor.objects.count() == 1

    def test_does_not_overwrite_existing_rows(self):
        owner = UserFactory()
        project = ProjectFactory(owner=owner)
        ProjectContributor.objects.filter(project=project, user=owner).update(
            full_edit=False
        )

        self._run_forward()

        row = ProjectContributor.objects.get(project=project, user=owner)
        assert row.full_edit is False
