from uuid import uuid4

import pytest

from apps.tags.models import TagStatus
from services.tags.django_impl import DjangoTagHandler, DjangoTagQuery
from services.tags.exceptions import (
    DuplicateTagNameError,
    DuplicateTagSlugError,
    TagAlreadyApprovedError,
    TagAlreadyRejectedError,
    TagCategoryNotFoundError,
    TagNotFoundError,
    TagRejectedError,
)
from tests.factories import ProjectFactory, TagCategoryFactory, TagFactory, UserFactory

query = DjangoTagQuery()
handler = DjangoTagHandler()


@pytest.mark.django_db
class TestListNonRejected:
    def test_excludes_rejected_tags(self):
        rejected = TagFactory(status=TagStatus.REJECTED)
        result = query.list_non_rejected()
        assert rejected not in result

    def test_includes_approved_and_pending(self):
        approved = TagFactory(status=TagStatus.APPROVED)
        pending = TagFactory(status=TagStatus.PENDING)
        result = query.list_non_rejected()
        assert approved in result
        assert pending in result


@pytest.mark.django_db
class TestListCategories:
    def test_returns_active_categories(self):
        active = TagCategoryFactory(is_active=True)
        TagCategoryFactory(is_active=False)

        result = query.list_categories()
        assert active in result


@pytest.mark.django_db
class TestListGrouped:
    def test_returns_tags_grouped_by_category(self):
        category = TagCategoryFactory(is_active=True)
        TagFactory(status=TagStatus.APPROVED, category=category)

        result = query.list_grouped()

        matching = [g for g in result if g["category"]["id"] == category.id]
        assert len(matching) == 1
        assert len(matching[0]["tags"]) == 1


@pytest.mark.django_db
class TestListPending:
    def test_returns_only_pending_tags(self):
        pending = TagFactory(status=TagStatus.PENDING)
        TagFactory(status=TagStatus.APPROVED)

        result = query.list_pending()
        assert pending in result


@pytest.mark.django_db
class TestGetById:
    def test_returns_tag_by_id(self):
        tag = TagFactory()

        result = query.get_by_id(tag.id)

        assert result.id == tag.id

    def test_raises_for_nonexistent_id(self):
        with pytest.raises(TagNotFoundError):
            query.get_by_id(uuid4())


@pytest.mark.django_db
class TestSuggest:
    def test_creates_pending_tag(self):
        category = TagCategoryFactory(is_active=True)
        user = UserFactory()

        tag = handler.suggest(
            name="New Tag",
            slug="new-tag",
            description="A new tag",
            color="#FF5733",
            category_id=category.id,
            created_by_id=user.id,
        )

        assert tag.status == TagStatus.PENDING
        assert tag.name == "New Tag"

    def test_raises_for_inactive_category(self):
        category = TagCategoryFactory(is_active=False)
        user = UserFactory()

        with pytest.raises(TagCategoryNotFoundError):
            handler.suggest(
                name="New Tag",
                slug="new-tag",
                description=None,
                color=None,
                category_id=category.id,
                created_by_id=user.id,
            )

    def test_raises_for_duplicate_name(self):
        TagFactory(name="Existing")
        category = TagCategoryFactory(is_active=True)
        user = UserFactory()

        with pytest.raises(DuplicateTagNameError):
            handler.suggest(
                name="Existing",
                slug="different-slug",
                description=None,
                color=None,
                category_id=category.id,
                created_by_id=user.id,
            )

    def test_raises_for_duplicate_slug(self):
        TagFactory(slug="existing")
        category = TagCategoryFactory(is_active=True)
        user = UserFactory()

        with pytest.raises(DuplicateTagSlugError):
            handler.suggest(
                name="Different Name",
                slug="existing",
                description=None,
                color=None,
                category_id=category.id,
                created_by_id=user.id,
            )


@pytest.mark.django_db
class TestApprove:
    def test_approves_pending_tag(self):
        tag = TagFactory(status=TagStatus.PENDING)
        admin = UserFactory()

        result = handler.approve(tag.id, admin.id)

        assert result.status == TagStatus.APPROVED
        assert result.reviewed_by_id == admin.id

    def test_raises_for_already_approved(self):
        tag = TagFactory(status=TagStatus.APPROVED)
        admin = UserFactory()

        with pytest.raises(TagAlreadyApprovedError):
            handler.approve(tag.id, admin.id)

    def test_raises_for_rejected_tag(self):
        tag = TagFactory(status=TagStatus.REJECTED)
        admin = UserFactory()

        with pytest.raises(TagRejectedError):
            handler.approve(tag.id, admin.id)

    def test_raises_for_nonexistent_tag(self):
        admin = UserFactory()

        with pytest.raises(TagNotFoundError):
            handler.approve(uuid4(), admin.id)


@pytest.mark.django_db
class TestReject:
    def test_rejects_pending_tag(self):
        tag = TagFactory(status=TagStatus.PENDING)
        admin = UserFactory()

        result = handler.reject(tag.id, admin.id)

        assert result.status == TagStatus.REJECTED
        assert result.reviewed_by_id == admin.id

    def test_raises_for_already_rejected(self):
        tag = TagFactory(status=TagStatus.REJECTED)
        admin = UserFactory()

        with pytest.raises(TagAlreadyRejectedError):
            handler.reject(tag.id, admin.id)

    def test_removes_tag_from_projects(self):
        tag = TagFactory(status=TagStatus.PENDING)
        project = ProjectFactory()
        project.tags.add(tag)
        admin = UserFactory()

        handler.reject(tag.id, admin.id)

        project.refresh_from_db()
        assert tag not in project.tags.all()
