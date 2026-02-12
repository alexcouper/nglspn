import json

from hamcrest import (
    assert_that,
    equal_to,
    greater_than_or_equal_to,
    has_entries,
    has_item,
    has_length,
)

from api.auth.jwt import create_access_token
from apps.projects.models import ProjectStatus
from apps.tags.models import Tag, TagCategory, TagStatus
from tests.factories import (
    ProjectFactory,
    TagCategoryFactory,
    TagFactory,
    UserFactory,
)


class TestListTagsGrouped:
    def test_returns_tags_grouped_by_category(self, client, db) -> None:
        # Get a category from the existing ones (created by migrations)
        category = TagCategory.objects.first()
        # Create a new tag in that category
        new_tag = TagFactory(name="TestTag123", slug="test-tag-123", category=category)

        response = client.get("/api/tags/grouped")

        assert_that(response.status_code, equal_to(200))
        data = response.json()
        # Should have at least one category
        assert_that(len(data), greater_than_or_equal_to(1))
        # Find the category with our test tag
        category_data = next(
            (g for g in data if g["category"]["id"] == str(category.id)), None
        )
        assert category_data is not None
        tag_ids = [t["id"] for t in category_data["tags"]]
        assert_that(tag_ids, has_item(str(new_tag.id)))

    def test_excludes_rejected_tags(self, client, db) -> None:
        category = TagCategory.objects.first()
        approved_tag = TagFactory(
            name="ApprovedTag",
            slug="approved-tag",
            category=category,
            status=TagStatus.APPROVED,
        )
        TagFactory(
            name="RejectedTag",
            slug="rejected-tag",
            category=category,
            status=TagStatus.REJECTED,
        )

        response = client.get("/api/tags/grouped")

        assert_that(response.status_code, equal_to(200))
        data = response.json()
        # Find the category
        category_data = next(
            (g for g in data if g["category"]["id"] == str(category.id)), None
        )
        assert category_data is not None
        tag_ids = [t["id"] for t in category_data["tags"]]
        assert_that(tag_ids, has_item(str(approved_tag.id)))
        # Rejected tag should not be in the list
        rejected_tags = [
            t["id"] for t in category_data["tags"] if t["slug"] == "rejected-tag"
        ]
        assert_that(rejected_tags, has_length(0))

    def test_with_projects_filter_only_returns_tags_with_approved_projects(
        self, client, db
    ) -> None:
        # Clear existing tags to have a clean test
        Tag.objects.all().delete()
        category = TagCategory.objects.first()
        tag_with_project = TagFactory(
            name="TagWithProject", slug="tag-with-project", category=category
        )
        TagFactory(
            name="TagWithoutProject", slug="tag-without-project", category=category
        )
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        project.tags.add(tag_with_project)

        response = client.get("/api/tags/grouped?with_projects=true")

        assert_that(response.status_code, equal_to(200))
        data = response.json()
        # Should only return categories with tags that have projects
        assert_that(len(data), equal_to(1))
        assert_that(data[0]["tags"], has_length(1))
        assert_that(data[0]["tags"][0]["id"], equal_to(str(tag_with_project.id)))

    def test_empty_categories_are_hidden(self, client, db) -> None:
        # Clear existing tags
        Tag.objects.all().delete()
        # Create a new empty category
        empty_category = TagCategoryFactory(name="EmptyCat", slug="empty-cat")
        # Create a different category with tags
        category_with_tags = TagCategoryFactory(name="WithTags", slug="with-tags")
        TagFactory(name="TagForTest", slug="tag-for-test", category=category_with_tags)

        response = client.get("/api/tags/grouped")

        assert_that(response.status_code, equal_to(200))
        data = response.json()
        # Empty category should not be in the response
        category_ids = [g["category"]["id"] for g in data]
        assert str(empty_category.id) not in category_ids
        assert str(category_with_tags.id) in category_ids


