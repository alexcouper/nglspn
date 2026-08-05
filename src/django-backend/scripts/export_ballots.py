#!/usr/bin/env python
"""Dump every competition's ballots to CSV. Raw data only.

Deliberately dumb: it imports nothing from `services/`, computes nothing, and
touches only long-standing model fields, so it runs against an older deployment
than the checkout it came from. All analysis happens elsewhere, on the exported
CSVs — see scripts/analyse_ballots.py.

READ ONLY. On PostgreSQL the session is put into read-only mode before any
query runs, so this cannot modify production even by mistake.

Reviewer identity is pseudonymised: each reviewer becomes a per-run reference
like `R007`. That is all the analysis needs — which rows belong to the same
ballot — without exporting who voted for what. No email, no name, no kennitala
leaves the database unless you pass --include-emails.

Writes four files to the output directory (default /tmp):

    competitions.csv  one row per competition
    projects.csv      which projects were in which competition
    reviewers.csv     one row per assigned reviewer, with their ballot length
    ballots.csv       one row per ranking: competition, reviewer, project, position

Run it from the django-backend directory — that is where it looks for the
Django project. Copying the file elsewhere is fine; the working directory is
what matters, not where the file sits.

Usage:
    uv run python /tmp/export_ballots.py
    uv run python /tmp/export_ballots.py --out /tmp/nglspn-export
    uv run python /tmp/export_ballots.py --include-emails   # PII
"""

import argparse
import csv
import os
import sys
from pathlib import Path


def find_backend_root() -> Path:
    """Locate the directory holding `project_showcase`, wherever we ran from.

    This script is meant to be copied onto a server, so it cannot assume it
    still lives in `<backend>/scripts/`. Worth knowing why it has to look:
    `python /tmp/export_ballots.py` puts */tmp* on `sys.path`, not the working
    directory — which is why an interactive `python` in the same shell can
    import the app but the script cannot.
    """
    candidates = [
        Path.cwd(),
        Path.cwd() / "src" / "django-backend",
        Path(__file__).resolve().parent.parent,
    ]
    for candidate in candidates:
        if (candidate / "project_showcase" / "settings.py").is_file():
            return candidate

    looked = "\n  ".join(str(c) for c in candidates)
    message = (
        "Could not find the Django project (project_showcase/settings.py).\n"
        f"Looked in:\n  {looked}\n"
        "Run this from the django-backend directory, or set PYTHONPATH to it."
    )
    raise SystemExit(message)


sys.path.insert(0, str(find_backend_root()))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_showcase.settings")

import django

django.setup()

from django.db import connection

from apps.projects.models import (
    Competition,
    CompetitionReviewer,
    ProjectRanking,
)

DEFAULT_OUT = Path("/tmp")  # noqa: S108 — asked for; --out overrides

# Wanted, but not assumed: an older deployment may not have all of these, so
# each is included only if the model actually declares it.
COMPETITION_FIELDS = [
    "id",
    "name",
    "slug",
    "status",
    "start_date",
    "submission_deadline",
    "voting_end_date",
    "winner",
]
PROJECT_FIELDS = ["id", "title", "slug", "status"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"directory to write the CSVs into (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--include-emails",
        action="store_true",
        help="also export reviewer emails (PII; off by default)",
    )
    return parser.parse_args()


def present_fields(model: type, wanted: list[str]) -> list[str]:
    """Whichever of `wanted` this deployment's model actually declares."""
    declared = {field.name for field in model._meta.get_fields()}  # noqa: SLF001
    return [name for name in wanted if name in declared]


def go_read_only() -> None:
    """Make writes impossible for the rest of this session, where supported."""
    if connection.vendor != "postgresql":
        print(f"  (database is {connection.vendor}; read-only guard is postgres-only)")
        return
    with connection.cursor() as cursor:
        cursor.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
    print("  Session set to READ ONLY.")


def describe_target() -> str:
    """Which database this is about to read, without revealing credentials."""
    params = connection.get_connection_params()
    name = params.get("database") or params.get("dbname") or "?"
    host = params.get("host", "local")
    return f"{connection.vendor}://{host}/{name}"


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"  {path}  ({len(rows)} rows)")


