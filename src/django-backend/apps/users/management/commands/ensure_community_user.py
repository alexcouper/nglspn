from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.users.seed import ensure_community_user


class Command(BaseCommand):
    help = "Idempotently create the Community/Unowned system user."

    def handle(self, *args, **options) -> None:
        user = ensure_community_user(get_user_model())
        self.stdout.write(
            self.style.SUCCESS(
                f"Community/Unowned user ensured: {user.email} ({user.id})"
            )
        )
