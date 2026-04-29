import pytest
from django.contrib.auth.models import AnonymousUser

from apps.projects.models import ContributorRole, ProjectContributor
from services.project.permissions import user_can_edit_project
from tests.factories import ProjectFactory, UserFactory


@pytest.mark.django_db
class TestUserCanEditProject:
    def test_returns_false_for_none(self):
        project = ProjectFactory()

        assert user_can_edit_project(project, None) is False

    def test_returns_false_for_anonymous_user(self):
        project = ProjectFactory()

        assert user_can_edit_project(project, AnonymousUser()) is False

    def test_returns_false_for_user_without_contributor_row(self):
        project = ProjectFactory()
        unrelated = UserFactory()

        assert user_can_edit_project(project, unrelated) is False

    def test_returns_true_for_owner_contributor_with_full_edit(self):
        owner = UserFactory()
        project = ProjectFactory(owner=owner)

        assert user_can_edit_project(project, owner) is True

    def test_returns_false_when_full_edit_disabled(self):
        owner = UserFactory()
        project = ProjectFactory(owner=owner)
        ProjectContributor.objects.filter(project=project, user=owner).update(
            full_edit=False
        )

        assert user_can_edit_project(project, owner) is False

    def test_returns_true_for_suggester_with_full_edit(self):
        project = ProjectFactory()
        suggester = UserFactory()
        ProjectContributor.objects.create(
            project=project,
            user=suggester,
            role=ContributorRole.SUGGESTER,
            full_edit=True,
        )

        assert user_can_edit_project(project, suggester) is True
