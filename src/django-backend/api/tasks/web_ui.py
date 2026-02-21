from __future__ import annotations

from django_tasks import task


@task()
def revalidate_project(project_id: str) -> None:
    from services import HANDLERS  # noqa: PLC0415

    HANDLERS.web_ui.revalidate_paths(
        [
            "/",
            "/projects",
            f"/projects/{project_id}",
            "/competitions",
        ]
    )
