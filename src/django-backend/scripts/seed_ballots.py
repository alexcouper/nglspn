#!/usr/bin/env python
"""Fill a competition with enough ballots to exercise the admin results page.

Tops an existing competition up to a target number of *completed* reviewers —
only completed reviews are counted by the tally, which is why a competition can
look empty on the results page despite having reviewers assigned.

Ballots are deliberately partial and disagreeing: each seeded reviewer perceives
a latent project quality through their own noise, ranks the ones they like, and
stops. That is what the pairwise tally is built for, and it is what makes the
"ranked by N/M" column and the margins grid show anything interesting. A few
reviewers abstain entirely.

Seeded reviewers are identified by their email prefix, so `--reset` can clear
them without touching real accounts or the hand-made fixtures.

Usage:
    uv run python scripts/seed_ballots.py
    uv run python scripts/seed_ballots.py --reviewers 30 --reset
    uv run python scripts/seed_ballots.py --competition "Mars keppni 2025"
    # or
    make seed-ballots
"""

import argparse
import os
import random
import secrets
import string
import sys
from pathlib import Path

DJANGO_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DJANGO_BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_showcase.settings")

import django

django.setup()

from apps.projects.models import (
    Competition,
    CompetitionReviewer,
    ProjectRanking,
    ReviewStatus,
)
from apps.users.models import User
from services import HANDLERS, REPO

DEFAULT_COMPETITION = "Verification keppni 2026"
DEFAULT_REVIEWERS = 20
DEFAULT_SEED = 20260806
DEFAULT_PASSWORD = "123"

# Every account this script creates starts with this. `--reset` deletes exactly
# these, so hand-made reviewers on the same competition survive.
SEED_EMAIL_PREFIX = "ballot-seed-"

FIRST_NAMES = [
    "Anna",
    "Bjarni",
    "Dagur",
    "Elín",
    "Freyja",
    "Gunnar",
    "Halla",
    "Ingi",
    "Jóhanna",
    "Katrín",
    "Lárus",
    "Margrét",
    "Njáll",
    "Ólöf",
    "Páll",
    "Ragna",
    "Sigrún",
    "Tómas",
    "Unnur",
    "Vigdís",
    "Ýmir",
    "Þóra",
    "Ævar",
    "Örn",
]
LAST_NAMES = [
    "Arnarsdóttir",
    "Björnsson",
    "Einarsdóttir",
    "Guðmundsson",
    "Haraldsdóttir",
    "Jónsson",
    "Kristjánsdóttir",
    "Magnússon",
    "Ólafsdóttir",
    "Pétursson",
    "Sigurðardóttir",
    "Þorsteinsson",
]

# How many projects a reviewer bothers to rank, as weights over
# 0..len(projects). Short ballots dominate; a couple of people abstain.
BALLOT_LENGTH_WEIGHTS = [3, 6, 10, 12, 10, 6, 3, 2, 1]

# How much a reviewer's taste diverges from the latent quality ordering. Latent
# quality steps by 1.0 per rank, so noise above ~1.0 makes adjacent projects
# swap freely and pushes real disagreement — and sometimes a cycle — into the
# middle of the table, which is the case worth looking at on the admin page.
TASTE_NOISE = 1.25


def generate_kennitala() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(10))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--competition",
        default=DEFAULT_COMPETITION,
        help=f"competition name (default: {DEFAULT_COMPETITION!r})",
    )
    parser.add_argument(
        "--reviewers",
        type=int,
        default=DEFAULT_REVIEWERS,
        help=f"target number of completed ballots (default: {DEFAULT_REVIEWERS})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="RNG seed; same seed gives the same ballots",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="delete previously seeded reviewers and their ballots first",
    )
    return parser.parse_args()


def get_competition(name: str) -> Competition:
    competition = Competition.objects.filter(name=name).first()
    if competition is None:
        available = ", ".join(
            repr(n) for n in Competition.objects.values_list("name", flat=True)
        )
        message = f"No competition named {name!r}.\nAvailable: {available}"
        raise SystemExit(message)
    return competition


def reset_seeded(competition: Competition) -> int:
    """Remove this script's reviewers, leaving hand-made ones in place."""
    seeded = User.objects.filter(email__startswith=SEED_EMAIL_PREFIX)
    ProjectRanking.objects.filter(competition=competition, reviewer__in=seeded).delete()
    removed, _ = CompetitionReviewer.objects.filter(
        competition=competition, user__in=seeded
    ).delete()
    return removed


def get_or_create_reviewer(index: int, rng: random.Random) -> User:
    email = f"{SEED_EMAIL_PREFIX}{index:02d}@example.com"
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "first_name": rng.choice(FIRST_NAMES),
            "last_name": rng.choice(LAST_NAMES),
            "kennitala": generate_kennitala(),
            "is_verified": True,
        },
    )
    if created:
        user.set_password(DEFAULT_PASSWORD)
        user.save()
    return user


