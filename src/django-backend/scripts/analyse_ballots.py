#!/usr/bin/env python
"""Run the new tally over ballots exported from production.

Reads the CSVs written by scripts/export_ballots.py and, for every competition,
shows what the old Borda score said and what the pairwise/Schulze tally says.
No reconstruction and no sampling — these are the real ballots, so the answer
is exact.

With --load it also recreates the competitions in the local database, so the
new admin results page renders real production data. Local only: it refuses to
run against anything that is not SQLite unless you pass --i-know-its-not-local.

Usage:
    uv run python scripts/analyse_ballots.py --in /tmp/nglspn-export
    uv run python scripts/analyse_ballots.py --in /tmp/nglspn-export --load
    uv run python scripts/analyse_ballots.py --in /tmp/nglspn-export --only "Broadside"
"""

import argparse
import csv
import os
import secrets
import string
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

DJANGO_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DJANGO_BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_showcase.settings")

import django

django.setup()

from django.db import connection

from apps.projects.models import (
    Competition,
    CompetitionReviewer,
    CompetitionStatus,
    Project,
    ProjectRanking,
    ProjectStatus,
    ReviewStatus,
)
from apps.users.models import User
from services import HANDLERS
from services.review.tally import (
    break_ties,
    reduce_ballots_to_margins,
    schulze_order,
    support_signals,
)

COIN_FLIP = 1
CLOSE = 3
LOADED_PREFIX = "prod-voter-"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--in",
        dest="source",
        type=Path,
        required=True,
        help="directory holding the exported CSVs",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="only competitions whose name contains this (case-insensitive)",
    )
    parser.add_argument(
        "--load",
        action="store_true",
        help="also recreate the competitions in the local database",
    )
    parser.add_argument(
        "--i-know-its-not-local",
        action="store_true",
        help="permit --load against a non-SQLite database",
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict]:
    if not path.is_file():
        message = f"missing {path} — run scripts/export_ballots.py first"
        raise SystemExit(message)
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class Export:
    """The four CSVs, indexed the way the tally wants them."""

    def __init__(self, source: Path) -> None:
        self.competitions = read_csv(source / "competitions.csv")
        self.projects = read_csv(source / "projects.csv")
        self.reviewers = read_csv(source / "reviewers.csv")
        self.ballot_rows = read_csv(source / "ballots.csv")

        self.title = {r["project_id"]: r["project_title"] for r in self.projects}
        self.status = {
            r["project_id"]: r.get("project_status", "") for r in self.projects
        }

        self.in_competition = defaultdict(list)
        for row in self.projects:
            self.in_competition[row["competition_id"]].append(row["project_id"])

        self.completed = defaultdict(set)
        for row in self.reviewers:
            if row["review_status"] == "completed":
                self.completed[row["competition_id"]].add(row["reviewer_ref"])

    def eligible(self, competition_id: str) -> list[str]:
        return [
            pid
            for pid in self.in_competition.get(competition_id, [])
            if self.status.get(pid) not in ("rejected", "ice_box")
        ]

    def ballots(self, competition_id: str) -> dict[str, list[str]]:
        """Counted ballots only: completed reviewers, eligible projects, in order."""
        eligible = set(self.eligible(competition_id))
        counted = self.completed.get(competition_id, set())
        by_reviewer: dict[str, list[tuple[int, str]]] = {ref: [] for ref in counted}
        for row in self.ballot_rows:
            if row["competition_id"] != competition_id:
                continue
            ref = row["reviewer_ref"]
            if ref in by_reviewer and row["project_id"] in eligible:
                by_reviewer[ref].append((int(row["position"]), row["project_id"]))
        return {
            ref: [pid for _pos, pid in sorted(entries)]
            for ref, entries in by_reviewer.items()
        }


def borda(ballots: dict[str, list[str]], eligible: list[str]) -> dict[str, int]:
    """The old rule, for comparison: 1st is worth len(eligible), last is worth 1.

    Unranked projects score nothing, which is exactly the bias that motivated
    the change — on full ballots it makes no difference.
    """
    scores = dict.fromkeys(eligible, 0)
    for ballot in ballots.values():
        for index, project_id in enumerate(ballot):
            scores[project_id] += len(eligible) - index
    return scores


def closeness(margin: int) -> str:
    if abs(margin) <= COIN_FLIP:
        return "COIN FLIP"
    if abs(margin) <= CLOSE:
        return "close"
    return "clear"


