"""Pure tally functions: ballots in, pairwise margins and ranked tiers out.

No ORM, no Django. Ballot reduction and the ordering rule are separable —
reduction never invokes an ordering rule, and an ordering rule sees only a
matrix. Swapping in a different rule therefore changes only which projects end
up in which tier, never how a ballot is read.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Collection, Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

ProjectId = UUID

# margins[a][b] is (ballots preferring a over b) - (ballots preferring b over a).
# Complete over the eligible projects; margins[a][a] is 0.
MarginMatrix = dict[ProjectId, dict[ProjectId, int]]

Ballot = Sequence[ProjectId]

# Strength of a non-existent path. Margins are ints, so this never collides.
_NO_PATH = float("-inf")


@dataclass(frozen=True)
class ProjectSupport:
    """Raw signals behind one project's placement, for an admin to weigh."""

    first_place_count: int = 0
    ranked_by_count: int = 0
    mean_position: float | None = None


# A rung scores each tied project; higher is better, and equal scores stay tied.
ScoreRung = Callable[
    [list[ProjectId], MarginMatrix, dict[ProjectId, ProjectSupport]],
    dict[ProjectId, float],
]

# Score for a project a rung cannot rate at all. Sorts last.
_WORST = float("-inf")


@dataclass(frozen=True)
class TieBreak:
    """Why a project shared a tier with others but no longer ranks alongside
    all of them.

    `tied_with` holds only the projects `rung` moved it clear of. A project it
    still shares a rank with is absent — the ladder never separated the two.
    """

    rung: str
    tied_with: tuple[ProjectId, ...]


class OrderingRule(Protocol):
    """Turns a margin matrix into ranked tiers, best tier first.

    Tiers rather than a flat list so that a tie is a first-class result the
    consumer can render without knowing which rule produced it.
    """

    def __call__(self, margins: MarginMatrix) -> list[list[ProjectId]]: ...


def reduce_ballots_to_margins(
    ballots: Iterable[Ballot],
    eligible_project_ids: Collection[ProjectId],
) -> MarginMatrix:
    """Reduce ballots to pairwise margins over the eligible projects.

    A ranked project is preferred over every project ranked below it and over
    every eligible project the reviewer left unranked. Two unranked projects
    contribute nothing, which is what makes truncating a ballot harmless.

    Project ids that are not eligible are ignored wherever they appear.
    """
    eligible = list(dict.fromkeys(eligible_project_ids))
    margins: MarginMatrix = {a: dict.fromkeys(eligible, 0) for a in eligible}

    for ballot in ballots:
        ranked = list(dict.fromkeys(p for p in ballot if p in margins))
        unranked = [p for p in eligible if p not in set(ranked)]
        for index, preferred in enumerate(ranked):
            for over in (*ranked[index + 1 :], *unranked):
                margins[preferred][over] += 1
                margins[over][preferred] -= 1

    return margins


def schulze_order(margins: MarginMatrix) -> list[list[ProjectId]]:
    """Order projects by the Schulze method (strongest paths) over margins.

    A project is ordered above another when its strongest path to that project
    is stronger than the reverse. Projects the method cannot separate share a
    tier.
    """
    projects = list(margins)
    strengths = _strongest_paths(margins)

    beaten = {
        a: sum(1 for b in projects if a != b and strengths[a][b] > strengths[b][a])
        for a in projects
    }

    return [
        [p for p in projects if beaten[p] == count]
        for count in sorted(set(beaten.values()), reverse=True)
    ]


def _strongest_paths(margins: MarginMatrix) -> dict[ProjectId, dict[ProjectId, float]]:
    """Floyd-Warshall over the positive-margin links."""
    projects = list(margins)
    strengths: dict[ProjectId, dict[ProjectId, float]] = {
        a: {
            b: (margins[a][b] if a != b and margins[a][b] > 0 else _NO_PATH)
            for b in projects
        }
        for a in projects
    }

    for via in projects:
        for a in projects:
            if a == via:
                continue
            for b in projects:
                if b in (a, via):
                    continue
                through = min(strengths[a][via], strengths[via][b])
                strengths[a][b] = max(strengths[a][b], through)

    return strengths


def support_signals(
    ballots: Iterable[Ballot],
    eligible_project_ids: Collection[ProjectId],
) -> dict[ProjectId, ProjectSupport]:
    """First-place count, ranked-by count and mean position among rankers.

    Positions are the reviewer's own contiguous ordering, so a project ranked
    second on a two-project ballot has position 2 regardless of how many
    projects the reviewer skipped.
    """
    first_place: dict[ProjectId, int] = defaultdict(int)
    ranked_by: dict[ProjectId, int] = defaultdict(int)
    position_total: dict[ProjectId, int] = defaultdict(int)

    for ballot in ballots:
        for position, project_id in enumerate(ballot, start=1):
            ranked_by[project_id] += 1
            position_total[project_id] += position
            if position == 1:
                first_place[project_id] += 1

    return {
        project_id: ProjectSupport(
            first_place_count=first_place[project_id],
            ranked_by_count=ranked_by[project_id],
            mean_position=(
                position_total[project_id] / ranked_by[project_id]
                if ranked_by[project_id]
                else None
            ),
        )
        for project_id in eligible_project_ids
    }