def export(out: Path, *, include_emails: bool) -> None:
    competition_fields = present_fields(Competition, COMPETITION_FIELDS)
    project_fields = present_fields(
        ProjectRanking.project.field.related_model, PROJECT_FIELDS
    )
    print(f"  competition columns: {', '.join(competition_fields)}")
    print(f"  project columns:     {', '.join(project_fields)}")

    competitions = list(Competition.objects.all().values(*competition_fields))
    competition_ids = [c["id"] for c in competitions]
    names = {c["id"]: c["name"] for c in competitions}

    membership = list(
        Competition.projects.through.objects.filter(
            competition_id__in=competition_ids
        ).values_list("competition_id", "project_id")
    )

    project_model = ProjectRanking.project.field.related_model
    project_ids = {pid for _cid, pid in membership}
    projects = {
        p["id"]: p
        for p in project_model.objects.filter(id__in=project_ids).values(
            *project_fields
        )
    }

    assignments = list(
        CompetitionReviewer.objects.filter(
            competition_id__in=competition_ids
        ).values_list("competition_id", "user_id", "status")
    )
    rankings = list(
        ProjectRanking.objects.filter(competition_id__in=competition_ids)
        .order_by("competition_id", "reviewer_id", "position")
        .values_list("competition_id", "reviewer_id", "project_id", "position")
    )

    refs = {
        uid: f"R{i:03d}"
        for i, uid in enumerate(
            sorted({uid for _cid, uid, _st in assignments}, key=str), start=1
        )
    }

    ballot_length: dict = {}
    for competition_id, reviewer_id, _project_id, _position in rankings:
        key = (competition_id, reviewer_id)
        ballot_length[key] = ballot_length.get(key, 0) + 1

    out.mkdir(parents=True, exist_ok=True)

    counts_by_competition: dict = {}
    for competition_id, _uid, status in assignments:
        bucket = counts_by_competition.setdefault(competition_id, {"all": 0, "done": 0})
        bucket["all"] += 1
        if status == "completed":
            bucket["done"] += 1

    # `id` on its own would be ambiguous once these files sit side by side,
    # so every column says which entity it belongs to.
    write_csv(
        out / "competitions.csv",
        [
            *[
                "competition_id" if f == "id" else f"competition_{f}"
                for f in competition_fields
            ],
            "reviewers_assigned",
            "reviewers_completed",
        ],
        [
            [
                *[
                    c.get(f, "") if c.get(f) is not None else ""
                    for f in competition_fields
                ],
                counts_by_competition.get(c["id"], {}).get("all", 0),
                counts_by_competition.get(c["id"], {}).get("done", 0),
            ]
            for c in competitions
        ],
    )

    write_csv(
        out / "projects.csv",
        [
            "competition_id",
            "competition_name",
            *[f"project_{f}" for f in project_fields],
        ],
        [
            [
                competition_id,
                names.get(competition_id, ""),
                *[
                    projects.get(project_id, {}).get(f, "")
                    if projects.get(project_id, {}).get(f) is not None
                    else ""
                    for f in project_fields
                ],
            ]
            for competition_id, project_id in membership
        ],
    )

    reviewer_header = [
        "competition_id",
        "competition_name",
        "reviewer_ref",
        "review_status",
        "projects_ranked",
    ]
    reviewer_rows = [
        [
            competition_id,
            names.get(competition_id, ""),
            refs[user_id],
            status,
            ballot_length.get((competition_id, user_id), 0),
        ]
        for competition_id, user_id, status in sorted(
            assignments, key=lambda a: (str(a[0]), refs[a[1]])
        )
    ]
    if include_emails:
        user_model = CompetitionReviewer.user.field.related_model
        emails = dict(user_model.objects.filter(id__in=refs).values_list("id", "email"))
        reviewer_header.append("email")
        by_ref = {refs[uid]: email for uid, email in emails.items()}
        for row in reviewer_rows:
            row.append(by_ref.get(row[2], ""))
    write_csv(out / "reviewers.csv", reviewer_header, reviewer_rows)

    write_csv(
        out / "ballots.csv",
        [
            "competition_id",
            "competition_name",
            "reviewer_ref",
            "project_id",
            "project_title",
            "position",
        ],
        [
            [
                competition_id,
                names.get(competition_id, ""),
                refs[reviewer_id],
                project_id,
                projects.get(project_id, {}).get("title", "(not in competition)"),
                position,
            ]
            for competition_id, reviewer_id, project_id, position in rankings
        ],
    )

    print(
        f"\n{len(competitions)} competitions, {len(assignments)} reviewer assignments, "
        f"{len(rankings)} ranking rows."
    )


def main() -> None:
    args = parse_args()
    print(f"Reading {describe_target()}")
    go_read_only()
    export(args.out, include_emails=args.include_emails)
    print(f"\nDone. Send me the four CSVs in {args.out}/ (or just tar that directory).")
    if args.include_emails:
        print(
            "reviewers.csv contains emails — strip it before sharing if you'd rather not."
        )


if __name__ == "__main__":
    main()
