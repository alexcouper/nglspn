from uuid import uuid4

import pytest

from apps.tags.models import Tag, TagStatus
from services.tags.django_impl import DjangoTagHandler
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

handler = DjangoTagHandler()


@pytest.mark.django_db
class TestSuggest:
    def test_creates_pending_tag(self):
        user = UserFactory()
        category = TagCategoryFactory()

        tag = handler.suggest(
            name="New Tag",
            description="desc",
            color=None,
            category_id=category.id,
            created_by=user,
        )

        assert tag.status == TagStatus.PENDING
        assert tag.created_by == user
        assert tag.category_id == category.id

    def test_raises_on_duplicate_name(self):
        user = UserFactory()
        category = TagCategoryFactory()
        TagFactory(name="dup")

        with pytest.raises(DuplicateTagNameError):
            handler.suggest(
                name="dup",
                description=None,
                color=None,
                category_id=category.id,
                created_by=user,
            )

    def test_raises_on_duplicate_slug(self):
        user = UserFactory()
        category = TagCategoryFactory()
        TagFactory(name="Dup Tag", slug="dup-tag")

        with pytest.raises((DuplicateTagSlugError, DuplicateTagNameError)):
            handler.suggest(
                name="dup-tag",
                description=None,
                color=None,
                category_id=category.id,
                created_by=user,
            )

    def test_raises_on_missing_category(self):
        user = UserFactory()
        with pytest.raises(TagCategoryNotFoundError):
            handler.suggest(
                name="New",
                description=None,
                color=None,
                category_id=uuid4(),
                created_by=user,
            )

    def test_raises_on_inactive_category(self):
        user = UserFactory()
        category = TagCategoryFactory(is_active=False)
        with pytest.raises(TagCategoryNotFoundError):
            handler.suggest(
                name="New",
                description=None,
                color=None,
                category_id=category.id,
                created_by=user,
            )


@pytest.mark.django_db
class TestApprove:
    def test_approves_pending_tag(self):
        user = UserFactory(is_staff=True)
        tag = TagFactory(status=TagStatus.PENDING)

        result = handler.approve(tag.id, user)

        assert result.status == TagStatus.APPROVED
        assert result.reviewed_by == user
        assert result.reviewed_at is not None

    def test_raises_when_missing(self):
        user = UserFactory(is_staff=True)
        with pytest.raises(TagNotFoundError):
            handler.approve(uuid4(), user)

    def test_raises_when_already_approved(self):
        user = UserFactory(is_staff=True)
        tag = TagFactory(status=TagStatus.APPROVED)
        with pytest.raises(TagAlreadyApprovedError):
            handler.approve(tag.id, user)

    def test_raises_when_rejected(self):
        user = UserFactory(is_staff=True)
        tag = TagFactory(status=TagStatus.REJECTED)
        with pytest.raises(TagRejectedError):
            handler.approve(tag.id, user)


@pytest.mark.django_db
class TestReject:
    def test_rejects_and_clears_projects(self):
        user = UserFactory(is_staff=True)
        tag = TagFactory(status=TagStatus.APPROVED)
        project = ProjectFactory()
        project.tags.add(tag)

        result = handler.reject(tag.id, user)

        assert result.status == TagStatus.REJECTED
        assert result.reviewed_by == user
        assert Tag.objects.get(id=tag.id).projects.count() == 0

    def test_raises_when_missing(self):
        user = UserFactory(is_staff=True)
        with pytest.raises(TagNotFoundError):
            handler.reject(uuid4(), user)

    def test_raises_when_already_rejected(self):
        user = UserFactory(is_staff=True)
        tag = TagFactory(status=TagStatus.REJECTED)
        with pytest.raises(TagAlreadyRejectedError):
            handler.reject(tag.id, user)
