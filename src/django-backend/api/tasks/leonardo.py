from __future__ import annotations

from django_tasks import task


@task()
def generate_project_image(generation_request_id: str) -> None:
    from services import HANDLERS  # noqa: PLC0415

    HANDLERS.leonardo.generate(generation_request_id)
