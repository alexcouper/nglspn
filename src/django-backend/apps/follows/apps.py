from django.apps import AppConfig


class FollowsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.follows"

    def ready(self) -> None:
        # Django convention: import signal handlers in ready() so they are
        # connected once the app registry is fully loaded.
        from apps.follows import signals  # noqa: F401, PLC0415
