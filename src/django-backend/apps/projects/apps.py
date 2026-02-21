from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.projects"

    def ready(self) -> None:
        from django.db.models.signals import post_delete, post_save  # noqa: PLC0415

        from apps.projects.models import Project  # noqa: PLC0415
        from apps.projects.signals import (  # noqa: PLC0415
            on_project_deleted,
            on_project_saved,
        )

        post_save.connect(on_project_saved, sender=Project)
        post_delete.connect(on_project_deleted, sender=Project)
