#!/usr/bin/env python
"""Replay a past competition's published results table under the new tally.

The old admin page published a *position histogram* — how many reviewers put
each project 1st, 2nd, and so on — plus a Borda score. That histogram does not
determine the ballots: many different ballot sets produce the same table, and
they do not all give the same pairwise result. So this script does two things:

  --analyse   sample many ballot sets consistent with the table and report how
              often each outcome comes up. This is the honest answer to "what
              would have happened", because it shows what the table does and
              does not pin down.

  (default)   build the competition in the database from one reconstruction, so
              the admin results page can be looked at.

Reconstruction is a Birkhoff decomposition: the histogram is a non-negative
integer matrix whose rows and columns all sum to the voter count, so it splits
into exactly that many permutation matrices — one full ballot each. A perfect
matching therefore always exists at every step (Hall's condition), and the
result reproduces the published table exactly, which the script checks.

Usage:
    uv run python scripts/replay_competition.py --analyse
    uv run python scripts/replay_competition.py
    uv run python scripts/replay_competition.py --seed 3 --reset
"""

import argparse
import os
import random
import secrets
import string
import sys
from collections import Counter
from datetime import date
from pathlib import Path

DJANGO_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DJANGO_BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_showcase.settings")

import django

django.setup()

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
from services import HANDLERS, REPO
from services.review.tally import (
    MarginMatrix,
    break_ties,
    reduce_ballots_to_margins,
    schulze_order,
    support_signals,
)

COMPETITION_NAME = "Broadside keppni (replay)"
SEED_EMAIL_PREFIX = "replay-voter-"
DEFAULT_PASSWORD = "123"
DEFAULT_SEED = 1
DEFAULT_SAMPLES = 2000

# The published results table, as it appeared on the production admin page.
# project -> how many reviewers placed it 1st, 2nd, ... 8th.
RESULTS_TABLE: dict[str, list[int]] = {
    "Broadside": [6, 3, 1, 3, 2, 0, 0, 0],
    "folfvellir.is": [3, 2, 8, 1, 0, 1, 0, 0],
    "Vissar": [1, 7, 1, 1, 0, 0, 2, 3],
    "Komms": [1, 1, 3, 4, 4, 1, 1, 0],
    "WikiRadar": [2, 2, 0, 2, 1, 2, 4, 2],
    "Sino.pe": [1, 0, 1, 2, 4, 6, 1, 0],
    "tepuisec.com": [1, 0, 0, 2, 3, 1, 5, 3],
    "CowCo": [0, 0, 1, 0, 1, 4, 2, 7],
}
TITLES = list(RESULTS_TABLE)
PLACES = len(TITLES)
VOTERS = sum(RESULTS_TABLE[TITLES[0]])


def generate_kennitala() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(10))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--analyse",
        action="store_true",
        help="sample consistent ballot sets and report outcome stability; no writes",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=DEFAULT_SAMPLES,
        help=f"reconstructions to sample when analysing (default: {DEFAULT_SAMPLES})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="RNG seed; the same seed reconstructs the same ballots",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="delete the replay competition and its voters first",
    )
    return parser.parse_args()


def check_table() -> None:
    """The table must describe full ballots, or it is not a valid histogram."""
    for title, counts in RESULTS_TABLE.items():
        if sum(counts) != VOTERS:
            message = f"{title} has {sum(counts)} ballots, expected {VOTERS}"
            raise SystemExit(message)
    for place in range(PLACES):
        total = sum(RESULTS_TABLE[t][place] for t in TITLES)
        if total != VOTERS:
            message = f"place {place + 1} was awarded {total} times, expected {VOTERS}"
            raise SystemExit(message)


def borda_scores() -> dict[str, int]:
    """The old rule: 1st is worth `PLACES` points, last is worth 1."""
    return {
        title: sum(count * (PLACES - place) for place, count in enumerate(counts))
        for title, counts in RESULTS_TABLE.items()
    }


def _perfect_matching(
    remaining: dict[str, list[int]], rng: random.Random
) -> dict[int, str] | None:
    """Assign each place to a distinct project that still has a slot there.

    Exists at every step while all rows and columns of `remaining` sum to the
    same positive number, which decrementing a full matching preserves.
    """
    taken: dict[int, str] = {}

    def augment(title: str, seen: set[int]) -> bool:
        places = [p for p in range(PLACES) if remaining[title][p] > 0]
        rng.shuffle(places)
        for place in places:
            if place in seen:
                continue
            seen.add(place)
            if place not in taken or augment(taken[place], seen):
                taken[place] = title
                return True
        return False

    order = list(TITLES)
    rng.shuffle(order)
    for title in order:
        if not augment(title, set()):
            return None
    return taken


