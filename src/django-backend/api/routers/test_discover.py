import pytest
from django.utils import timezone

from apps.projects.models import ProjectStatus
from services.project.django_impl.query import resolve_image_by_purpose
from tests.factories import (
    CompetitionFactory,
    DiscussionFactory,
    ProjectCategoryFactory,
    ProjectFactory,
    ProjectImageFactory,
)


@pytest.mark.django_db
class TestImagePurposeFallback:
    def test_returns_purpose_specific_image(self):
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        ProjectImageFactory(project=project, purpose="general")
        icon = ProjectImageFactory(project=project, purpose="icon")
        result = resolve_image_by_purpose(project, "icon")
        assert result.id == icon.id

    def test_falls_back_to_main_image(self):
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        main = ProjectImageFactory(project=project, purpose="general", is_main=True)
        result = resolve_image_by_purpose(project, "icon")
        assert result.id == main.id

    def test_falls_back_to_first_image(self):
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        first = ProjectImageFactory(project=project, purpose="general")
        result = resolve_image_by_purpose(project, "icon")
        assert result.id == first.id

    def test_returns_none_when_no_images(self):
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        result = resolve_image_by_purpose(project, "icon")
        assert result is None

    def test_returns_hero_image_by_boolean(self):
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        ProjectImageFactory(project=project)
        hero = ProjectImageFactory(project=project, is_hero=True)
        result = resolve_image_by_purpose(project, "hero_banner")
        assert result.id == hero.id

    def test_returns_usage_image_by_boolean(self):
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        ProjectImageFactory(project=project)
        usage = ProjectImageFactory(project=project, is_usage=True)
        result = resolve_image_by_purpose(project, "in_use")
        assert result.id == usage.id

    def test_hero_falls_back_to_main(self):
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        main = ProjectImageFactory(project=project, is_main=True)
        result = resolve_image_by_purpose(project, "hero_banner")
        assert result.id == main.id


@pytest.mark.django_db
class TestListCategories:
    def test_returns_categories_with_project_count(self, client):
        cat = ProjectCategoryFactory(name="Dev Tools", slug="dev-tools")
        ProjectFactory(status=ProjectStatus.APPROVED, category=cat)
        ProjectFactory(status=ProjectStatus.APPROVED, category=cat)
        ProjectFactory(status=ProjectStatus.PENDING, category=cat)

        response = client.get("/api/projects/categories")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Dev Tools"
        assert data[0]["project_count"] == 2

    def test_returns_empty_list_when_no_categories(self, client):
        response = client.get("/api/projects/categories")
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.django_db
class TestListFeatured:
    def test_returns_featured_projects(self, client):
        ProjectFactory(status=ProjectStatus.APPROVED, is_featured=True)
        ProjectFactory(status=ProjectStatus.APPROVED, is_featured=False)

        response = client.get("/api/projects/featured")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_returns_empty_when_none_featured(self, client):
        ProjectFactory(status=ProjectStatus.APPROVED)
        response = client.get("/api/projects/featured")
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.django_db
class TestListNewArrivals:
    def test_returns_recently_approved_projects(self, client):
        ProjectFactory(
            status=ProjectStatus.APPROVED,
            approved_at=timezone.now(),
        )

        response = client.get("/api/projects/new-arrivals")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_includes_projects_with_null_approved_at_using_created_at(self, client):
        old = ProjectFactory(
            status=ProjectStatus.APPROVED,
            approved_at=None,
            created_at=timezone.now() - timezone.timedelta(days=10),
        )
        new = ProjectFactory(
            status=ProjectStatus.APPROVED,
            approved_at=None,
            created_at=timezone.now() - timezone.timedelta(days=1),
        )

        response = client.get("/api/projects/new-arrivals")

        assert response.status_code == 200
        data = response.json()
        titles = [p["title"] for p in data]
        assert new.title in titles
        assert old.title in titles
        assert titles.index(new.title) < titles.index(old.title)

    def test_falls_back_to_most_recent_when_few_recent(self, client):
        for _ in range(3):
            ProjectFactory(
                status=ProjectStatus.APPROVED,
                approved_at=timezone.now() - timezone.timedelta(days=60),
            )

        response = client.get("/api/projects/new-arrivals")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3


@pytest.mark.django_db
class TestListWinners:
    def test_returns_competition_winners(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        CompetitionFactory(winner=project, projects=[project])

        response = client.get("/api/projects/winners")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(project.id)
        assert "competition_name" in data[0]

    def test_returns_empty_when_no_winners(self, client):
        response = client.get("/api/projects/winners")
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.django_db
class TestListMostDiscussed:
    def test_returns_projects_with_discussions(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        DiscussionFactory(project=project)
        DiscussionFactory(project=project)

        response = client.get("/api/projects/most-discussed")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["discussion_count"] == 2

    def test_excludes_replies_from_count(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        discussion = DiscussionFactory(project=project)
        DiscussionFactory(project=project, parent=discussion)

        response = client.get("/api/projects/most-discussed")

        data = response.json()
        assert len(data) == 1
        assert data[0]["discussion_count"] == 1

    def test_returns_empty_when_no_discussions(self, client):
        ProjectFactory(status=ProjectStatus.APPROVED)
        response = client.get("/api/projects/most-discussed")
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.django_db
class TestListByCategory:
    def test_returns_projects_in_category(self, client):
        cat = ProjectCategoryFactory(slug="dev-tools")
        ProjectFactory(status=ProjectStatus.APPROVED, category=cat)
        ProjectFactory(status=ProjectStatus.APPROVED)

        response = client.get("/api/projects/by-category/dev-tools")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_returns_404_for_unknown_category(self, client):
        response = client.get("/api/projects/by-category/nonexistent")
        assert response.status_code == 404

    def test_sorts_by_name(self, client):
        cat = ProjectCategoryFactory(slug="tools")
        ProjectFactory(
            title="Zebra",
            status=ProjectStatus.APPROVED,
            category=cat,
        )
        ProjectFactory(
            title="Alpha",
            status=ProjectStatus.APPROVED,
            category=cat,
        )

        response = client.get("/api/projects/by-category/tools?sort=name")

        data = response.json()
        assert data[0]["title"] == "Alpha"
        assert data[1]["title"] == "Zebra"

    def test_sorts_by_most_discussed(self, client):
        cat = ProjectCategoryFactory(slug="tools")
        p1 = ProjectFactory(
            title="Few",
            status=ProjectStatus.APPROVED,
            category=cat,
        )
        p2 = ProjectFactory(
            title="Many",
            status=ProjectStatus.APPROVED,
            category=cat,
        )
        DiscussionFactory(project=p1)
        DiscussionFactory(project=p2)
        DiscussionFactory(project=p2)

        response = client.get("/api/projects/by-category/tools?sort=most-discussed")

        data = response.json()
        assert data[0]["title"] == "Many"
