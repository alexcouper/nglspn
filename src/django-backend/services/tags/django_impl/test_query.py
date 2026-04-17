from uuid import uuid4

import pytest

from apps.projects.models import ProjectStatus
from apps.tags.models import TagStatus
from services.tags.django_impl import DjangoTagQuery
from services.tags.exceptions import TagNotFoundError
from tests.factories import ProjectFactory, TagCategoryFactory, TagFactory

query = DjangoTagQuery()


@pytest.mark.django_db
class TestListNonRejected:
    def test_excludes_rejected(self):
        approved = TagFactory(status=TagStatus.APPROVED)
        pending = TagFactory(status=TagStatus.PENDING)
        rejected = TagFactory(status=TagStatus.REJECTED)

        result_ids = {t.id for t in query.list_non_rejected()}

        assert approved.id in result_ids
        assert pending.id in result_ids
        assert rejected.id not in result_ids


@pytest.mark.django_db
class TestListCategories:
    def test_returns_only_active(self):
        active = TagCategoryFactory(is_active=True)
        inactive = TagCategoryFactory(is_active=False)

        ids = {c.id for c in query.list_categories()}

        assert active.id in ids
        assert inactive.id not in ids


@pytest.mark.django_db
class TestListGrouped:
    def test_returns_categories_with_tags(self):
        category = TagCategoryFactory()
        tag = TagFactory(category=category)

        result = query.list_grouped()

        group = next(g for g in result if g.category.id == category.id)
        assert tag.id in {t.id for t in group.tags}

    def test_with_projects_filters_to_approved(self):
        category = TagCategoryFactory()
        tag_with = TagFactory(category=category)
        tag_without = TagFactory(category=category)
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        project.tags.add(tag_with)

        result = query.list_grouped(with_projects=True)

        group = next(g for g in result if g.category.id == category.id)
        tag_ids = {t.id for t in group.tags}
        assert tag_with.id in tag_ids
        assert tag_without.id not in tag_ids


@pytest.mark.django_db
class TestListPending:
    def test_returns_pending_only(self):
        pending = TagFactory(status=TagStatus.PENDING)
        approved = TagFactory(status=TagStatus.APPROVED)

        ids = {t.id for t in query.list_pending()}

        assert pending.id in ids
        assert approved.id not in ids


@pytest.mark.django_db
class TestGetById:
    def test_returns_tag(self):
        tag = TagFactory()

        result = query.get_by_id(tag.id)

        assert result.id == tag.id

    def test_raises_when_missing(self):
        with pytest.raises(TagNotFoundError):
            query.get_by_id(uuid4())
