from unittest.mock import patch
from uuid import uuid4

import pytest

from apps.projects.models import UploadStatus
from services.project_images.django_impl import (
    DjangoProjectImageHandler,
    DjangoProjectImageQuery,
)
from services.project_images.exceptions import (
    ProjectImageNotFoundError,
)
from tests.factories import ProjectFactory, ProjectImageFactory, UserFactory

query = DjangoProjectImageQuery()
handler = DjangoProjectImageHandler()


@pytest.mark.django_db
class TestGetProjectForOwner:
    def test_returns_project_owned_by_user(self):
        user = UserFactory()
        project = ProjectFactory(owner=user)

        result = query.get_project_for_owner(project.id, user.id)

        assert result.id == project.id

    def test_raises_when_not_owner(self):
        project = ProjectFactory()
        other_user = UserFactory()

        with pytest.raises(ProjectImageNotFoundError):
            query.get_project_for_owner(project.id, other_user.id)


@pytest.mark.django_db
class TestGetImageForProject:
    def test_returns_image_for_project(self):
        image = ProjectImageFactory()

        result = query.get_image_for_project(image.id, image.project_id)

        assert result.id == image.id

    def test_filters_by_upload_status(self):
        image = ProjectImageFactory(upload_status=UploadStatus.PENDING)

        result = query.get_image_for_project(
            image.id, image.project_id, upload_status="pending"
        )
        assert result.id == image.id

        with pytest.raises(ProjectImageNotFoundError):
            query.get_image_for_project(
                image.id, image.project_id, upload_status="uploaded"
            )

    def test_raises_for_nonexistent_image(self):
        project = ProjectFactory()

        with pytest.raises(ProjectImageNotFoundError):
            query.get_image_for_project(uuid4(), project.id)


@pytest.mark.django_db
class TestCountUploadedNonIconImages:
    def test_counts_uploaded_non_icon_images(self):
        project = ProjectFactory()
        ProjectImageFactory(project=project, upload_status="uploaded", is_icon=False)
        ProjectImageFactory(project=project, upload_status="uploaded", is_icon=True)
        ProjectImageFactory(project=project, upload_status="pending", is_icon=False)

        count = query.count_uploaded_non_icon_images(project)

        assert count == 1


@pytest.mark.django_db
class TestHasMainImage:
    def test_returns_true_when_main_image_exists(self):
        project = ProjectFactory()
        ProjectImageFactory(project=project, is_main=True)

        assert query.has_main_image(project) is True

    def test_returns_false_when_no_main_image(self):
        project = ProjectFactory()
        ProjectImageFactory(project=project, is_main=False)

        assert query.has_main_image(project) is False


@pytest.mark.django_db
class TestCreateImage:
    def test_creates_image_with_pending_status(self):
        user = UserFactory()
        project = ProjectFactory(owner=user)

        image = handler.create_image(
            project_id=project.id,
            owner_id=user.id,
            storage_key="test/key.jpg",
            original_filename="test.jpg",
            content_type="image/jpeg",
            file_size=1024,
            is_icon=False,
            display_order=0,
        )

        assert image.upload_status == UploadStatus.PENDING
        assert image.project_id == project.id

    def test_raises_for_nonexistent_project(self):
        user = UserFactory()

        with pytest.raises(ProjectImageNotFoundError):
            handler.create_image(
                project_id=uuid4(),
                owner_id=user.id,
                storage_key="test/key.jpg",
                original_filename="test.jpg",
                content_type="image/jpeg",
                file_size=1024,
                is_icon=False,
                display_order=0,
            )


@pytest.mark.django_db
class TestCompleteUpload:
    def test_completes_upload_and_sets_main_for_first_non_icon(self):
        user = UserFactory()
        project = ProjectFactory(owner=user)
        image = ProjectImageFactory(
            project=project, upload_status="pending", is_icon=False
        )

        result = handler.complete_upload(
            project_id=project.id,
            owner_id=user.id,
            image_id=image.id,
            width=800,
            height=600,
        )

        assert result.upload_status == UploadStatus.UPLOADED
        assert result.is_main is True
        assert result.width == 800


@pytest.mark.django_db
class TestUpdateRoles:
    def test_sets_exclusive_role(self):
        user = UserFactory()
        project = ProjectFactory(owner=user)
        image1 = ProjectImageFactory(
            project=project, upload_status="uploaded", is_main=True
        )
        image2 = ProjectImageFactory(
            project=project, upload_status="uploaded", is_main=False
        )

        handler.update_roles(
            project_id=project.id,
            owner_id=user.id,
            image_id=image2.id,
            is_main=True,
        )

        image1.refresh_from_db()
        image2.refresh_from_db()
        assert image1.is_main is False
        assert image2.is_main is True


@pytest.mark.django_db
class TestDeleteImage:
    @patch("services.project_images.django_impl.handler.storage_service")
    def test_deletes_image(self, mock_storage):
        user = UserFactory()
        project = ProjectFactory(owner=user)
        image = ProjectImageFactory(project=project)

        handler.delete_image(
            project_id=project.id,
            owner_id=user.id,
            image_id=image.id,
        )

        assert not project.images.filter(id=image.id).exists()

    @patch("services.project_images.django_impl.handler.storage_service")
    def test_promotes_next_image_to_main(self, mock_storage):
        user = UserFactory()
        project = ProjectFactory(owner=user)
        main_image = ProjectImageFactory(
            project=project, upload_status="uploaded", is_main=True
        )
        other_image = ProjectImageFactory(
            project=project, upload_status="uploaded", is_main=False
        )

        handler.delete_image(
            project_id=project.id,
            owner_id=user.id,
            image_id=main_image.id,
        )

        other_image.refresh_from_db()
        assert other_image.is_main is True
