from __future__ import annotations

from django_tasks import task


@task()
def generate_image_variants(image_id: str) -> None:
    from services import HANDLERS  # noqa: PLC0415

    HANDLERS.image.generate_variants(image_id)