class TestSuggestTag:
    def test_creates_pending_tag(self, client, auth_headers, db) -> None:
        category = TagCategoryFactory()
        payload = {"name": "New Tag", "category_id": str(category.id)}

        response = client.post(
            "/api/tags/suggest",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(201))
        data = response.json()
        assert_that(data["name"], equal_to("New Tag"))
        assert_that(data["slug"], equal_to("new-tag"))
        assert_that(data["status"], equal_to("pending"))
        assert_that(data["category_id"], equal_to(str(category.id)))

    def test_rejects_duplicate_name(self, client, auth_headers, db) -> None:
        category = TagCategoryFactory()
        TagFactory(name="Existing Tag", category=category)
        payload = {"name": "Existing Tag", "category_id": str(category.id)}

        response = client.post(
            "/api/tags/suggest",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))
        assert_that(
            response.json(),
            has_entries(detail="A tag with this name already exists"),
        )

    def test_requires_authentication(self, client, db) -> None:
        category = TagCategoryFactory()
        payload = {"name": "New Tag", "category_id": str(category.id)}

        response = client.post(
            "/api/tags/suggest",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(401))


class TestApproveTag:
    def test_approves_pending_tag(self, client, db) -> None:
        admin = UserFactory(is_staff=True)

        token = create_access_token(admin.id)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

        tag = TagFactory(status=TagStatus.PENDING)

        response = client.put(f"/api/tags/admin/{tag.id}/approve", **headers)

        assert_that(response.status_code, equal_to(200))
        data = response.json()
        assert_that(data["status"], equal_to("approved"))
        tag.refresh_from_db()
        assert_that(tag.status, equal_to(TagStatus.APPROVED))
        assert_that(tag.reviewed_by, equal_to(admin))

    def test_requires_staff_permission(self, client, auth_headers, db) -> None:
        tag = TagFactory(status=TagStatus.PENDING)

        response = client.put(f"/api/tags/admin/{tag.id}/approve", **auth_headers)

        assert_that(response.status_code, equal_to(403))
        assert_that(response.json(), has_entries(detail="Admin access required"))

    def test_cannot_approve_already_approved_tag(self, client, db) -> None:
        admin = UserFactory(is_staff=True)

        token = create_access_token(admin.id)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

        tag = TagFactory(status=TagStatus.APPROVED)

        response = client.put(f"/api/tags/admin/{tag.id}/approve", **headers)

        assert_that(response.status_code, equal_to(400))
        assert_that(response.json(), has_entries(detail="Tag is already approved"))


class TestRejectTag:
    def test_rejects_tag_and_removes_from_projects(self, client, db) -> None:
        admin = UserFactory(is_staff=True)

        token = create_access_token(admin.id)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

        tag = TagFactory(status=TagStatus.PENDING)
        project = ProjectFactory()
        project.tags.add(tag)

        response = client.put(f"/api/tags/admin/{tag.id}/reject", **headers)

        assert_that(response.status_code, equal_to(200))
        data = response.json()
        assert_that(data["status"], equal_to("rejected"))
        tag.refresh_from_db()
        assert_that(tag.status, equal_to(TagStatus.REJECTED))
        assert_that(project.tags.count(), equal_to(0))

    def test_requires_staff_permission(self, client, auth_headers, db) -> None:
        tag = TagFactory(status=TagStatus.PENDING)

        response = client.put(f"/api/tags/admin/{tag.id}/reject", **auth_headers)

        assert_that(response.status_code, equal_to(403))

    def test_cannot_reject_already_rejected_tag(self, client, db) -> None:
        admin = UserFactory(is_staff=True)

        token = create_access_token(admin.id)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

        tag = TagFactory(status=TagStatus.REJECTED)

        response = client.put(f"/api/tags/admin/{tag.id}/reject", **headers)

        assert_that(response.status_code, equal_to(400))
        assert_that(response.json(), has_entries(detail="Tag is already rejected"))


class TestListPendingTags:
    def test_returns_only_pending_tags(self, client, db) -> None:
        admin = UserFactory(is_staff=True)

        token = create_access_token(admin.id)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

        TagFactory(status=TagStatus.PENDING)
        TagFactory(status=TagStatus.PENDING)
        TagFactory(status=TagStatus.APPROVED)
        TagFactory(status=TagStatus.REJECTED)

        response = client.get("/api/tags/admin/pending", **headers)

        assert_that(response.status_code, equal_to(200))
        data = response.json()
        assert_that(data, has_length(2))

    def test_requires_staff_permission(self, client, auth_headers, db) -> None:
        response = client.get("/api/tags/admin/pending", **auth_headers)

        assert_that(response.status_code, equal_to(403))
