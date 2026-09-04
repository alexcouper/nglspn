"""Apply the top-level categories of a taxonomy report.

    uv run python manage.py apply_taxonomy \
        ../../docs/taxonomy/<date>-report.json --dry-run

Reports are written by the `nglspn-taxonomy` skill and checked against the live
API by `python3 -m scripts.taxonomy check`. This command is the write half: it
takes a checked report and moves the database to match it.

Two deliberate limits. Projects are matched on `id`, never on title, because
titles are editorial text that changes. Categories the report drops are emptied
but never deleted: `Project.category` is `on_delete=SET_NULL`, so deleting a row
would silently uncategorise every draft and pending project still pointing at
it, and those never appear in a report — the API a report is built from only
serves approved projects.

Subcategories in the report are ignored. Nothing in the schema, the API or the
UI models them; the command says how many placements it passed over so a reader
is not left assuming they landed.
"""

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from apps.projects.models import Project, ProjectCategory

Placement = dict[str, Any]
CategoryEntry = dict[str, Any]


class Command(BaseCommand):
    help = "Apply a taxonomy report's top-level categories to the database."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("report", help="Path to a docs/taxonomy/<date>-report.json")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change, then roll it back.",
        )

    def handle(self, *args, **options) -> None:
        report = _load(Path(options["report"]))
        taxonomy = report.get("proposed_taxonomy", [])
        placements = _placements(report, defined={c["slug"] for c in taxonomy})
        projects = _projects_by_id(placements)

        with transaction.atomic():
            categories = self._upsert_categories(taxonomy)
            self._reassign(placements, projects, categories)
            self._report_retired({c["slug"] for c in taxonomy})
            self._report_ignored_subcategories(placements)

            if options["dry_run"]:
                # Roll back the real writes rather than predicting them, so the
                # output above is what an apply would actually do.
                transaction.set_rollback(True)
                self.stdout.write(
                    self.style.WARNING("Dry run — rolled back, nothing written.")
                )
                return

        self.stdout.write(self.style.SUCCESS("Applied."))

    def _upsert_categories(
        self, taxonomy: list[CategoryEntry]
    ) -> dict[str, ProjectCategory]:
        categories = {}
        for order, entry in enumerate(taxonomy, start=1):
            category, created = ProjectCategory.objects.update_or_create(
                slug=entry["slug"],
                defaults={"name": entry["name"], "display_order": order},
            )
            categories[category.slug] = category
            verb = "created" if created else "updated"
            self.stdout.write(f"  {verb}  {category.slug} — {category.name} ({order})")
        return categories

    def _reassign(
        self,
        placements: list[Placement],
        projects: dict[UUID, Project],
        categories: dict[str, ProjectCategory],
    ) -> None:
        moved = unchanged = 0
        for placement in placements:
            project = projects[UUID(placement["id"])]
            target = categories[placement["proposed_category_slug"]]
            was = project.category.slug if project.category else None

            # A project sitting at neither the category the report read nor the
            # one it proposes has been moved by someone else since the report
            # was written. Sitting at the proposed one just means this report
            # has already been applied, which is not worth a warning.
            if was not in (placement["current_category_slug"], target.slug):
                self.stdout.write(
                    self.style.WARNING(
                        f"  stale   {project.title}: report says it is in "
                        f"{placement['current_category_slug']}, database says {was}"
                    )
                )

            if project.category_id == target.id:
                unchanged += 1
                continue

            project.category = target
            project.save(update_fields=["category"])
            moved += 1
            self.stdout.write(f"  moved   {project.title}: {was} -> {target.slug}")

        self.stdout.write(f"{moved} moved, {unchanged} unchanged.")

    def _report_retired(self, defined: set[str]) -> None:
        for category in ProjectCategory.objects.exclude(slug__in=defined):
            held = category.projects.count()
            if held:
                self.stdout.write(
                    self.style.WARNING(
                        f"  retired {category.slug} still holds {held} project(s) the "
                        f"report does not cover — row kept, they stay where they are"
                    )
                )
            else:
                self.stdout.write(f"  retired {category.slug} — now empty, row kept")

    def _report_ignored_subcategories(self, placements: list[Placement]) -> None:
        wanted = sum(1 for p in placements if p.get("proposed_subcategory_slug"))
        if wanted:
            self.stdout.write(
                f"{wanted} subcategory placement(s) ignored — no subcategory support."
            )


def _load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        msg = f"No such report: {path}"
        raise CommandError(msg) from None
    except json.JSONDecodeError as exc:
        msg = f"{path} is not valid JSON: {exc}"
        raise CommandError(msg) from None


def _placements(report: dict[str, Any], defined: set[str]) -> list[Placement]:
    """The report entries that name a category, once every name is known good."""
    placed = [p for p in report.get("projects", []) if p.get("proposed_category_slug")]

    undefined = sorted(
        {
            p["proposed_category_slug"]
            for p in placed
            if p["proposed_category_slug"] not in defined
        }
    )
    if undefined:
        msg = "Report places projects in categories it never defines: " + ", ".join(
            undefined
        )
        raise CommandError(msg)
    return placed


def _projects_by_id(placements: list[Placement]) -> dict[UUID, Project]:
    try:
        wanted = [UUID(p["id"]) for p in placements]
    except (ValueError, TypeError) as exc:
        msg = f"Report contains a malformed project id: {exc}"
        raise CommandError(msg) from None

    found = Project.objects.select_related("category").in_bulk(wanted)

    missing = [p for p in placements if UUID(p["id"]) not in found]
    if missing:
        listed = ", ".join(f"{p['title']} ({p['id']})" for p in missing[:10])
        msg = (
            f"{len(missing)} project(s) in the report are not in the database: {listed}"
        )
        raise CommandError(msg)
    return found