def reconstruct(rng: random.Random) -> list[list[str]]:
    """One set of full ballots whose position histogram is exactly the table."""
    remaining = {t: list(RESULTS_TABLE[t]) for t in TITLES}
    ballots = []
    for _ in range(VOTERS):
        matching = _perfect_matching(remaining, rng)
        if matching is None:  # unreachable while Hall's condition holds
            message = "no perfect matching; the table is not a valid histogram"
            raise SystemExit(message)
        for place, title in matching.items():
            remaining[title][place] -= 1
        ballots.append([matching[place] for place in range(PLACES)])

    if histogram(ballots) != RESULTS_TABLE:
        message = "reconstruction does not reproduce the published table"
        raise SystemExit(message)
    return ballots


def histogram(ballots: list[list[str]]) -> dict[str, list[int]]:
    counts = {t: [0] * PLACES for t in TITLES}
    for ballot in ballots:
        for place, title in enumerate(ballot):
            counts[title][place] += 1
    return counts


def schulze_tiers(
    ballots: list[list[str]],
) -> tuple[list[list[str]], MarginMatrix]:
    margins = reduce_ballots_to_margins(ballots, TITLES)
    support = support_signals(ballots, TITLES)
    # Same ladder the admin page applies, so a replay matches what it shows.
    tiers, _reasons = break_ties(schulze_order(margins), margins, support)
    return tiers, margins


def has_condorcet_winner(margins: MarginMatrix) -> bool:
    return any(all(margins[a][b] > 0 for b in TITLES if b != a) for a in TITLES)


class Survey:
    """What varied across ballot sets that all match the published table."""

    def __init__(self) -> None:
        self.samples = 0
        self.winners: Counter = Counter()
        self.orderings: Counter = Counter()
        self.ranks: dict[str, Counter] = {t: Counter() for t in TITLES}
        self.cycles = 0
        self.margin_range: dict[tuple[str, str], tuple[int, int]] = {}

    def record(self, tiers: list[list[str]], margins: MarginMatrix) -> None:
        self.samples += 1
        self.winners[" = ".join(sorted(tiers[0]))] += 1
        self.orderings[tuple(t for tier in tiers for t in tier)] += 1

        rank = 1
        for tier in tiers:
            for title in tier:
                self.ranks[title][rank] += 1
            rank += len(tier)

        if not has_condorcet_winner(margins):
            self.cycles += 1

        for a in TITLES:
            for b in TITLES:
                if a == b:
                    continue
                lo, hi = self.margin_range.get((a, b), (VOTERS, -VOTERS))
                self.margin_range[(a, b)] = (
                    min(lo, margins[a][b]),
                    max(hi, margins[a][b]),
                )

    def pct(self, count: int) -> str:
        return f"{100 * count / self.samples:.1f}%"

    def undetermined_pairs(self) -> list[tuple[str, str]]:
        """Pairs whose head-to-head winner the table leaves open."""
        return sorted(
            (a, b)
            for (a, b), (lo, hi) in self.margin_range.items()
            if lo <= 0 <= hi and TITLES.index(a) < TITLES.index(b)
        )


def analyse(samples: int, rng: random.Random) -> None:
    survey = Survey()
    for _ in range(samples):
        tiers, margins = schulze_tiers(reconstruct(rng))
        survey.record(tiers, margins)
    report(survey)


def report(survey: Survey) -> None:
    samples = survey.samples
    winners = survey.winners
    orderings = survey.orderings
    ranks = survey.ranks
    cycles = survey.cycles
    pct = survey.pct

    print(f"=== {samples} ballot sets consistent with the published table ===\n")

    print("Winner under the new tally:")
    for winner, count in winners.most_common():
        print(f"  {pct(count):>7}  {winner}")

    print(f"\nNo Condorcet winner (a cycle at the top): {pct(cycles)} of samples")

    print("\nWhere each project lands (rank: share of samples):")
    old_rank = {t: i + 1 for i, t in enumerate(TITLES)}
    for title in TITLES:
        spread = "  ".join(
            f"{r}:{pct(c)}" for r, c in sorted(ranks[title].items()) if c
        )
        print(f"  was {old_rank[title]}  {title:<15} {spread}")

    print(f"\nDistinct orderings seen: {len(orderings)}")
    for ordering, count in orderings.most_common(3):
        print(f"  {pct(count):>7}  {' > '.join(ordering)}")

    undetermined = survey.undetermined_pairs()
    print("\nHead-to-head results the table does NOT pin down:")
    if not undetermined:
        print("  none")
    for a, b in undetermined:
        lo, hi = survey.margin_range[(a, b)]
        print(f"  {a} vs {b}: margin anywhere from {lo:+d} to {hi:+d}")


