import pytest

from apps.projects.models import ContributorRole, Project, ProjectContributor
from tests.factories import ProjectFactory, UserFactory


def _system_user():
    return UserFactory(is_system_user=True, email="community@example.com")


def _refresh(project: Project) -> Project:
    return Project.objects.get(pk=project.pk)


@pytest.mark.django_db
class TestIsCommunityTipoffSignals:
    def test_self_owned_project_starts_false(self):
        project = ProjectFactory()
        assert _refresh(project).is_community_tipoff is False

    def test_adding_system_user_owner_flips_true(self):
        project = ProjectFactory()
        ProjectContributor.objects.create(
            project=project,
            user=_system_user(),
            role=ContributorRole.OWNER,
        )
        assert _refresh(project).is_community_tipoff is True

    def test_removing_system_user_owner_flips_false(self):
        project = ProjectFactory()
        contributor = ProjectContributor.objects.create(
            project=project,
            user=_system_user(),
            role=ContributorRole.OWNER,
        )
        assert _refresh(project).is_community_tipoff is True

        contributor.delete()
        assert _refresh(project).is_community_tipoff is False

    def test_non_owner_contributor_does_not_change_column(self):
        project = ProjectFactory()
        ProjectContributor.objects.create(
            project=project,
            user=_system_user(),
            role=ContributorRole.TIPSTER,
        )
        assert _refresh(project).is_community_tipoff is False

    def test_non_system_owner_does_not_set_column(self):
        project = ProjectFactory()
        ProjectContributor.objects.create(
            project=project,
            user=UserFactory(),
            role=ContributorRole.OWNER,
        )
        assert _refresh(project).is_community_tipoff is False

    def test_recompute_method_is_idempotent(self):
        project = ProjectFactory()
        ProjectContributor.objects.create(
            project=project,
            user=_system_user(),
            role=ContributorRole.OWNER,
        )
        before = _refresh(project)
        before.recompute_community_tipoff()
        before.recompute_community_tipoff()
        assert _refresh(project).is_community_tipoff is True
