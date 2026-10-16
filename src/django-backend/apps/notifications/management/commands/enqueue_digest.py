"""Enqueue one digest task. Called by the `notify-*` CronJobs.

This is the deployment's entry point into the digest schedule. It exists so the
cron side names a stable CLI rather than a Python symbol: the jobs used to
`INSERT` straight into `django_tasks_database_dbtaskresult` with a hard-coded
`task_path` string, which meant renaming a task in `api/tasks/notifications.py`
broke production without failing anything the cron could see — the INSERT
succeeds whatever string it carries, and only the worker discovers the path no
longer resolves.

An unknown `--kind` / `--cadence` here is a non-zero exit on the CronJob itself.
"""

from argparse import ArgumentParser

from django.core.management.base import BaseCommand, CommandError

KIND_DISCUSSION = "discussion"
KIND_ARTICLE = "article"

# (kind, cadence) -> task name in `api.tasks.notifications`. Discussions have no
# weekly cadence (`DiscussionEmailFrequency` doesn't offer one), so that pairing
# is absent rather than a no-op.
TASK_BY_KIND_AND_CADENCE = {
    (KIND_DISCUSSION, "hourly"): "send_discussion_digest_hourly",
    (KIND_DISCUSSION, "daily"): "send_discussion_digest_daily",
    (KIND_ARTICLE, "hourly"): "send_article_digest_hourly",
    (KIND_ARTICLE, "daily"): "send_article_digest_daily",
    (KIND_ARTICLE, "weekly"): "send_article_digest_weekly",
}

KINDS = sorted({kind for kind, _ in TASK_BY_KIND_AND_CADENCE})
CADENCES = sorted({cadence for _, cadence in TASK_BY_KIND_AND_CADENCE})


class Command(BaseCommand):
    help = "Enqueue the digest task for one notification kind and cadence."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--kind", required=True, choices=KINDS)
        parser.add_argument("--cadence", required=True, choices=CADENCES)

    def handle(self, *args, **options) -> None:
        kind = options["kind"]
        cadence = options["cadence"]

        task_name = TASK_BY_KIND_AND_CADENCE.get((kind, cadence))
        if task_name is None:
            supported = ", ".join(
                sorted(c for k, c in TASK_BY_KIND_AND_CADENCE if k == kind)
            )
            msg = (
                f"No {kind} digest runs on a {cadence} cadence. "
                f"Supported cadences for {kind}: {supported}."
            )
            raise CommandError(msg)

        from api.tasks import notifications  # noqa: PLC0415

        getattr(notifications, task_name).enqueue()

        self.stdout.write(self.style.SUCCESS(f"Enqueued {task_name}"))