def build_ballot(project_ids: list, quality: dict, rng: random.Random) -> list:
    """One reviewer's partial ballot: their taste order, truncated.

    Perceived quality is the latent quality plus per-reviewer noise, so
    reviewers broadly agree at the extremes and disagree in the middle — which
    is where a pairwise tally earns its keep.
    """
    perceived = {pid: quality[pid] + rng.gauss(0, TASTE_NOISE) for pid in project_ids}
    preference = sorted(project_ids, key=lambda pid: perceived[pid], reverse=True)

    lengths = range(min(len(BALLOT_LENGTH_WEIGHTS), len(project_ids) + 1))
    length = rng.choices(list(lengths), weights=BALLOT_LENGTH_WEIGHTS[: len(lengths)])[
        0
    ]
    return preference[:length]


def seed_ballots(competition: Competition, target: int, rng: random.Random) -> dict:
    projects = list(
        competition.projects.exclude(
            status__in=["rejected", "ice_box"],
        ).values_list("id", "title")
    )
    if not projects:
        message = f"{competition.name!r} has no rankable projects."
        raise SystemExit(message)

    project_ids = [pid for pid, _ in projects]
    # Shuffle *before* assigning quality, so which project is strongest depends
    # on the seed rather than on the competition's default project ordering.
    rng.shuffle(project_ids)
    quality = {pid: float(len(project_ids) - i) for i, pid in enumerate(project_ids)}

    already_completed = CompetitionReviewer.objects.filter(
        competition=competition, status=ReviewStatus.COMPLETED
    ).count()
    to_add = max(0, target - already_completed)

    abstentions = 0
    for index in range(1, to_add + 1):
        user = get_or_create_reviewer(index, rng)
        assignment, _ = CompetitionReviewer.objects.get_or_create(
            user=user, competition=competition
        )
        # Write through the service so the ballot goes in the way the API would
        # write it. It refuses a closed review, so rank first, complete after.
        assignment.status = ReviewStatus.IN_PROGRESS
        assignment.save(update_fields=["status"])

        ballot = build_ballot(project_ids, quality, rng)
        HANDLERS.reviews.replace_ballot(user.id, competition.id, ballot)
        if not ballot:
            abstentions += 1

        assignment.status = ReviewStatus.COMPLETED
        assignment.save(update_fields=["status"])

    return {
        "added": to_add,
        "already_completed": already_completed,
        "abstentions": abstentions,
        "projects": len(project_ids),
    }


def print_standings(competition: Competition) -> None:
    """Show what the admin results page will now show."""
    tally = REPO.reviews.get_competition_tally(competition.id)

    print(f"\nStandings for {competition.name!r} — {tally.counted_ballots} ballots")
    print(f"  {'#':<4}{'Project':<24}{'1st':>5}{'Ranked by':>11}{'Mean pos':>10}")
    rank = 1
    for tier in tally.tiers:
        for project_id in tier:
            support = tally.support[project_id]
            mean = (
                f"{support.mean_position:.1f}"
                if support.mean_position is not None
                else "—"
            )
            shared = " =" if len(tier) > 1 else ""
            print(
                f"  {str(rank) + shared:<4}"
                f"{tally.projects[project_id].title[:23]:<24}"
                f"{support.first_place_count:>5}"
                f"{support.ranked_by_count:>7}/{tally.counted_ballots:<3}"
                f"{mean:>10}"
            )
        rank += len(tier)

    ties = sum(1 for tier in tally.tiers if len(tier) > 1)
    top = tally.tiers[0] if tally.tiers else []
    if len(top) > 1:
        print("\n  No single winner — the top tier is shared (a cycle at the top).")
    elif ties:
        print(f"\n  {ties} shared tier(s) further down — the grid shows why.")
    else:
        print("\n  Clean total order, no ties.")


def main() -> None:
    args = parse_args()
    # Seeded deliberately: the same --seed must give the same ballots.
    rng = random.Random(args.seed)  # noqa: S311
    competition = get_competition(args.competition)

    print(f"=== Seeding ballots for {competition.name!r} ({competition.status}) ===")

    if args.reset:
        removed = reset_seeded(competition)
        print(f"Removed {removed} previously seeded reviewer(s).")

    result = seed_ballots(competition, args.reviewers, rng)

    print(
        f"Added {result['added']} completed ballot(s) "
        f"over {result['projects']} projects "
        f"({result['already_completed']} were already completed, "
        f"{result['abstentions']} of the new ones abstained)."
    )
    print_standings(competition)
    print(f"\nAdmin page: /admin/projects/competition/{competition.pk}/voting-results/")


if __name__ == "__main__":
    main()
