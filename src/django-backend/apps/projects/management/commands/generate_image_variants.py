from __future__ import annotations

import logging

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.projects.models import (
    ProjectImage,
    UploadStatus,
    VariantSize,
)
from services import HANDLERS

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate missing image variants for all uploaded project images."

    def handle(self, *args, **options) -> None:
        all_sizes = list(VariantSize)
        expected_count = len(all_sizes)

        # Find uploaded images that are missing at least one expected variant.
        # We can't filter on "missing for original width" here because that
        # depends on per-image width, so we grab all images with fewer than
        # the max possible variants and let the handler skip sizes that don't
        # apply (>= original width) or already exist.
        images = (
            ProjectImage.objects.filter(upload_status=UploadStatus.UPLOADED)
            .annotate(variant_count=Count("variants"))
            .filter(variant_count__lt=expected_count)
            .order_by("created_at")
        )

        total = images.count()
        if total == 0:
            self.stdout.write("No images need variant generation.")
            return

        self.stdout.write(f"Processing {total} images...")

        for i, image in enumerate(images.iterator(), start=1):
            try:
                HANDLERS.image.generate_variants(str(image.id))
            except Exception:
                logger.exception("Failed to process image %s", image.id)

            if i % 10 == 0 or i == total:
                self.stdout.write(f"  {i}/{total} processed")

        self.stdout.write(self.style.SUCCESS(f"Done. Processed {total} images."))
