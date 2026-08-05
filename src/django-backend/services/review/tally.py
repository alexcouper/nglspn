"""Pure tally functions: ballots in, pairwise margins and ranked tiers out.

No ORM, no Django. Ballot reduction and the ordering rule are separable —
reduction never invokes an ordering rule, and an ordering rule sees only a
matrix. See openspec/changes/less-biased-project-ranking/design.md.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Sequence
from typing import Protocol
from uuid import UUID

ProjectId = UUID

# margins[a][b] is (ballots preferring a over b) - (ballots preferring b over a).
# Complete over the eligible projects; margins[a][a] is 0.
MarginMatrix = dict[ProjectId, dict[ProjectId, int]]

Ballot = Sequence[ProjectId]

# Strength of a non-existent path. Margins are ints, so this never collides.
_NO_PATH = float("-inf")


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
