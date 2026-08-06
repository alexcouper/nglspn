"""Pure tally functions: ballots in, pairwise margins and ranked tiers out.

No ORM, no Django. Ballot reduction and the ordering rule are separable —
reduction never invokes an ordering rule, and an ordering rule sees only a
matrix. See openspec/changes/less-biased-project-ranking/design.md.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Collection, Iterable, Sequence
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
