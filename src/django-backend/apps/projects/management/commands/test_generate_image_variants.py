from __future__ import annotations

from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.projects.models import ImageVariant, UploadStatus, VariantSize
from tests.factories import ProjectImageFactory


@pytest.mark.django_db
class TestGenerateImageVariantsCommand:
    def test_processes_uploaded_images_missing_variants(self):
        img1 = ProjectImageFactory(
            width=4000, height=2250, upload_status=UploadStatus.UPLOADED
        )
        img2 = ProjectImageFactory(
            width=2000, height=1500, upload_status=UploadStatus.UPLOADED
        )

        with patch("services.HANDLERS.image.generate_variants") as mock_gen:
            call_command("generate_image_variants")

        assert mock_gen.call_count == 2
        called_ids = {c.args[0] for c in mock_gen.call_args_list}
        assert called_ids == {str(img1.id), str(img2.id)}

    def test_skips_non_uploaded_images(self):
        ProjectImageFactory(width=4000, height=2250, upload_status=UploadStatus.PENDING)
        ProjectImageFactory(width=4000, height=2250, upload_status=UploadStatus.FAILED)

        with patch("services.HANDLERS.image.generate_variants") as mock_gen:
            call_command("generate_image_variants")

        mock_gen.assert_not_called()

    def test_idempotent_skips_images_with_all_variants(self):
        image = ProjectImageFactory(
            width=4000, height=2250, upload_status=UploadStatus.UPLOADED
        )
        # Pre-create all 3 variants
        for size in VariantSize:
            ImageVariant.objects.create(
                image=image,
                size=size,
                storage_key=f"projects/test/{size}.webp",
                width=100,
                height=100,
                file_size=1000,
            )

        with patch("services.HANDLERS.image.generate_variants") as mock_gen:
            call_command("generate_image_variants")

        mock_gen.assert_not_called()

    def test_processes_images_with_partial_variants(self):
        image = ProjectImageFactory(
            width=4000, height=2250, upload_status=UploadStatus.UPLOADED
        )
        # Only thumb exists — still missing medium and large
        ImageVariant.objects.create(
            image=image,
            size=VariantSize.THUMB,
            storage_key="projects/test/thumb.webp",
            width=384,
            height=216,
            file_size=1000,
        )

        with patch("services.HANDLERS.image.generate_variants") as mock_gen:
            call_command("generate_image_variants")

        mock_gen.assert_called_once_with(str(image.id))

    def test_continues_on_individual_image_failure(self):
        img1 = ProjectImageFactory(
            width=4000, height=2250, upload_status=UploadStatus.UPLOADED
        )
        ProjectImageFactory(
            width=4000, height=2250, upload_status=UploadStatus.UPLOADED
        )

        msg = "boom"

        def fail_on_first(image_id):
            if image_id == str(img1.id):
                raise RuntimeError(msg)

        with patch(
            "services.HANDLERS.image.generate_variants", side_effect=fail_on_first
        ) as mock_gen:
            call_command("generate_image_variants")

        # Both should have been attempted despite the first failing
        assert mock_gen.call_count == 2