def _worst_defeat(
    tied: list[ProjectId],
    margins: MarginMatrix,
    support: dict[ProjectId, ProjectSupport],
) -> dict[ProjectId, float]:
    """Each project's biggest losing margin *within the tied group*.

    Least bad wins. For a pair this is simply the head-to-head result; for a
    loop it is the only comparison-based answer available, because no project
    in a loop is unbeaten.
    """
    return {a: min(margins[a][b] for b in tied if b != a) for a in tied}


def _breadth(
    tied: list[ProjectId],
    margins: MarginMatrix,
    support: dict[ProjectId, ProjectSupport],
) -> dict[ProjectId, float]:
    """How many reviewers ranked the project at all. More is better."""
    return {a: support[a].ranked_by_count for a in tied}


def _mean_position(
    tied: list[ProjectId],
    margins: MarginMatrix,
    support: dict[ProjectId, ProjectSupport],
) -> dict[ProjectId, float]:
    """Mean position among rankers, negated because position 1 is best.

    A project nobody ranked has no mean position and sorts last.
    """
    scores: dict[ProjectId, float] = {}
    for a in tied:
        mean = support[a].mean_position
        scores[a] = _WORST if mean is None else -mean
    return scores


def _first_places(
    tied: list[ProjectId],
    margins: MarginMatrix,
    support: dict[ProjectId, ProjectSupport],
) -> dict[ProjectId, float]:
    """How many reviewers put the project top. More is better."""
    return {a: support[a].first_place_count for a in tied}


# Order matters: the margin-based rung leads so the ladder can never
# contradict the vote, and the positional rungs come last
# because they measure how much reviewers preferred a project rather than how
# often — the scoring this tally deliberately moved away from.
TIE_BREAK_RUNGS: list[tuple[str, ScoreRung]] = [
    ("least-bad worst defeat", _worst_defeat),
    ("ranked by more reviewers", _breadth),
    ("better mean position", _mean_position),
    ("more first-place votes", _first_places),
]


def _separate(
    tied: list[ProjectId],
    margins: MarginMatrix,
    support: dict[ProjectId, ProjectSupport],
    rungs: list[tuple[str, ScoreRung]],
) -> list[tuple[list[ProjectId], str | None, list[ProjectId]]]:
    """Split a tied group into ordered subgroups, best first.

    Each subgroup carries the rung that separated it and the group that rung
    was weighing when it did — the subgroup's own members plus the ones it was
    separated from, and nobody else. The rung is None when the ladder ran out
    and the subgroup is genuinely indistinguishable.
    """
    if len(tied) == 1 or not rungs:
        return [(list(tied), None, list(tied))]

    (name, score), *rest = rungs
    scores = score(tied, margins, support)
    groups = [
        [p for p in tied if scores[p] == value]
        for value in sorted(set(scores.values()), reverse=True)
    ]
    if len(groups) == 1:
        return _separate(tied, margins, support, rest)

    separated: list[tuple[list[ProjectId], str | None, list[ProjectId]]] = []
    for group in groups:
        for subgroup, deeper_name, deeper_cohort in _separate(
            group, margins, support, rest
        ):
            # A deeper rung acted last and on a narrower group; report that
            # rather than this one, which the subgroup no longer needs.
            if deeper_name is None:
                separated.append((subgroup, name, tied))
            else:
                separated.append((subgroup, deeper_name, deeper_cohort))
    return separated


def break_ties(
    tiers: list[list[ProjectId]],
    margins: MarginMatrix,
    support: dict[ProjectId, ProjectSupport],
) -> tuple[list[list[ProjectId]], dict[ProjectId, TieBreak]]:
    """Split tied tiers as far as the ladder allows.

    Returns the new tiers and, for each project whose placement came from a
    tiebreak, which rung decided it and who that rung separated it from.
    Projects still sharing its rank are not listed: they were tied with it
    before and remain so.
    """
    resolved: list[list[ProjectId]] = []
    reasons: dict[ProjectId, TieBreak] = {}

    for tier in tiers:
        if len(tier) == 1:
            resolved.append(list(tier))
            continue

        for group, rung, cohort in _separate(
            list(tier), margins, support, TIE_BREAK_RUNGS
        ):
            resolved.append(group)
            if rung is None:
                continue
            still_tied = set(group)
            separated_from = tuple(p for p in cohort if p not in still_tied)
            for project_id in group:
                reasons[project_id] = TieBreak(rung=rung, tied_with=separated_from)

    return resolved, reasons
