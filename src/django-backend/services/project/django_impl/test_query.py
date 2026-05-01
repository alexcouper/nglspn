from uuid import uuid4

import pytest

from apps.projects.models import ContributorRole, ProjectContributor, ProjectStatus
from services.project.django_impl import DjangoProjectQuery, get_title_from_url
from services.project.exceptions import ProjectNotFoundError
from tests.factories import ProjectFactory, UserFactory

query = DjangoProjectQuery()


@pytest.mark.django_db
class TestGetById:
    def test_returns_existing_project(self):
        project = ProjectFactory()

        result = query.get_by_id(project.id)

        assert result.id == project.id
        assert result.title == project.title

    def test_raises_for_nonexistent_project(self):
        with pytest.raises(ProjectNotFoundError):
            query.get_by_id(uuid4())


@pytest.mark.django_db
class TestGetForOwner:
    def test_returns_project_owned_by_user(self):
        user = UserFactory()
        project = ProjectFactory(owner=user)

        result = query.get_for_owner(project.id, user.id)

        assert result.id == project.id

    def test_raises_when_not_owner(self):
        project = ProjectFactory()
        other_user = UserFactory()

        with pytest.raises(ProjectNotFoundError):
            query.get_for_owner(project.id, other_user.id)

    def test_returns_project_for_non_creator_full_edit_contributor(self):
        project = ProjectFactory()
        contributor = UserFactory()
        ProjectContributor.objects.create(
            project=project,
            user=contributor,
            role=ContributorRole.TIPSTER,
            full_edit=True,
        )

        result = query.get_for_owner(project.id, contributor.id)

        assert result.id == project.id

    def test_raises_for_contributor_without_full_edit(self):
        project = ProjectFactory()
        contributor = UserFactory()
        ProjectContributor.objects.create(
            project=project,
            user=contributor,
            role=ContributorRole.TIPSTER,
            full_edit=False,
        )

        with pytest.raises(ProjectNotFoundError):
            query.get_for_owner(project.id, contributor.id)


@pytest.mark.django_db
class TestUserCanEdit:
    def test_returns_false_for_none_user_id(self):
        project = ProjectFactory()

        assert query.user_can_edit(project.id, None) is False

    def test_returns_false_for_none_project_id(self):
        user = UserFactory()

        assert query.user_can_edit(None, user.id) is False

    def test_returns_false_for_user_without_contributor_row(self):
        project = ProjectFactory()
        unrelated = UserFactory()

        assert query.user_can_edit(project.id, unrelated.id) is False

    def test_returns_true_for_owner_contributor_with_full_edit(self):
        owner = UserFactory()
        project = ProjectFactory(owner=owner)

        assert query.user_can_edit(project.id, owner.id) is True

    def test_returns_false_when_full_edit_disabled(self):
        owner = UserFactory()
        project = ProjectFactory(owner=owner)
        ProjectContributor.objects.filter(project=project, user=owner).update(
            full_edit=False
        )

        assert query.user_can_edit(project.id, owner.id) is False

    def test_returns_true_for_tipster_with_full_edit(self):
        project = ProjectFactory()
        tipster = UserFactory()
        ProjectContributor.objects.create(
            project=project,
            user=tipster,
            role=ContributorRole.TIPSTER,
            full_edit=True,
        )

        assert query.user_can_edit(project.id, tipster.id) is True


@pytest.mark.django_db
class TestListApproved:
    def test_returns_only_approved_projects(self):
        ProjectFactory(status=ProjectStatus.APPROVED)
        ProjectFactory(status=ProjectStatus.PENDING)

        result = query.list_approved()

        assert result.total == 1

    def test_paginates_results(self):
        for _ in range(3):
            ProjectFactory(status=ProjectStatus.APPROVED)

        result = query.list_approved(per_page=2, page=1)

        assert len(result.projects) == 2
        assert result.total == 3
        assert result.pages == 2


@pytest.mark.django_db
class TestListForOwner:
    def test_returns_all_projects_for_owner(self):
        user = UserFactory()
        ProjectFactory(owner=user)
        ProjectFactory(owner=user)
        ProjectFactory()  # different owner

        result = query.list_for_owner(user.id)

        assert result.count() == 2

    def test_excludes_projects_where_user_is_only_a_tipster(self):
        # `list_for_owner` is creator-scoped; TIPSTER-only projects belong
        # in `list_tip_offs_for`.
        contributor = UserFactory()
        project = ProjectFactory()
        ProjectContributor.objects.create(
            project=project,
            user=contributor,
            role=ContributorRole.TIPSTER,
            full_edit=True,
        )

        result = query.list_for_owner(contributor.id)

        assert result.count() == 0

    def test_excludes_tipoff_projects_where_user_is_creator(self):
        # Community tip-offs: the tipster is the creator, but the OWNER
        # contributor is the seed system user. They belong in /tip-offs only.
        user = UserFactory()
        system_user = UserFactory(is_system_user=True)
        project = ProjectFactory(creator=user, _contributor=False)
        ProjectContributor.objects.create(
            project=project,
            user=system_user,
            role=ContributorRole.OWNER,
            full_edit=True,
        )
        ProjectContributor.objects.create(
            project=project,
            user=user,
            role=ContributorRole.TIPSTER,
            full_edit=True,
        )

        result = query.list_for_owner(user.id)

        assert result.count() == 0


@pytest.mark.django_db
class TestCountPending:
    def test_counts_pending_projects(self):
        ProjectFactory(status=ProjectStatus.PENDING)
        ProjectFactory(status=ProjectStatus.PENDING)
        ProjectFactory(status=ProjectStatus.APPROVED)

        assert query.count_pending() == 2


class TestGetTitleFromUrl:
    def test_extracts_domain_from_url(self):
        assert get_title_from_url("https://www.example.com/path") == "example.com"
        assert (
            get_title_from_url("http://subdomain.example.com")
            == "subdomain.example.com"
        )
        assert get_title_from_url("https://example.com") == "example.com"
        assert get_title_from_url("example.com/path") == "example.com"
        assert get_title_from_url("www.example.com") == "example.com"
        assert get_title_from_url("") == "Untitled Project"

    def test_special_handling_for_github_projects(self):
        assert get_title_from_url("https://github.com/x/y") == "y"