def print_comparison(ballots: list[list[str]]) -> None:
    tiers, margins = schulze_tiers(ballots)
    borda = borda_scores()
    firsts = {t: RESULTS_TABLE[t][0] for t in TITLES}

    print("\nOld Borda order vs this reconstruction's Schulze order:\n")
    print(f"  {'was':<5}{'now':<6}{'Project':<16}{'Borda':>6}{'1st':>5}  moved")
    rank = 1
    for tier in tiers:
        for title in tier:
            was = TITLES.index(title) + 1
            shared = "=" if len(tier) > 1 else " "
            move = was - rank
            arrow = (
                "—" if move == 0 else (f"up {move}" if move > 0 else f"down {-move}")
            )
            print(
                f"  {was:<5}{str(rank) + shared:<6}{title:<16}"
                f"{borda[title]:>6}{firsts[title]:>5}  {arrow}"
            )
        rank += len(tier)

    if not has_condorcet_winner(margins):
        print("\n  No Condorcet winner in this reconstruction — the top is a cycle.")


def verify_against_stored(competition: Competition, ballots: list[list[str]]) -> None:
    """The page must agree with the pure tally run over the same ballots."""
    stored = REPO.reviews.get_competition_tally(competition.id)
    stored_order = [stored.projects[pid].title for tier in stored.tiers for pid in tier]
    expected = [t for tier in schulze_tiers(ballots)[0] for t in tier]

    if stored_order == expected and stored.counted_ballots == VOTERS:
        print("\n  Verified: the stored competition tallies to the same order.")
    else:
        print(
            f"\n  MISMATCH — stored order {stored_order} "
            f"({stored.counted_ballots} ballots) vs expected {expected}"
        )


def reset(competition: Competition | None) -> None:
    if competition is not None:
        ProjectRanking.objects.filter(competition=competition).delete()
        CompetitionReviewer.objects.filter(competition=competition).delete()
        titles = list(competition.projects.values_list("title", flat=True))
        competition.delete()
        Project.objects.filter(title__in=titles, submission_month="replay").delete()
    User.objects.filter(email__startswith=SEED_EMAIL_PREFIX).delete()


def build_competition(
    rng: random.Random,
) -> tuple[Competition, list[list[str]]]:
    admin = User.objects.filter(is_staff=True).first()

    projects = []
    for title in TITLES:
        project, _ = Project.objects.get_or_create(
            title=title,
            submission_month="replay",
            defaults={
                "tagline": f"{title} — replayed from the published results table",
                "description": (
                    "Recreated locally so the admin results page has the "
                    "production competition's ballots to render."
                ),
                "website_url": f"https://{title.lower().replace(' ', '')}.example",
                "status": ProjectStatus.APPROVED,
                "creator": admin,
                "approved_by": admin,
            },
        )
        projects.append(project)

    competition, _ = Competition.objects.get_or_create(
        name=COMPETITION_NAME,
        defaults={
            "start_date": date(2026, 1, 1),
            "submission_deadline": date(2026, 1, 31),
            "status": CompetitionStatus.VOTING,
        },
    )
    competition.projects.set(projects)

    by_title = {p.title: p for p in projects}
    ballots = reconstruct(rng)
    for index, ballot in enumerate(ballots, start=1):
        user, created = User.objects.get_or_create(
            email=f"{SEED_EMAIL_PREFIX}{index:02d}@example.com",
            defaults={
                "first_name": "Replay",
                "last_name": f"Voter {index}",
                "kennitala": generate_kennitala(),
                "is_verified": True,
            },
        )
        if created:
            user.set_password(DEFAULT_PASSWORD)
            user.save()

        assignment, _ = CompetitionReviewer.objects.get_or_create(
            user=user, competition=competition
        )
        assignment.status = ReviewStatus.IN_PROGRESS
        assignment.save(update_fields=["status"])

        HANDLERS.reviews.replace_ballot(
            user.id, competition.id, [by_title[t].id for t in ballot]
        )

        assignment.status = ReviewStatus.COMPLETED
        assignment.save(update_fields=["status"])

    return competition, ballots


def main() -> None:
    args = parse_args()
    check_table()
    rng = random.Random(args.seed)  # noqa: S311 — reproducibility, not secrecy

    if args.analyse:
        analyse(args.samples, rng)
        return

    if args.reset:
        reset(Competition.objects.filter(name=COMPETITION_NAME).first())
        print(f"Removed any previous {COMPETITION_NAME!r}.")

    competition, ballots = build_competition(rng)
    print(
        f"Built {competition.name!r}: {PLACES} projects, {VOTERS} completed ballots "
        f"(reconstruction seed {args.seed})."
    )

    print_comparison(ballots)
    verify_against_stored(competition, ballots)

    print(f"\nAdmin page: /admin/projects/competition/{competition.pk}/voting-results/")
    print(
        "\nThis is ONE reconstruction. Run --analyse to see which parts of the "
        "result the published table actually determines."
    )


if __name__ == "__main__":
    main()
