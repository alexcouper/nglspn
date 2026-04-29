import pytest

from apps.projects.models import ContributorRole, ProjectContributor
from tests.factories import ProjectFactory, UserFactory


@pytest.mark.django_db
class TestProjectFactoryOwnerAlias:
    def test_owner_kwarg_sets_creator(self):
        owner = UserFactory()

        project = ProjectFactory(owner=owner)

        assert project.creator_id == owner.id

    def test_owner_kwarg_creates_owner_full_edit_contributor(self):
        owner = UserFactory()

        project = ProjectFactory(owner=owner)

        contributor = ProjectContributor.objects.get(project=project, user=owner)
        assert contributor.role == ContributorRole.OWNER
        assert contributor.full_edit is True

    def test_default_creator_creates_owner_contributor(self):
        project = ProjectFactory()

        contributor = ProjectContributor.objects.get(
            project=project, user=project.creator
        )
        assert contributor.role == ContributorRole.OWNER
        assert contributor.full_edit is True

    def test_passing_both_creator_and_owner_raises(self):
        creator = UserFactory()
        owner = UserFactory()

        with pytest.raises(TypeError, match="creator= or owner="):
            ProjectFactory(creator=creator, owner=owner)
