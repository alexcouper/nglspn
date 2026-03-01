from __future__ import annotations

import logging

from django.core.management.base import BaseCommand
from django.db.models import Case, Count, F, IntegerField, Value, When

from apps.projects.models import (
    VARIANT_SIZE_WIDTHS,
    ProjectImage,
    UploadStatus,
    VariantSize,
)
from services import HANDLERS

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate missing image variants for all uploaded project images."

    def handle(self, *args, **options) -> None:
        # Build an expression that counts how many variant sizes apply to each
        # image based on its width (only sizes with target_width < original_width
        # are generated). Images with unknown width get the max count so they
        # are still processed (the handler backfills dimensions on first run).
        applicable_count = Value(0, output_field=IntegerField())
        for target_width in VARIANT_SIZE_WIDTHS.values():
            applicable_count = applicable_count + Case(
                When(width__gt=target_width, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )

        expected_variants = Case(
            When(width__isnull=True, then=Value(len(VariantSize))),
            default=applicable_count,
            output_field=IntegerField(),
        )

        images = (
            ProjectImage.objects.filter(upload_status=UploadStatus.UPLOADED)
            .annotate(
                variant_count=Count("variants"),
                expected_variants=expected_variants,
            )
            .filter(variant_count__lt=F("expected_variants"))
            .order_by("created_at")
        )

        total = images.count()
        if total == 0:
            self.stdout.write("No images need variant generation.")
            return

        self.stdout.write(f"Processing {total} images...")

        for i, image in enumerate(images, start=1):
            try:
                HANDLERS.image.generate_variants(str(image.id))
            except Exception:
                logger.exception("Failed to process image %s", image.id)

            if i % 10 == 0 or i == total:
                self.stdout.write(f"  {i}/{total} processed")

        self.stdout.write(self.style.SUCCESS(f"Done. Processed {total} images."))
