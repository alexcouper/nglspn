from django.core.management.base import BaseCommand, CommandError

from apps.emails.broadcast_parity import check_all


class Command(BaseCommand):
    help = (
        "Compare legacy email_opt_in_* broadcast recipients against the new "
        "Follow-based resolver. Exits non-zero if they diverge. Run against a "
        "prod snapshot before dropping the legacy columns."
    )

    def handle(self, *args, **options) -> None:
        diverged = False
        for result in check_all():
            if result.matches:
                self.stdout.write(self.style.SUCCESS(f"{result.email_type}: parity OK"))
                continue
            diverged = True
            self.stdout.write(
                self.style.ERROR(
                    f"{result.email_type}: MISMATCH — "
                    f"{len(result.only_legacy)} legacy-only, "
                    f"{len(result.only_new)} new-only"
                )
            )
            for user_id in sorted(result.only_legacy):
                self.stdout.write(f"  legacy-only: {user_id}")
            for user_id in sorted(result.only_new):
                self.stdout.write(f"  new-only:    {user_id}")

        if diverged:
            msg = "Broadcast recipient parity check failed."
            raise CommandError(msg)