def report(export: Export, competition: dict) -> None:
    competition_id = competition["competition_id"]
    name = competition["competition_name"]
    eligible = export.eligible(competition_id)
    ballots = export.ballots(competition_id)

    print(f"\n{'=' * 70}\n{name}  [{competition.get('competition_status', '?')}]")
    if not ballots or not eligible:
        print("  no counted ballots — nothing to decide")
        return

    lengths = [len(b) for b in ballots.values()]
    partial = sum(1 for n in lengths if n < len(eligible))
    print(
        f"  {len(ballots)} counted ballots, {len(eligible)} projects, "
        f"{partial} partial, {sum(1 for n in lengths if n == 0)} abstentions"
    )

    margins = reduce_ballots_to_margins(ballots.values(), eligible)
    support = support_signals(ballots.values(), eligible)
    # Same ladder the admin page applies, so the two never disagree.
    tiers, tie_breaks = break_ties(schulze_order(margins), margins, support)
    scores = borda(ballots, eligible)
    old_order = sorted(eligible, key=lambda p: -scores[p])
    old_rank = {p: i + 1 for i, p in enumerate(old_order)}
    firsts = {p: sum(1 for b in ballots.values() if b and b[0] == p) for p in eligible}

    print(f"\n  {'old':<5}{'new':<6}{'project':<24}{'borda':>6}{'1sts':>6}  moved")
    rank = 1
    for tier in tiers:
        for project_id in tier:
            was = old_rank[project_id]
            move = was - rank
            arrow = (
                "—" if move == 0 else (f"up {move}" if move > 0 else f"down {-move}")
            )
            marker = (
                "=" if len(tier) > 1 else ("*" if project_id in tie_breaks else " ")
            )
            print(
                f"  {was:<5}{str(rank) + marker:<6}"
                f"{export.title.get(project_id, '?')[:23]:<24}"
                f"{scores[project_id]:>6}{firsts[project_id]:>6}  {arrow}"
            )
        rank += len(tier)

    for project_id in [p for tier in tiers for p in tier if p in tie_breaks]:
        others = ", ".join(
            export.title.get(o, "?") for o in tie_breaks[project_id].tied_with
        )
        print(
            f"    * {export.title.get(project_id, '?')} — separated from "
            f"{others} by {tie_breaks[project_id].rung}"
        )

    flat = [p for tier in tiers for p in tier]
    if len(tiers[0]) > 1:
        shared = ", ".join(export.title.get(p, "?") for p in tiers[0])
        print(f"\n  TIED AT THE TOP: {shared} — a real judgement call")
    elif len(flat) > 1:
        top, runner_up = flat[0], flat[1]
        margin = margins[top][runner_up]
        print(
            f"\n  {export.title.get(top, '?')} beats "
            f"{export.title.get(runner_up, '?')} by {margin:+d} "
            f"of {len(ballots)} -> {closeness(margin)}"
        )

    winner_id = competition.get("competition_winner") or ""
    if winner_id and winner_id != flat[0]:
        print(
            f"  NOTE: the winner set by hand was "
            f"{export.title.get(winner_id, winner_id)}, not the pairwise top"
        )

    print("\n  pairwise margins (row beats column by):")
    order = flat
    print("       " + "".join(f"{export.title.get(p, '?')[:7]:>9}" for p in order))
    for a in order:
        cells = "".join(
            f"{'—':>9}" if a == b else f"{margins[a][b]:>+9d}" for b in order
        )
        print(f"    {export.title.get(a, '?')[:5]:<5}{cells}")


def load_into_local_db(
    export: Export, competitions: list[dict], *, forced: bool
) -> None:
    """Recreate the exported competitions locally so the admin page renders them."""
    if connection.vendor != "sqlite" and not forced:
        message = (
            f"refusing to load into a {connection.vendor} database. "
            "This writes data — use a local SQLite dev database, or pass "
            "--i-know-its-not-local if you are certain."
        )
        raise SystemExit(message)

    admin = User.objects.filter(is_staff=True).first()
    print("\nLoading into the local database...")

    for competition in competitions:
        competition_id = competition["competition_id"]
        ballots = export.ballots(competition_id)
        if not ballots:
            continue

        local_name = f"{competition['competition_name']} (prod)"
        obj, _ = Competition.objects.get_or_create(
            name=local_name,
            defaults={
                "start_date": date(2026, 1, 1),
                "submission_deadline": date(2026, 1, 31),
                "status": CompetitionStatus.VOTING,
            },
        )

        by_export_id = {}
        for project_id in export.eligible(competition_id):
            project, _ = Project.objects.get_or_create(
                title=export.title.get(project_id, project_id),
                submission_month=f"prod-{competition_id[:8]}",
                defaults={
                    "tagline": "Imported from the production export",
                    "description": "Imported so the results page has real ballots.",
                    "website_url": "https://example.invalid",
                    "status": ProjectStatus.APPROVED,
                    "creator": admin,
                    "approved_by": admin,
                },
            )
            by_export_id[project_id] = project
        obj.projects.set(by_export_id.values())

        for ref, ballot in ballots.items():
            user, created = User.objects.get_or_create(
                email=f"{LOADED_PREFIX}{competition_id[:8]}-{ref}@example.com",
                defaults={
                    "first_name": "Prod",
                    "last_name": ref,
                    "kennitala": "".join(
                        secrets.choice(string.digits) for _ in range(10)
                    ),
                    "is_verified": True,
                },
            )
            if created:
                user.set_password("123")
                user.save()

            assignment, _ = CompetitionReviewer.objects.get_or_create(
                user=user, competition=obj
            )
            assignment.status = ReviewStatus.IN_PROGRESS
            assignment.save(update_fields=["status"])
            HANDLERS.reviews.replace_ballot(
                user.id, obj.id, [by_export_id[p].id for p in ballot]
            )
            assignment.status = ReviewStatus.COMPLETED
            assignment.save(update_fields=["status"])

        stored = ProjectRanking.objects.filter(competition=obj).count()
        print(
            f"  {local_name}: {len(ballots)} ballots, {stored} rankings  "
            f"-> /admin/projects/competition/{obj.pk}/voting-results/"
        )


def main() -> None:
    args = parse_args()
    export = Export(args.source)

    competitions = export.competitions
    if args.only:
        needle = args.only.lower()
        competitions = [
            c for c in competitions if needle in c["competition_name"].lower()
        ]
        if not competitions:
            message = f"no competition name contains {args.only!r}"
            raise SystemExit(message)

    print(f"Read {len(export.ballot_rows)} ranking rows from {args.source}")
    for competition in competitions:
        report(export, competition)

    if args.load:
        load_into_local_db(export, competitions, forced=args.i_know_its_not_local)


if __name__ == "__main__":
    main()
